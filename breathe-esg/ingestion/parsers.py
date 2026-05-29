"""
Parsers for each data source. Each parser returns a list of dicts with normalized fields.
Design decisions documented in DECISIONS.md.
"""
import math
import pandas as pd
from datetime import date
from decimal import Decimal


# SAP plant code lookup — in production this comes from a config table
SAP_PLANT_CODES = {
    '1010': 'Frankfurt HQ',
    '1020': 'Munich Plant',
    '2010': 'London Office',
    '2020': 'Amsterdam Warehouse',
    '3010': 'Singapore Hub',
    '9999': 'Unknown/Test',
}

# SAP material to fuel type mapping
SAP_MATERIAL_FUEL_MAP = {
    'DIESEL': 'diesel',
    'BENZIN': 'petrol',      # German
    'PETROL': 'petrol',
    'ERDGAS': 'natural_gas', # German: natural gas
    'GAS': 'natural_gas',
    'HEIZÖL': 'heating_oil', # German
    'HEIZOL': 'heating_oil',
    'LPG': 'lpg',
}

# Unit normalization to liters (fuel) or kWh (electricity) or km (travel)
FUEL_UNIT_TO_LITERS = {
    'L': Decimal('1'),
    'LTR': Decimal('1'),
    'LITER': Decimal('1'),
    'GAL': Decimal('3.78541'),   # US gallon
    'GALLON': Decimal('3.78541'),
    'KG': Decimal('1.136'),      # approximate for diesel density
    'M3': Decimal('1000'),
    'CBM': Decimal('1000'),
}

ELEC_UNIT_TO_KWH = {
    'KWH': Decimal('1'),
    'MWH': Decimal('1000'),
    'GWH': Decimal('1000000'),
}

# IATA airport coordinates for haversine distance calculation
AIRPORT_COORDS = {
    'LHR': (51.4775, -0.4614),
    'JFK': (40.6413, -73.7781),
    'CDG': (49.0097, 2.5479),
    'DXB': (25.2532, 55.3657),
    'SIN': (1.3644, 103.9915),
    'BOM': (19.0896, 72.8656),
    'DEL': (28.5562, 77.1000),
    'SFO': (37.6213, -122.3790),
    'ORD': (41.9742, -87.9073),
    'LAX': (33.9425, -118.4081),
    'HKG': (22.3080, 113.9185),
    'AMS': (52.3105, 4.7683),
    'FRA': (50.0379, 8.5622),
    'MUC': (48.3537, 11.7750),
    'BLR': (13.1979, 77.7063),
    'MAA': (12.9941, 80.1709),
    'HYD': (17.2313, 78.4298),
    'CCU': (22.6520, 88.4467),
    'PNQ': (18.5822, 73.9197),
    'BBI': (20.2444, 85.8177),
    'NBO': (-1.3192, 36.9275),
    'JNB': (-26.1392, 28.2460),
    'GRU': (-23.4356, -46.4731),
    'MXP': (45.6306, 8.7281),
    'ZRH': (47.4582, 8.5555),
    'DUS': (51.2895, 6.7668),
    'HAM': (53.6304, 9.9882),
    'VIE': (48.1103, 16.5697),
    'CPH': (55.6180, 12.6508),
    'OSL': (60.1976, 11.1004),
    'ARN': (59.6519, 17.9186),
    'HEL': (60.3172, 24.9633),
    'WAW': (52.1657, 20.9671),
    'IST': (40.9769, 28.8146),
    'DOH': (25.2609, 51.6138),
    'AUH': (24.4330, 54.6511),
    'KUL': (2.7456, 101.7099),
    'SYD': (-33.9461, 151.1772),
    'MEL': (-37.6690, 144.8410),
    'PEK': (40.0799, 116.6031),
    'PVG': (31.1443, 121.8083),
    'ICN': (37.4602, 126.4407),
    'NRT': (35.7720, 140.3929),
    'YYZ': (43.6777, -79.6248),
    'YVR': (49.1947, -123.1792),
    'MEX': (19.4363, -99.0721),
    'EZE': (-34.8222, -58.5358),
    'SCL': (-33.3930, -70.7858),
    'BOG': (4.7016, -74.1469),
    'LIM': (-12.0219, -77.1143),
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_sap_csv(df):
    """
    Parses SAP MB51 flat file export (material document list).
    Columns use German headers in SAP default locale.
    Dates in DD.MM.YYYY. Units inconsistent across plants.
    """
    results = []
    errors = []

    COLUMN_MAP = {
        'Buchungsdatum': 'posting_date',
        'Belegdatum': 'document_date',
        'Menge': 'quantity',
        'Einheit': 'unit',
        'Werk': 'plant_code',
        'Bezeichnung': 'material_description',
        'Materialnummer': 'material_number',
        'Kostenstelle': 'cost_center',
        'Bewegungsart': 'movement_type',
        'Lieferant': 'vendor',
    }

    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    for idx, row in df.iterrows():
        record = {'row_index': idx, 'flags': [], 'raw': row.to_dict()}

        # Parse date
        date_val = None
        date_str = str(row.get('posting_date', '') or row.get('document_date', '')).strip()
        if date_str and date_str != 'nan':
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
                try:
                    date_val = pd.to_datetime(date_str, format=fmt).date()
                    break
                except Exception:
                    continue
            if not date_val:
                record['flags'].append({'type': 'date_parse_error', 'field': 'posting_date', 'detail': f'Could not parse: {date_str}'})

        # Parse quantity
        qty_raw = str(row.get('quantity', '')).strip().replace(',', '.')
        try:
            qty = Decimal(qty_raw)
            if qty < 0:
                record['flags'].append({'type': 'negative_value', 'field': 'quantity', 'detail': f'Value: {qty}'})
        except Exception:
            record['flags'].append({'type': 'missing_field', 'field': 'quantity', 'detail': f'Could not parse: {qty_raw}'})
            qty = Decimal('0')

        # Parse unit
        unit_raw = str(row.get('unit', '')).strip().upper()
        multiplier = FUEL_UNIT_TO_LITERS.get(unit_raw)
        if not multiplier:
            record['flags'].append({'type': 'unknown_unit', 'field': 'unit', 'detail': f'Unrecognized unit: {unit_raw}'})
            multiplier = Decimal('1')

        qty_normalized = qty * multiplier

        # Plant lookup
        plant_code = str(row.get('plant_code', '')).strip()
        site_name = SAP_PLANT_CODES.get(plant_code, '')
        if not site_name:
            record['flags'].append({'type': 'unknown_site', 'field': 'plant_code', 'detail': f'Unknown plant: {plant_code}'})

        # Material → fuel type
        mat_desc = str(row.get('material_description', '')).strip().upper()
        fuel_type = 'unknown'
        for key, val in SAP_MATERIAL_FUEL_MAP.items():
            if key in mat_desc:
                fuel_type = val
                break

        record.update({
            'scope': 'scope1',
            'category': 'fuel',
            'activity_date': date_val,
            'quantity': qty_normalized,
            'unit_normalized': 'liters',
            'original_quantity': qty_raw,
            'original_unit': unit_raw,
            'site_code': plant_code,
            'site_name': site_name,
            'description': f"{fuel_type} — {row.get('material_description', '')}",
            'supplier_vendor': str(row.get('vendor', '')).strip(),
        })

        results.append(record)

    return results


def parse_utility_csv(df):
    """
    Parses Green Button / utility portal CSV export.
    Billing periods don't align with calendar months.
    Units may be kWh or MWh. Meter IDs identify sites.
    """
    results = []

    COLUMN_MAP = {
        'meter_id': 'meter_id',
        'Meter ID': 'meter_id',
        'site_name': 'site_name',
        'Site Name': 'site_name',
        'billing_start': 'billing_start',
        'Billing Start': 'billing_start',
        'billing_end': 'billing_end',
        'Billing End': 'billing_end',
        'consumption_kwh': 'consumption',
        'Consumption (kWh)': 'consumption',
        'consumption_mwh': 'consumption_mwh',
        'Consumption (MWh)': 'consumption_mwh',
        'unit': 'unit',
        'Unit': 'unit',
        'tariff': 'tariff',
        'Tariff': 'tariff',
        'account_number': 'account_number',
        'Account Number': 'account_number',
    }

    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    for idx, row in df.iterrows():
        record = {'row_index': idx, 'flags': [], 'raw': row.to_dict()}

        # Parse billing period
        start_date = None
        end_date = None
        for col, target in [('billing_start', 'start'), ('billing_end', 'end')]:
            val = str(row.get(col, '')).strip()
            if val and val != 'nan':
                try:
                    parsed = pd.to_datetime(val).date()
                    if target == 'start':
                        start_date = parsed
                    else:
                        end_date = parsed
                except Exception:
                    record['flags'].append({'type': 'date_parse_error', 'field': col, 'detail': f'Could not parse: {val}'})

        if not start_date:
            record['flags'].append({'type': 'missing_field', 'field': 'billing_start', 'detail': 'Missing billing start date'})

        # Determine consumption and unit
        unit_raw = str(row.get('unit', 'kWh')).strip()
        consumption_raw = None

        if 'consumption_mwh' in df.columns and str(row.get('consumption_mwh', '')).strip() not in ('', 'nan'):
            try:
                consumption_raw = Decimal(str(row.get('consumption_mwh', '0')).replace(',', ''))
                unit_raw = 'MWh'
            except Exception:
                pass

        if consumption_raw is None:
            raw_val = str(row.get('consumption', '')).strip()
            if raw_val and raw_val.lower() not in ('nan', 'none', ''):
                try:
                    consumption_raw = Decimal(raw_val.replace(',', ''))
                except Exception:
                    consumption_raw = Decimal('0')
                    record['flags'].append({'type': 'missing_field', 'field': 'consumption', 'detail': f'Could not parse consumption: {raw_val}'})
            else:
                consumption_raw = Decimal('0')
                record['flags'].append({'type': 'missing_field', 'field': 'consumption', 'detail': 'Consumption value is empty'})

        multiplier = ELEC_UNIT_TO_KWH.get(unit_raw.upper(), None)
        if not multiplier:
            record['flags'].append({'type': 'unknown_unit', 'field': 'unit', 'detail': f'Unknown unit: {unit_raw}'})
            multiplier = Decimal('1')

        qty_kwh = consumption_raw * multiplier

        if qty_kwh < 0:
            record['flags'].append({'type': 'negative_value', 'field': 'consumption', 'detail': f'Value: {qty_kwh}'})

        meter_id = str(row.get('meter_id', '')).strip()
        site_name = str(row.get('site_name', '')).strip()

        if not meter_id:
            record['flags'].append({'type': 'missing_field', 'field': 'meter_id', 'detail': 'Missing meter ID'})

        record.update({
            'scope': 'scope2',
            'category': 'electricity',
            'activity_date': start_date,
            'period_start': start_date,
            'period_end': end_date,
            'quantity': qty_kwh,
            'unit_normalized': 'kWh',
            'original_quantity': str(consumption_raw),
            'original_unit': unit_raw,
            'site_code': meter_id,
            'site_name': site_name,
            'description': f"Electricity — {row.get('tariff', 'Standard')} tariff",
            'supplier_vendor': str(row.get('account_number', '')).strip(),
        })

        results.append(record)

    return results


def parse_travel_csv(df):
    """
    Parses Navan/Concur trip report CSV export.
    Flights use IATA codes; distance calculated via haversine.
    Hotels use nights. Ground transport uses distance_km where available.
    """
    results = []

    COLUMN_MAP = {
        'trip_id': 'trip_id',
        'Trip ID': 'trip_id',
        'traveler_name': 'traveler_name',
        'Traveler Name': 'traveler_name',
        'travel_date': 'travel_date',
        'Travel Date': 'travel_date',
        'departure_date': 'travel_date',
        'Departure Date': 'travel_date',
        'category': 'travel_category',
        'Category': 'travel_category',
        'Type': 'travel_category',
        'origin': 'origin',
        'Origin': 'origin',
        'From': 'origin',
        'destination': 'destination',
        'Destination': 'destination',
        'To': 'destination',
        'distance_km': 'distance_km',
        'Distance (km)': 'distance_km',
        'nights': 'nights',
        'Nights': 'nights',
        'hotel_city': 'hotel_city',
        'Hotel City': 'hotel_city',
        'class': 'travel_class',
        'Class': 'travel_class',
        'cost_usd': 'cost_usd',
        'Cost (USD)': 'cost_usd',
        'department': 'department',
        'Department': 'department',
    }

    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    for idx, row in df.iterrows():
        record = {'row_index': idx, 'flags': [], 'raw': row.to_dict()}

        travel_date = None
        date_str = str(row.get('travel_date', '')).strip()
        if date_str and date_str != 'nan':
            try:
                travel_date = pd.to_datetime(date_str).date()
            except Exception:
                record['flags'].append({'type': 'date_parse_error', 'field': 'travel_date', 'detail': f'Could not parse: {date_str}'})

        travel_cat = str(row.get('travel_category', '')).strip().lower()

        if 'flight' in travel_cat or 'air' in travel_cat:
            category = 'flight'
            scope = 'scope3'

            origin = str(row.get('origin', '')).strip().upper()
            dest = str(row.get('destination', '')).strip().upper()

            distance_km = None
            raw_dist = str(row.get('distance_km', '')).strip()
            if raw_dist and raw_dist != 'nan':
                try:
                    distance_km = Decimal(raw_dist)
                except Exception:
                    pass

            if distance_km is None:
                o_coords = AIRPORT_COORDS.get(origin)
                d_coords = AIRPORT_COORDS.get(dest)
                if o_coords and d_coords:
                    distance_km = Decimal(str(round(haversine_km(*o_coords, *d_coords), 1)))
                else:
                    distance_km = Decimal('0')
                    if not o_coords:
                        record['flags'].append({'type': 'unknown_site', 'field': 'origin', 'detail': f'Unknown airport code: {origin}'})
                    if not d_coords:
                        record['flags'].append({'type': 'unknown_site', 'field': 'destination', 'detail': f'Unknown airport code: {dest}'})

            qty = distance_km
            unit = 'km'
            description = f"Flight {origin}→{dest} ({row.get('travel_class', 'Economy')})"
            site_code = f"{origin}-{dest}"

        elif 'hotel' in travel_cat or 'accommodation' in travel_cat:
            category = 'hotel'
            scope = 'scope3'

            nights_raw = str(row.get('nights', '1')).strip()
            try:
                qty = Decimal(nights_raw)
            except Exception:
                qty = Decimal('1')
                record['flags'].append({'type': 'missing_field', 'field': 'nights', 'detail': f'Could not parse nights: {nights_raw}'})

            unit = 'nights'
            hotel_city = str(row.get('hotel_city', row.get('destination', ''))).strip()
            description = f"Hotel — {hotel_city}"
            site_code = hotel_city

        elif 'ground' in travel_cat or 'taxi' in travel_cat or 'car' in travel_cat or 'rail' in travel_cat or 'train' in travel_cat:
            category = 'ground_transport'
            scope = 'scope3'

            dist_raw = str(row.get('distance_km', '')).strip()
            if dist_raw and dist_raw != 'nan':
                try:
                    qty = Decimal(dist_raw)
                except Exception:
                    qty = Decimal('0')
                    record['flags'].append({'type': 'missing_field', 'field': 'distance_km', 'detail': 'Could not parse distance'})
            else:
                qty = Decimal('0')
                record['flags'].append({'type': 'missing_field', 'field': 'distance_km', 'detail': 'Distance not provided for ground transport'})

            unit = 'km'
            description = f"Ground transport — {travel_cat}"
            site_code = str(row.get('origin', '')).strip()

        else:
            category = 'flight'
            scope = 'scope3'
            qty = Decimal('0')
            unit = 'km'
            description = f"Unknown travel category: {travel_cat}"
            site_code = ''
            record['flags'].append({'type': 'missing_field', 'field': 'category', 'detail': f'Unrecognized travel category: {travel_cat}'})

        if qty < 0:
            record['flags'].append({'type': 'negative_value', 'field': 'quantity', 'detail': f'Value: {qty}'})

        record.update({
            'scope': scope,
            'category': category,
            'activity_date': travel_date,
            'quantity': qty,
            'unit_normalized': unit,
            'original_quantity': str(row.get('distance_km', qty)),
            'original_unit': unit,
            'site_code': site_code,
            'site_name': str(row.get('hotel_city', row.get('destination', ''))).strip(),
            'description': description,
            'supplier_vendor': str(row.get('traveler_name', '')).strip(),
        })

        results.append(record)

    return results
