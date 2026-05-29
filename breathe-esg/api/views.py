from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ingestion.models import IngestionBatch, EmissionRecord, ValidationFlag, AuditEvent, Tenant
from ingestion.services import process_batch
from .serializers import (
    IngestionBatchSerializer, EmissionRecordSerializer,
    EmissionRecordDetailSerializer, AuditEventSerializer,
    BatchUploadSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok'})


class BatchUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        source_type = serializer.validated_data['source_type']
        tenant_slug = serializer.validated_data.get('tenant_slug', 'default')

        tenant, _ = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={'name': tenant_slug.replace('-', ' ').title()}
        )

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type=source_type,
            filename=file_obj.name,
            uploaded_by=request.user,
        )

        file_bytes = file_obj.read()
        process_batch(batch, file_bytes)

        return Response(IngestionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class BatchListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        return IngestionBatch.objects.select_related('tenant', 'uploaded_by').order_by('-uploaded_at')


class BatchDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IngestionBatchSerializer
    queryset = IngestionBatch.objects.all()

    def destroy(self, request, *args, **kwargs):
        batch = self.get_object()
        if batch.uploaded_by_id != request.user.id:
            return Response({'detail': 'Only the uploader may delete this batch.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class EmissionRecordListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        qs = EmissionRecord.objects.select_related(
            'tenant', 'batch', 'reviewed_by'
        ).prefetch_related('flags').order_by('-created_at')

        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(batch__source_type=source)

        scope = self.request.query_params.get('scope')
        if scope:
            qs = qs.filter(scope=scope)

        rec_status = self.request.query_params.get('status')
        if rec_status:
            qs = qs.filter(status=rec_status)

        batch_id = self.request.query_params.get('batch')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)

        tenant = self.request.query_params.get('tenant')
        if tenant:
            qs = qs.filter(tenant__slug=tenant)

        return qs


class EmissionRecordDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmissionRecordDetailSerializer
    queryset = EmissionRecord.objects.prefetch_related('flags', 'audit_events__performed_by')


class RecordReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if record.locked:
            return Response({'error': 'Record is locked for audit'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action')
        note = request.data.get('note', '')

        if action not in ('approve', 'reject', 'flag'):
            return Response({'error': 'action must be approve, reject, or flag'}, status=status.HTTP_400_BAD_REQUEST)

        prev_status = record.status
        status_map = {
            'approve': EmissionRecord.STATUS_APPROVED,
            'reject': EmissionRecord.STATUS_REJECTED,
            'flag': EmissionRecord.STATUS_FLAGGED,
        }
        audit_map = {
            'approve': AuditEvent.ACTION_APPROVED,
            'reject': AuditEvent.ACTION_REJECTED,
            'flag': AuditEvent.ACTION_FLAGGED,
        }

        record.status = status_map[action]
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_note = note
        if action == 'approve':
            record.locked = True
        record.save()

        AuditEvent.objects.create(
            emission_record=record,
            action=audit_map[action],
            performed_by=request.user,
            previous_status=prev_status,
            new_status=record.status,
            note=note,
        )

        return Response(EmissionRecordSerializer(record).data)


class BulkReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get('ids', [])
        action = request.data.get('action')
        note = request.data.get('note', '')

        if not ids or action not in ('approve', 'reject'):
            return Response({'error': 'ids and action (approve/reject) required'}, status=status.HTTP_400_BAD_REQUEST)

        records = EmissionRecord.objects.filter(pk__in=ids, locked=False)
        updated = 0

        status_val = EmissionRecord.STATUS_APPROVED if action == 'approve' else EmissionRecord.STATUS_REJECTED
        audit_action = AuditEvent.ACTION_APPROVED if action == 'approve' else AuditEvent.ACTION_REJECTED

        for record in records:
            prev = record.status
            record.status = status_val
            record.reviewed_by = request.user
            record.reviewed_at = timezone.now()
            record.review_note = note
            if action == 'approve':
                record.locked = True
            record.save()

            AuditEvent.objects.create(
                emission_record=record,
                action=audit_action,
                performed_by=request.user,
                previous_status=prev,
                new_status=status_val,
                note=note,
            )
            updated += 1

        return Response({'updated': updated})


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = EmissionRecord.objects.all()

        tenant = request.query_params.get('tenant')
        if tenant:
            records = records.filter(tenant__slug=tenant)

        stats = records.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            flagged=Count('id', filter=Q(status='flagged')),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected')),
        )

        by_scope = list(
            records.values('scope').annotate(count=Count('id'))
        )
        by_source = list(
            records.values('batch__source_type').annotate(count=Count('id'))
        )

        recent_batches = IngestionBatch.objects.order_by('-uploaded_at')[:5]

        return Response({
            'summary': stats,
            'by_scope': by_scope,
            'by_source': by_source,
            'recent_batches': IngestionBatchSerializer(recent_batches, many=True, context={'request': request}).data,
        })
