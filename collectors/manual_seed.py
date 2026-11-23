"""Read CSV rows without guessing units, separators, booleans or missing IDs."""
import csv
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from models.property import PropertyListing

NUMERIC = {
    'price_eur': ('price_eur', 'price'),
    'plot_area_m2': ('plot_area_m2', 'plot_area'),
    'existing_building_m2': ('existing_building_m2', 'existing_building'),
    'far': ('far',), 'coverage_ratio': ('coverage_ratio', 'coverage'),
    'frontage_m': ('frontage_m', 'frontage'),
}
BOOLEAN = {
    'corner_plot': ('corner_plot', 'corner'), 'inside_plan': ('inside_plan',),
    'demolition_candidate': ('demolition_candidate', 'demolition'),
}
TEXT_FIELDS = (
    'listing_id', 'url', 'title', 'municipality', 'neighbourhood', 'address',
    'description', 'far_source', 'assumptions',
)
DATE_FIELDS = ('observed_at', 'far_date')
ALLOWED_HEADERS = set(TEXT_FIELDS + DATE_FIELDS + ('source',)) | {
    name for aliases in (*NUMERIC.values(), *BOOLEAN.values()) for name in aliases
}


def parse_number(raw, percent=False):
    """Return a finite float or (None, explanation); blank means unknown."""
    s = '' if raw is None else str(raw).strip()
    if not s:
        return None, None
    s = s.replace('\u00a0', ' ').replace('\u202f', ' ')
    has_percent = s.endswith('%')
    if has_percent:
        if not percent:
            return None, 'percentage is supported only for coverage_ratio'
        s = s[:-1].strip()
    if re.fullmatch(r'[+-]?(?:inf(?:inity)?|s?nan[0-9]*)', s, re.IGNORECASE):
        return None, 'non-finite numbers are not allowed'
    # A space is accepted only as a correctly grouped thousands separator.
    if ' ' in s:
        if not re.fullmatch(r'[+-]?[1-9][0-9]{0,2}(?: [0-9]{3})+(?:[.,][0-9]+)?', s):
            return None, 'malformed space grouping; use e.g. 1 234,56'
        s = s.replace(' ', '').replace(',', '.')
    elif ',' in s and '.' in s:
        if re.fullmatch(r'[+-]?[1-9][0-9]{0,2}(?:\.[0-9]{3})+,[0-9]+', s):
            s = s.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'[+-]?[1-9][0-9]{0,2}(?:,[0-9]{3})+\.[0-9]+', s):
            s = s.replace(',', '')
        else:
            return None, 'malformed or mixed decimal/thousands separators'
    elif re.fullmatch(r'[+-]?[0-9]{1,3}[.,][0-9]{3}', s):
        return None, 'ambiguous separator: write 1234 or 1.234,00 for thousands; 1.2340 for a decimal'
    elif re.fullmatch(r'[+-]?[1-9][0-9]{0,2}(?:\.[0-9]{3}){2,}', s):
        s = s.replace('.', '')
    elif re.fullmatch(r'[+-]?[1-9][0-9]{0,2}(?:,[0-9]{3}){2,}', s):
        s = s.replace(',', '')
    elif re.fullmatch(r'[+-]?(?:[0-9]+(?:[.,][0-9]+)?|[.,][0-9]+)', s):
        s = s.replace(',', '.')
    else:
        return None, 'invalid number; no currency symbols, units, exponents or malformed separators'
    try:
        number = Decimal(s)
        if has_percent:
            number /= 100
        value = float(number)
        if not math.isfinite(value):
            return None, 'number is too large; conversion would be non-finite'
        if number != 0 and value == 0:
            return None, 'number is too small; conversion would incorrectly become zero'
        return value, None
    except (InvalidOperation, OverflowError, ArithmeticError, ValueError):
        return None, 'invalid or unsupported numeric value'


def parse_bool(raw):
    """Keep unknown distinct from False; never use bool(text)."""
    s = '' if raw is None else str(raw).strip().casefold()
    if s in ('', 'unknown', '?', 'n/a'):
        return None, None
    if s in ('true', 'yes', 'y', '1', 'ναι'):
        return True, None
    if s in ('false', 'no', 'n', '0', 'όχι', 'οχι'):
        return False, None
    return None, 'unrecognized boolean; use true/false, yes/no, 1/0 or ναι/όχι'


def pick(row, names):
    """Preserve old column aliases; conflicting supplied text needs review."""
    populated = [(name, row[name].strip()) for name in names
                 if row.get(name) is not None and row[name].strip()]
    if len({value for _, value in populated}) > 1:
        return None, 'conflicting alias columns: ' + ', '.join(name for name, _ in populated)
    return (populated[0][1] if populated else None), None


def _check_headers(headers):
    if not headers or any(not name for name in headers):
        raise ValueError('CSV line 1: missing or empty header')
    if len(headers) != len(set(headers)):
        raise ValueError('CSV line 1: duplicate column headers')
    unknown = sorted(set(headers) - ALLOWED_HEADERS)
    if unknown:
        raise ValueError('CSV line 1: unsupported headers: ' + ', '.join(unknown))
    for aliases in [('listing_id',), ('municipality',), NUMERIC['price_eur'], NUMERIC['plot_area_m2']]:
        if not set(aliases).intersection(headers):
            raise ValueError('CSV line 1: required header missing: ' + ' or '.join(aliases))


def _listing(row, filepath, line):
    errors, fields = [], {}
    for field, aliases in (*NUMERIC.items(), *BOOLEAN.items()):
        raw, error = pick(row, aliases)
        if field in NUMERIC:
            value, parse_error = parse_number(raw, percent=field == 'coverage_ratio')
        else:
            value, parse_error = parse_bool(raw)
        if error or parse_error:
            errors.append(f'{field}: {error or parse_error} (input {raw!r})')
        fields[field] = value
    for field in TEXT_FIELDS:
        fields[field] = row.get(field, '').strip()
    for field in DATE_FIELDS:
        supplied = row.get(field, '').strip()
        fields[field] = supplied
        if supplied:
            try:
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', supplied):
                    raise ValueError('wrong date format')
                date.fromisoformat(supplied)
            except ValueError:
                fields[field] = ''
                errors.append(f'{field}: invalid date {supplied!r}; use YYYY-MM-DD')
    path = Path(filepath).resolve()
    root = Path(__file__).resolve().parents[1]
    try:
        provenance = path.relative_to(root).as_posix()
    except ValueError:
        provenance = str(path)
    return PropertyListing(
        source=(row.get('source', '').strip() or 'MANUAL').upper(),
        input_file=provenance, input_line=line,
        raw_values=dict(row), raw_errors=errors, **fields,
    )


def listings_from_manual_seed(filepath='fixtures/manual_seed.csv', delimiter=','):
    """Read every record or fail clearly on structural CSV errors, without guessing."""
    if delimiter not in (',', ';'):
        raise ValueError('CSV delimiter must be comma or semicolon')
    properties = []
    with open(filepath, newline='', encoding='utf-8-sig') as handle:
        reader = csv.reader(handle, delimiter=delimiter, strict=True)
        try:
            headers = next(reader, None)
            if headers is None:
                raise ValueError('CSV line 1: no header')
            headers = [name.strip() for name in headers]
            _check_headers(headers)
            while True:
                start_line = reader.line_num + 1
                cells = next(reader, None)
                if cells is None:
                    break
                if not cells:  # Blank physical lines carry no record.
                    continue
                if len(cells) != len(headers):
                    raise ValueError(
                        f'CSV line {start_line}: expected {len(headers)} cells, got {len(cells)}; '
                        'check delimiter and quote values containing commas'
                    )
                row = dict(zip(headers, cells))
                properties.append((start_line, _listing(row, filepath, start_line)))
        except csv.Error as exc:
            raise ValueError(f'CSV line {reader.line_num}: malformed CSV: {exc}') from exc
    if not properties:
        raise ValueError('CSV has a header but no records')
    return properties
