# Data Model

## Core Design Principles

1. **Raw records are immutable.** Every ingested row is stored verbatim in `RawRecord` before any parsing occurs. This means we can always reconstruct what we received, even if our normalization logic changes.

2. **Source-of-truth tracking.** Every `EmissionRecord` points to its `RawRecord`, its `IngestionBatch`, and its `Tenant`. You can always answer: which file produced this row, when, who uploaded it, and what the original value was.

3. **Approved records are locked.** Once an analyst approves a record, `locked = True` and the API rejects any further status changes. This matches the audit requirement — once signed off, a record is immutable.

4. **Append-only audit trail.** `AuditEvent` rows are never updated or deleted. Every status change creates a new event with `previous_status` and `new_status`.

---

## Tables

### Tenant
Multi-tenancy root. Every record belongs to a tenant. Identified by a slug (e.g., `acme-corp`).

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| name | CharField | Display name |
| slug | SlugField | URL-safe unique identifier |
| created_at | DateTimeField | |

### IngestionBatch
One row per file upload. Tracks status of the parse job.

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| tenant | FK → Tenant | |
| source_type | CharField | `sap`, `utility`, `travel` |
| filename | CharField | Original filename |
| uploaded_by | FK → User | |
| uploaded_at | DateTimeField | |
| status | CharField | `pending`, `processing`, `done`, `failed` |
| total_rows | IntegerField | Rows found in file |
| parsed_rows | IntegerField | Rows successfully parsed |
| failed_rows | IntegerField | Rows that threw exceptions |
| error_message | TextField | If batch-level parse fails |

### RawRecord
Verbatim copy of each CSV row as a JSON object. Never mutated.

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| batch | FK → IngestionBatch | |
| row_index | IntegerField | Row position in original file |
| raw_data | JSONField | Entire row as dict |
| ingested_at | DateTimeField | |

Unique constraint on `(batch, row_index)` prevents double-ingestion.

### EmissionRecord
Normalized emission activity. One per `RawRecord`.

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| raw_record | OneToOne → RawRecord | Always traceable to source |
| tenant | FK → Tenant | |
| batch | FK → IngestionBatch | |
| scope | CharField | `scope1`, `scope2`, `scope3` |
| category | CharField | `fuel`, `electricity`, `flight`, `hotel`, `ground_transport` |
| quantity | Decimal(14,4) | Always in base unit |
| unit_normalized | CharField | `liters`, `kWh`, `km`, `nights` |
| original_quantity | CharField | Pre-normalization value as string |
| original_unit | CharField | Pre-normalization unit |
| activity_date | Date | For point-in-time records |
| period_start / period_end | Date | For billing-period records (utility) |
| site_code | CharField | Plant code, meter ID, airport pair |
| site_name | CharField | Human-readable site name |
| description | TextField | Derived description |
| supplier_vendor | CharField | SAP vendor, traveler name, etc. |
| status | CharField | `pending`, `flagged`, `approved`, `rejected` |
| reviewed_by | FK → User | |
| reviewed_at | DateTimeField | |
| review_note | TextField | Analyst's reason |
| locked | BooleanField | True once approved — API blocks changes |
| created_at / updated_at | DateTimeField | |

**Scope classification:**
- Scope 1: SAP fuel records (direct combustion by the company)
- Scope 2: Utility electricity records (purchased energy)
- Scope 3: Corporate travel (value chain / business travel emissions)

**Unit normalization:**
- Fuel: everything → liters (1 US gal = 3.78541 L, 1 kg ≈ 1.136 L for diesel, 1 M3 = 1000 L)
- Electricity: everything → kWh (1 MWh = 1000 kWh)
- Flights / ground: km (calculated via haversine for airport-code-only records)
- Hotels: nights (dimensionless count)

The choice to store normalized quantities without CO2e conversion is deliberate — emission factors depend on fuel type, grid region, year, and methodology (GWP values change). Storing activity data in base units means the CO2e calculation can be applied later without re-ingestion.

### ValidationFlag
One or more flags per `EmissionRecord`, created at parse time.

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| emission_record | FK → EmissionRecord | |
| flag_type | CharField | `missing_field`, `unknown_unit`, `outlier`, `unknown_site`, `date_parse_error`, `negative_value` |
| field_name | CharField | Which field triggered the flag |
| detail | TextField | Human-readable explanation |
| created_at | DateTimeField | |

Outlier detection: after all rows in a batch are parsed, quantities are compared against mean ± 3σ. Records above this threshold get an `outlier` flag. This catches data entry errors (e.g., the 47,000 L diesel row in the SAP sample).

### AuditEvent
Append-only log. Never updated, never deleted.

| Field | Type | Notes |
|---|---|---|
| id | PK | |
| emission_record | FK → EmissionRecord | |
| action | CharField | `created`, `approved`, `rejected`, `flagged`, `note_added` |
| performed_by | FK → User | |
| performed_at | DateTimeField | auto |
| previous_status | CharField | |
| new_status | CharField | |
| note | TextField | Analyst's note text |

---

## What This Model Does Not Cover

- **CO2e calculation** — emission factors are not stored. This is intentional (see TRADEOFFS.md).
- **Emission factor versioning** — when factors change (e.g., GWP100 updates), past records should not be silently recalculated.
- **Document attachments** — original PDFs or raw files are not stored, only the parsed CSV content.
- **Approval workflows** — only one review state per record. Multi-step approval chains (analyst → manager → auditor) are not modeled.
