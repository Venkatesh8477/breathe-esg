"""
Orchestrates parsing + saving for each upload batch.
Applies outlier detection after all rows are parsed.
"""
import io
import math
import numpy as np
import pandas as pd
from decimal import Decimal
from django.utils import timezone


def sanitize_for_json(obj):
    """Convert pandas/numpy types to plain Python for JSONField storage."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    return obj

from .models import IngestionBatch, RawRecord, EmissionRecord, ValidationFlag, AuditEvent
from .parsers import parse_sap_csv, parse_utility_csv, parse_travel_csv


PARSERS = {
    IngestionBatch.SOURCE_SAP: parse_sap_csv,
    IngestionBatch.SOURCE_UTILITY: parse_utility_csv,
    IngestionBatch.SOURCE_TRAVEL: parse_travel_csv,
}


def process_batch(batch, file_bytes):
    batch.status = IngestionBatch.STATUS_PROCESSING
    batch.save(update_fields=['status'])

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        batch.status = IngestionBatch.STATUS_FAILED
        batch.error_message = f"Could not read CSV: {e}"
        batch.save(update_fields=['status', 'error_message'])
        return

    parser = PARSERS[batch.source_type]
    try:
        parsed_rows = parser(df)
    except Exception as e:
        batch.status = IngestionBatch.STATUS_FAILED
        batch.error_message = f"Parse error: {e}"
        batch.save(update_fields=['status', 'error_message'])
        return

    batch.total_rows = len(parsed_rows)

    # Outlier detection: flag records where quantity > mean + 3*std
    quantities = [float(r['quantity']) for r in parsed_rows if r.get('quantity') is not None]
    if len(quantities) > 3:
        mean_q = np.mean(quantities)
        std_q = np.std(quantities)
        outlier_threshold = mean_q + 3 * std_q
    else:
        outlier_threshold = None

    parsed_count = 0
    failed_count = 0

    for row_data in parsed_rows:
        raw, created = RawRecord.objects.get_or_create(
            batch=batch,
            row_index=row_data['row_index'],
            defaults={'raw_data': sanitize_for_json(row_data['raw'])},
        )

        # Skip rows already processed (e.g. retry after partial failure)
        if not created and hasattr(raw, 'emission_record'):
            parsed_count += 1
            continue

        flags = row_data.get('flags', [])

        if outlier_threshold and float(row_data.get('quantity', 0)) > outlier_threshold:
            flags.append({
                'type': 'outlier',
                'field': 'quantity',
                'detail': f"Value {row_data['quantity']:.2f} exceeds mean+3σ threshold ({outlier_threshold:.2f})"
            })

        initial_status = EmissionRecord.STATUS_FLAGGED if flags else EmissionRecord.STATUS_PENDING

        try:
            record = EmissionRecord.objects.create(
                raw_record=raw,
                tenant=batch.tenant,
                batch=batch,
                scope=row_data.get('scope', 'scope3'),
                category=row_data.get('category', 'fuel'),
                quantity=row_data.get('quantity', Decimal('0')),
                unit_normalized=row_data.get('unit_normalized', ''),
                original_quantity=str(row_data.get('original_quantity', '')),
                original_unit=row_data.get('original_unit', ''),
                activity_date=row_data.get('activity_date'),
                period_start=row_data.get('period_start'),
                period_end=row_data.get('period_end'),
                site_code=row_data.get('site_code', ''),
                site_name=row_data.get('site_name', ''),
                description=row_data.get('description', ''),
                supplier_vendor=row_data.get('supplier_vendor', ''),
                status=initial_status,
            )

            for flag in flags:
                ValidationFlag.objects.create(
                    emission_record=record,
                    flag_type=flag['type'],
                    field_name=flag.get('field', ''),
                    detail=flag.get('detail', ''),
                )

            AuditEvent.objects.create(
                emission_record=record,
                action=AuditEvent.ACTION_CREATED,
                performed_by=batch.uploaded_by,
                new_status=initial_status,
            )

            parsed_count += 1

        except Exception:
            failed_count += 1

    batch.parsed_rows = parsed_count
    batch.failed_rows = failed_count
    batch.status = IngestionBatch.STATUS_DONE
    batch.save(update_fields=['parsed_rows', 'failed_rows', 'status'])
