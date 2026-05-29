# Tradeoffs — Three Things Deliberately Not Built

## 1. CO2e Calculation Engine

**What it would look like:** Multiply normalized quantity by an emission factor (e.g., 2.68 kg CO2e per liter of diesel, UK grid intensity of 0.207 kg CO2e/kWh, DEFRA flight factors by cabin class and distance band) to produce a CO2e figure per record.

**Why not built:**

Emission factors are not static. They depend on:
- Fuel type (diesel vs. HVO diesel have different factors)
- Grid region and year (UK grid intensity dropped 60% in 10 years)
- Methodology (AR4 vs. AR5 GWP100 values differ by ~14% for methane)
- Scope 3 category (Category 6 business travel vs. Category 4 upstream transport)
- Radiative forcing inclusion (flights: with or without RF multiplier is a contested methodology choice)

Building this correctly requires a versioned emission factor database, a methodology selection layer, and a recalculation mechanism when factors are updated. That is a significant product in itself (it's essentially what Ecometrica, Sphera, and similar tools are).

The right boundary for this prototype is: store normalized activity quantities and scope classification. Apply emission factors as a separate, auditable transformation step. This is also what regulators want — the activity data and the conversion factors should be separately traceable.

**What was built instead:** Quantities are stored in base units (liters, kWh, km, nights) ready for factor application. Scope and category are explicitly labeled to make factor lookup deterministic.

---

## 2. Multi-step Approval Workflow (Analyst → Manager → Auditor)

**What it would look like:** A record goes through multiple approval stages — an analyst reviews, a sustainability manager signs off, an external auditor access-reviews before the data is exported to a reporting framework (GHG Protocol, CDP, CSRD).

**Why not built:**

The PM's brief says "let analysts review and sign off." That implies a single-reviewer workflow is the right scope for this prototype. Multi-step approval requires:
- Role-based permissions (analyst vs. manager vs. auditor roles)
- Conditional transitions (only a manager can approve what an analyst has already reviewed)
- Notification/escalation logic
- Possibly external auditor access controls (read-only, no login)

This is meaningful product work that would double the scope of the project. More importantly, getting the data model right (immutable raw records, locked approved records, append-only audit trail) is the prerequisite for any approval workflow — and that foundation is built. Adding stages is additive once the model is correct.

**What was built instead:** Single analyst review with approve/reject/flag, full audit trail on every state change, and a locked state on approved records. The audit trail is designed to support multi-step workflows when added later.

---

## 3. Real-time / Scheduled API Ingestion from Source Systems

**What it would look like:** A scheduled job that pulls from SAP OData, Green Button Connect, or the Navan API on a daily/weekly cadence without manual file uploads.

**Why not built:**

Each source requires separate integration work:
- **SAP OData:** Requires the client's SAP Gateway URL, client credentials, RFC authorization, and knowledge of which OData service is available (standard S/4HANA vs. custom ECC). This is a multi-week IT engagement per client, not something a prototype can fake.
- **Green Button Connect:** Requires OAuth registration with each utility company. Most US utilities support this, but it requires approved third-party application status.
- **Navan/Concur API:** Requires admin-level API key scoped to the client's corporate account. Navan's API is enterprise-tier gated.

More fundamentally: **file upload is the actual workflow for the analyst personas described in the brief.** Sustainability coordinators at enterprise companies do not have SAP API access. They get files from IT on a monthly basis. Building API pull before the manual workflow is solid would be premature optimization.

**What was built instead:** File upload with source-type selection covers the actual workflow. The ingestion architecture (batch → raw records → normalized records) is designed so that API-sourced records could be written by a separate ingestor that bypasses the file upload step but reuses the same `process_batch` service.
