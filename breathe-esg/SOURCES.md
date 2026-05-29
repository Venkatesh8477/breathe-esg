# Sources — Research and Sample Data Rationale

## 1. SAP Fuel & Procurement

**Format researched:** SAP MB51 (Material Document List) flat file export from SAP ERP / S/4HANA.

**What I learned:**
- SAP's default export locale is German. Column headers like `Buchungsdatum` (posting date), `Menge` (quantity), `Einheit` (unit of measure), `Werk` (plant), `Bezeichnung` (description) appear in un-customized exports. Some SAP installations are configured with English headers — the parser handles both.
- Units in SAP are SAP-internal unit codes: `L` (liter), `GAL` (US gallon), `KG` (kilogram), `M3` (cubic meter), `CBM` (also cubic meter, regional variant). There is no single standard.
- Plant codes are 4-digit internal identifiers (e.g., `1010` = Frankfurt HQ). They are meaningless without a plant master lookup table. The parser has a hardcoded lookup table representing a realistic enterprise with plants in Frankfurt, Munich, London, Amsterdam, and Singapore.
- Dates use DD.MM.YYYY in German locale exports. Some exports use MM/DD/YYYY or YYYY-MM-DD depending on SAP system settings.
- Movement type 101 = goods receipt. In the context of fuel procurement, a goods receipt against a purchase order is the trigger for recording consumption.

**What the sample data looks like and why:**
- 28 rows covering Jan–May 2024 for 5 plants.
- Mix of DIESEL, BENZIN (petrol), ERDGAS (natural gas), HEIZÖL/HEIZOL (heating oil), LPG across plants.
- Intentional issues: one row with GAL units (row 14) to test unit conversion, one row with a negative quantity (row 23 — a return/reversal, common in SAP), one row with unknown plant code 9999 (a test record), one row with quantity 47,000 L (row 17 — intended as an outlier to trigger the 3σ detection).
- HEIZÖL appears both with and without the umlaut (row 27: HEIZOL) — common encoding issue in CSV exports from older SAP systems.

**What would break in real deployment:**
- SAP custom layouts: clients with Z-tables or custom transaction variants have completely different column names.
- Encoding: SAP exports in Windows-1252 or ISO-8859-1 (Latin-1), not UTF-8. Umlauts break if the parser assumes UTF-8 without explicit encoding handling.
- Multiple cost centers or profit centers per material document: the flat file collapses these into one row but actual procurement can split across multiple account assignments.
- The plant-code lookup table is hardcoded. In production, this must come from the client's SAP plant master data (table T001W).

---

## 2. Utility Electricity

**Format researched:** Green Button CSV (US standard adopted by FERC and most major US utilities), and Urjanet portal export format (used by UK and EU utilities).

**What I learned:**
- Green Button defines a standard XML schema (ESPI) and a derived CSV format. The CSV has: meter ID, interval start/end timestamps, consumption in kWh, demand in kW.
- Billing periods are not calendar months. Utilities bill based on meter reading cycles — typically 28–35 day cycles offset by meter location. A meter at one site might read Dec 18 – Jan 19, while another site reads Jan 1 – Jan 31.
- Mixed units are common in EU contexts: German industrial customers (HV connection) receive bills in MWh; small offices get kWh. Singapore uses kWh but their tariff structure (C2S, governed by SP Group) is different from European structures.
- Tariff codes appear in exports: HT-Gewerbe (German: high-tariff commercial), NT-Gewerbe (low-tariff commercial), HT-Industrie (industrial high-tariff). These are meaningful for carbon accounting because time-of-use tariffs imply different grid mix.
- Demand charges (kW, not kWh) appear as separate line items on industrial meters. Demand is not an activity quantity for GHG purposes — it's a billing mechanism. The parser captures it but does not include it in the normalized emission record.

**What the sample data looks like and why:**
- 24 rows covering 5 sites (Frankfurt HQ with 2 meters + EV parking, Munich Plant with 2 meters, London Office, Amsterdam Warehouse, Singapore Hub) over Jan–Apr 2024.
- Frankfurt and Munich have overlapping non-calendar billing cycles (e.g., Frankfurt HQ bills Dec 18 – Jan 19, then Jan 19 – Feb 21).
- Singapore uses MWh units rather than kWh — tests the MWh→kWh conversion path.
- One row (Frankfurt EV parking, row 19) has empty consumption — tests the missing-field flag.
- One row (Frankfurt Unknown Meter, row 24) has no tariff value — tests missing field handling.
- London and Amsterdam have clean calendar-month periods because UK/NL utilities tend to align billing with calendar months.

**What would break in real deployment:**
- PDF bills: most SME customers don't have access to a portal CSV export. They receive a PDF. Parsing PDF bills requires OCR and layout detection — brittle and format-specific.
- Multi-currency: UK bills are in GBP, German bills in EUR, Singapore in SGD. The parser ignores cost columns, but a real implementation needs to handle this.
- Reactive energy (kVAr): industrial meters include reactive power components that don't map to kWh. These appear in exports and need to be filtered.
- Sub-metering: large facilities have main meters and sub-meters. Summing both causes double-counting. The sample data doesn't include this edge case.

---

## 3. Corporate Travel

**Format researched:** Navan (formerly TripActions) Trip Report CSV export; Concur Expense / Travel Report XML and CSV export.

**What I learned:**
- Both Navan and Concur offer a "Trip Report" or "Expense Report" CSV downloadable by travel admins with date range and department filters.
- The Navan export has columns: trip_id, traveler_name, department, travel_date, category (Flight/Hotel/Car/Rail), origin, destination, class, cost_usd, booking_ref. Distance is not provided — only airport codes for flights.
- Concur's format is similar but uses a different category taxonomy (AIR, HTL, CAR, TRN) and sometimes includes distance for car rentals.
- IATA airport codes are the standard identifier for flights. Distances must be calculated from coordinates, not looked up from a table maintained by the platform.
- "Business class" vs "economy class" matters for emission factors — Business is approximately 2.9× economy on a per-km basis (due to larger seat footprint) per DEFRA 2023 guidance.
- Hotel stays are recorded as nights, not check-in/check-out timestamps, in most export formats.
- Ground transport is heterogeneous: taxi, rental car, rail, and company car all appear as "Ground Transport" or subcategories. Emission factors differ significantly (rail ≈ 0.041 kg CO2e/km vs. rental car ≈ 0.168 kg CO2e/km).
- Distances for ground transport are often absent from the export (row 39 in sample data: a 15 km local taxi with no origin/destination).

**What the sample data looks like and why:**
- 45 trip segments for 8 fictional travelers across Engineering, Sales, Finance, Operations, HR, Product, Legal.
- Long-haul business class flights (FRA-SIN, NRT-LAX) have no pre-given distance — haversine is calculated from the IATA lookup table.
- Short intra-European flights (FRA-LHR, FRA-CDG) are present to contrast with long-haul.
- Hotel stays paired with flights to show multi-segment trips (same trip_id convention).
- Ground transport row 39 has no origin/destination and a pre-given 15 km distance — tests the path where we trust the provided distance.
- One ground transport row (AMS→FRA, 480 km) uses a realistic road distance rather than a straight-line distance — representing that ground transport is reported as driven distance, not haversine.
- Traveler `Sarah Chen` makes multiple trips to Singapore and Bombay — representing an engineering resource doing multiple data center visits.

**What would break in real deployment:**
- Unknown airport codes: the haversine lookup table has ~50 airports. Any route to a regional airport (e.g., BHX, BRS, LBA) would fail and be flagged. Production requires a full IATA database (~10,000 airports).
- Cancelled trips: Navan/Concur exports sometimes include cancelled or voided bookings. The parser has no way to detect these without a `status` column.
- Multi-leg itineraries: a connection flight (JFK → LHR via CDG) may appear as two rows or one row depending on how the booking was made. Double-counting risk.
- Currency conversion: cost_usd is not used in emission calculations, but if a travel budget report is overlaid, FX rates at booking date matter.
- Personal vs. business trips: some corporate platforms include personal bookings made on the company account. A `trip_type` filter is needed but not always present.
