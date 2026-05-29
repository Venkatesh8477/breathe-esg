# Decisions

## SAP: Why flat file CSV (MB51 format) over IDoc / OData / BAPI

**Ambiguity:** SAP offers many integration paths. IDoc, OData (via SAP Gateway), BAPI, and flat file exports all exist.

**Decision:** MB51 flat file CSV export.

**Why:** A sustainability analyst at a client company does not have SAP developer access. They get their data by asking the SAP admin to run a transaction (MB51 = material document list, ME2M = purchase orders by material) and export as a text/CSV file. IDoc requires middleware (SAP PI/PO or BTP Integration Suite) and a receiving system registered in the SAP landscape — not realistic for a prototype. OData requires SAP Gateway activated (not on by default in older ECC systems). BAPI requires RFC access and a developer SDK. The flat file export is what sustainability teams actually do in practice.

**German column headers:** SAP's default locale is German. Headers like `Buchungsdatum` (posting date), `Menge` (quantity), `Einheit` (unit), `Werk` (plant) are standard in un-customized SAP exports. The parser handles both German and English column names via a mapping dict.

**Subset handled:** Fuel and energy-related procurement only — records where the material description contains recognizable fuel type keywords. Non-fuel procurement (office supplies, equipment) is ignored because Scope 3 purchased goods requires a separate spend-based methodology we are not implementing.

**What I'd ask the PM:** Do clients have customized SAP layouts (renamed columns, additional fields)? Is the output always ANSI or can it be UTF-8/Latin-1 depending on SAP system locale? Do we need to handle purchase orders (ME2M) as well as goods movements (MB51), and how do we de-duplicate if both are provided?

---

## Utility: Why portal CSV over PDF / API

**Ambiguity:** Utility data comes as PDF bills, portal CSV exports, or (rarely) an API.

**Decision:** Portal CSV export modeled on Green Button / Urjanet format.

**Why:** PDF parsing requires OCR or layout-aware parsing (pdfplumber, camelot) which is brittle — every utility's PDF bill has a different layout. Utility APIs exist (Green Button Connect, Urjanet Connect) but require OAuth partnerships with each utility company — impractical for a prototype. The CSV export from utility portals is the actual workflow: the facilities manager logs into their utility account, navigates to billing history, downloads a CSV. This is a deterministic, standardized output that sustainability teams use routinely.

**Green Button format:** US utilities that have adopted Green Button use a standard XML or CSV structure with meter ID, billing interval start/end, consumption in kWh or MWh. I modeled the CSV on this standard because it's the most likely format a US/EU enterprise would encounter.

**Billing period handling:** Billing periods are explicitly modeled with `period_start` and `period_end` rather than forcing a single `activity_date`. A billing period for one meter might be Dec 18 – Jan 19, while another is Jan 1 – Jan 31. Storing both dates preserves the actual reading window for emissions accounting (which calendar quarter does this belong to is a downstream decision).

**What I'd ask the PM:** Are all client sites on the same utility, or is there one CSV per utility per site? Does the facilities team consolidate across sites before sending, or do we get one file per meter? What happens when a billing period straddles a reporting year boundary?

---

## Travel: Why Concur/Navan CSV export over API

**Ambiguity:** Navan has a REST API; Concur has an XML/JSON API. Both also offer trip report CSV exports.

**Decision:** CSV export modeled on Navan trip report format.

**Why:** Both APIs require enterprise-level OAuth with admin credentials scoped to the company's travel management account. The CSV export is what sustainability teams actually use — they request a "Trip Report" from their travel admin covering a date range and get a flat file with one row per trip segment. This is documented in both Concur and Navan's help centers as the standard sustainability reporting workflow.

**Flight distance calculation:** Navan trip reports include IATA airport codes but not always distance. When distance is absent, I calculate it using the haversine formula on a lookup table of ~50 common business travel airports. This is the same approach used by most carbon accounting tools (DEFRA guidelines suggest using great-circle distance × 1.09 routing factor). When both origin and destination airport codes are recognized, a distance is calculated. When one is unknown, the record is flagged.

**Hotel units as nights:** Hotels are stored as nights rather than square meters or room-nights because that's what travel platforms expose. The emission factor for hotels (applied later) typically uses nights as the activity unit anyway.

**Subset handled:** Flights, hotels, ground transport (taxi, rental car, rail). Air freight and international shipping (also Scope 3 Category 4) are not handled — they require different data sources (freight forwarder manifests, shipping APIs).

**What I'd ask the PM:** Does the client use Navan or Concur specifically, or something else (Cytric, TravelPerk, AmTrav)? Are personal trips included in the export or filtered out? How do we handle cancelled trips that appear in the export?

---

## Status machine design

**Decision:** Four states — `pending → flagged | approved | rejected`. Approved records are locked.

**Why:** The PM's brief says "let analysts review and sign off before it goes to auditors." This implies a one-way gate: once approved, the record is authoritative. A rejected record is excluded from reporting. A flagged record stays in the queue for further review. The `locked` boolean on top of `approved` status is a belt-and-suspenders protection — the API rejects changes to locked records regardless of how the status field was set.

**Tradeoff:** This is a single-analyst approval model. There is no "reviewed by analyst, pending manager sign-off" state. See TRADEOFFS.md.

---

## SQLite in development

**Decision:** Using SQLite locally, PostgreSQL for production (documented in deploy config).

**Why:** SQLite requires zero setup and is sufficient for a prototype with a single analyst. The ORM abstracts the difference. For production on Railway/Render, the DATABASE_URL environment variable switches to PostgreSQL automatically.
