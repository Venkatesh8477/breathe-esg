from rest_framework import serializers
from ingestion.models import IngestionBatch, EmissionRecord, ValidationFlag, AuditEvent, RawRecord


class ValidationFlagSerializer(serializers.ModelSerializer):
    flag_type_display = serializers.CharField(source='get_flag_type_display', read_only=True)

    class Meta:
        model = ValidationFlag
        fields = ['id', 'flag_type', 'flag_type_display', 'field_name', 'detail']


class AuditEventSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = ['id', 'action', 'performed_by_name', 'performed_at', 'previous_status', 'new_status', 'note']

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name() or obj.performed_by.username
        return 'System'


class IngestionBatchSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'tenant_name', 'source_type', 'source_type_display',
            'filename', 'uploaded_by_name', 'is_mine', 'uploaded_at',
            'status', 'status_display', 'total_rows', 'parsed_rows', 'failed_rows', 'error_message'
        ]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return 'Unknown'

    def get_is_mine(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            return obj.uploaded_by_id == request.user.id
        return False


class EmissionRecordSerializer(serializers.ModelSerializer):
    flags = ValidationFlagSerializer(many=True, read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_type = serializers.CharField(source='batch.source_type', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    flag_count = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'tenant_name', 'source_type',
            'scope', 'scope_display', 'category', 'category_display',
            'quantity', 'unit_normalized', 'original_quantity', 'original_unit',
            'activity_date', 'period_start', 'period_end',
            'site_code', 'site_name', 'description', 'supplier_vendor',
            'status', 'status_display', 'reviewed_by_name', 'reviewed_at', 'review_note',
            'locked', 'created_at', 'flags', 'flag_count',
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return None

    def get_flag_count(self, obj):
        return obj.flags.count()


class EmissionRecordDetailSerializer(EmissionRecordSerializer):
    audit_events = AuditEventSerializer(many=True, read_only=True)
    raw_data = serializers.SerializerMethodField()

    class Meta(EmissionRecordSerializer.Meta):
        fields = EmissionRecordSerializer.Meta.fields + ['audit_events', 'raw_data']

    def get_raw_data(self, obj):
        return obj.raw_record.raw_data


class BatchUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    source_type = serializers.ChoiceField(choices=IngestionBatch.SOURCE_CHOICES)
    tenant_slug = serializers.SlugField(required=False, default='default-client')
