from django.contrib import admin
from .models import Tenant, IngestionBatch, RawRecord, EmissionRecord, ValidationFlag, AuditEvent

admin.site.register(Tenant)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'scope', 'category', 'quantity', 'unit_normalized', 'status', 'activity_date']
    list_filter = ['scope', 'category', 'status', 'batch__source_type']

admin.site.register(ValidationFlag)
admin.site.register(AuditEvent)
