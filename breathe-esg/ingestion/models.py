from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    SOURCE_SAP = 'sap'
    SOURCE_UTILITY = 'utility'
    SOURCE_TRAVEL = 'travel'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Fuel & Procurement'),
        (SOURCE_UTILITY, 'Utility Electricity'),
        (SOURCE_TRAVEL, 'Corporate Travel'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=500)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_rows = models.IntegerField(default=0)
    parsed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tenant.name} / {self.source_type} / {self.uploaded_at:%Y-%m-%d}"


class RawRecord(models.Model):
    """Verbatim copy of each row as ingested — never mutated after creation."""
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='raw_records')
    row_index = models.IntegerField()
    raw_data = models.JSONField()
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'row_index')

    def __str__(self):
        return f"Raw {self.batch_id}:{self.row_index}"


class EmissionRecord(models.Model):
    SCOPE_1 = 'scope1'
    SCOPE_2 = 'scope2'
    SCOPE_3 = 'scope3'
    SCOPE_CHOICES = [
        (SCOPE_1, 'Scope 1 — Direct combustion'),
        (SCOPE_2, 'Scope 2 — Purchased electricity'),
        (SCOPE_3, 'Scope 3 — Value chain / travel'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_FLAGGED = 'flagged'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_FLAGGED, 'Flagged'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    CATEGORY_FUEL = 'fuel'
    CATEGORY_ELECTRICITY = 'electricity'
    CATEGORY_FLIGHT = 'flight'
    CATEGORY_HOTEL = 'hotel'
    CATEGORY_GROUND = 'ground_transport'
    CATEGORY_CHOICES = [
        (CATEGORY_FUEL, 'Fuel'),
        (CATEGORY_ELECTRICITY, 'Electricity'),
        (CATEGORY_FLIGHT, 'Flight'),
        (CATEGORY_HOTEL, 'Hotel'),
        (CATEGORY_GROUND, 'Ground Transport'),
    ]

    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name='emission_record')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='emission_records')

    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Normalized quantities — all stored in base units
    # fuel: liters | electricity: kWh | flight/ground: km | hotel: nights
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    unit_normalized = models.CharField(max_length=20)
    original_quantity = models.CharField(max_length=100)
    original_unit = models.CharField(max_length=50)

    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    site_code = models.CharField(max_length=100, blank=True)
    site_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    supplier_vendor = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Locked once approved — no further edits allowed
    locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tenant.name} / {self.scope} / {self.category} / {self.activity_date}"


class ValidationFlag(models.Model):
    FLAG_MISSING_FIELD = 'missing_field'
    FLAG_UNKNOWN_UNIT = 'unknown_unit'
    FLAG_OUTLIER = 'outlier'
    FLAG_UNKNOWN_SITE = 'unknown_site'
    FLAG_DATE_PARSE = 'date_parse_error'
    FLAG_NEGATIVE = 'negative_value'
    FLAG_CHOICES = [
        (FLAG_MISSING_FIELD, 'Missing required field'),
        (FLAG_UNKNOWN_UNIT, 'Unrecognized unit'),
        (FLAG_OUTLIER, 'Statistical outlier (>3σ from mean)'),
        (FLAG_UNKNOWN_SITE, 'Unknown site/plant code'),
        (FLAG_DATE_PARSE, 'Date parse error'),
        (FLAG_NEGATIVE, 'Negative quantity'),
    ]

    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='flags')
    flag_type = models.CharField(max_length=30, choices=FLAG_CHOICES)
    field_name = models.CharField(max_length=100, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.flag_type} on record {self.emission_record_id}"


class AuditEvent(models.Model):
    """Append-only audit trail — rows are never updated or deleted."""
    ACTION_CREATED = 'created'
    ACTION_APPROVED = 'approved'
    ACTION_REJECTED = 'rejected'
    ACTION_FLAGGED = 'flagged'
    ACTION_NOTE_ADDED = 'note_added'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Record created'),
        (ACTION_APPROVED, 'Record approved'),
        (ACTION_REJECTED, 'Record rejected'),
        (ACTION_FLAGGED, 'Record flagged'),
        (ACTION_NOTE_ADDED, 'Note added'),
    ]

    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_events')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['performed_at']

    def __str__(self):
        return f"{self.action} on {self.emission_record_id} at {self.performed_at}"
