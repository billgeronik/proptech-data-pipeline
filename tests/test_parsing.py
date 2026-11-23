"""Parsing checks protect meaning before any engineering arithmetic runs."""
import tempfile
import unittest
from pathlib import Path

from collectors.manual_seed import listings_from_manual_seed, parse_bool, parse_number, pick

HEADER = 'listing_id,municipality,price_eur,plot_area_m2'


class NumberTests(unittest.TestCase):
    def test_supported_numbers(self):
        cases = {
            '1234': 1234, '1234.56': 1234.56, '1234,56': 1234.56,
            '1.234,56': 1234.56, '1,234.56': 1234.56,
            '1.234.567': 1234567, '1,234,567': 1234567,
            '1 234,56': 1234.56, '1\u00a0234.56': 1234.56,
            '1\u202f234': 1234, '+1.25': 1.25, '-1,25': -1.25,
            '.25': .25, ',25': .25, ' 0 ': 0, '1.2340': 1.234,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_number(raw), (expected, None))

    def test_missing_is_not_zero(self):
        self.assertEqual(parse_number(None), (None, None))
        self.assertEqual(parse_number('  '), (None, None))
        self.assertEqual(parse_number('0'), (0, None))

    def test_coverage_percentage(self):
        self.assertEqual(parse_number('60%', percent=True), (.6, None))
        self.assertEqual(parse_number('60,5 %', percent=True), (.605, None))
        self.assertEqual(parse_number('0%', percent=True), (0, None))
        self.assertIsNotNone(parse_number('60%')[1])
        self.assertIsNotNone(parse_number('60%%', percent=True)[1])

    def test_ambiguous_single_separator(self):
        for raw in ('1.234', '1,234', '123.456', '-12,345', '0.600'):
            with self.subTest(raw=raw):
                value, error = parse_number(raw)
                self.assertIsNone(value)
                self.assertIn('ambiguous', error)

    def test_rejects_malformed_grouping_and_units(self):
        for raw in ('1 2', '12 34', '1  234', '01 234', '1\t234', '1,23.45',
                    '1.234.56', '1,234,56', '€100', '100m2', '1e3', '１２３', '١٢٣', '--2'):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_number(raw)[0])
                self.assertIsNotNone(parse_number(raw)[1])

    def test_rejects_non_finite_values(self):
        for raw in ('NaN', 'nan', 'sNaN', 'Inf', '+Infinity', '-inf'):
            with self.subTest(raw=raw):
                value, error = parse_number(raw)
                self.assertIsNone(value)
                self.assertIn('non-finite', error)

    def test_rejects_overflow_and_underflow(self):
        self.assertIn('too large', parse_number('9' * 400)[1])
        self.assertIn('too small', parse_number('0.' + '0' * 400 + '1')[1])


class BooleanTests(unittest.TestCase):
    def test_boolean_tokens(self):
        for raw in ('true', 'YES', 'y', '1', 'ΝΑΙ'):
            self.assertEqual(parse_bool(raw), (True, None))
        for raw in ('false', 'NO', 'n', '0', 'ΌΧΙ', 'οχι'):
            self.assertEqual(parse_bool(raw), (False, None))

    def test_unknown_and_invalid_stay_unknown(self):
        for raw in ('', 'unknown', '?', 'n/a', None):
            self.assertEqual(parse_bool(raw), (None, None))
        for raw in ('2', '-1', '0.0', 'maybe'):
            value, error = parse_bool(raw)
            self.assertIsNone(value)
            self.assertIn('unrecognized', error)


class CollectorTests(unittest.TestCase):
    def read(self, text, delimiter=',', encoding='utf-8'):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'input.csv'
            file.write_text(text, encoding=encoding)
            return listings_from_manual_seed(file, delimiter=delimiter)

    def test_legacy_aliases_and_blank_source(self):
        _, item = self.read('source,listing_id,municipality,price,plot_area,corner\n ,X, Athens ,100,200,no\n')[0]
        self.assertEqual(item.source, 'MANUAL')
        self.assertEqual(item.municipality, 'Athens')
        self.assertEqual(item.price_eur, 100)
        self.assertIs(item.corner_plot, False)

    def test_conflicting_aliases_are_not_chosen(self):
        _, item = self.read(HEADER + ',price\nX,Athens,100,200,101\n')[0]
        self.assertIsNone(item.price_eur)
        self.assertIn('conflicting alias', item.raw_errors[0])
        self.assertEqual(pick({'price': '100', 'price_eur': '100'}, ('price', 'price_eur')), ('100', None))

    def test_missing_id_is_preserved(self):
        _, item = self.read(HEADER + '\n,Athens,100,200\n')[0]
        self.assertEqual(item.listing_id, '')
        self.assertEqual(item.raw_values['listing_id'], '')

    def test_semicolon_and_utf8_bom(self):
        _, item = self.read(HEADER.replace(',', ';') + '\nX;Αθήνα;1.234,56;500,50\n', delimiter=';', encoding='utf-8-sig')[0]
        self.assertEqual(item.price_eur, 1234.56)
        self.assertEqual(item.municipality, 'Αθήνα')

    def test_unknown_headers_and_typos_are_errors(self):
        for header in (HEADER + ',random', HEADER.replace('price_eur', 'prcie_eur')):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, 'unsupported headers'):
                self.read(header + '\nX,Athens,100,200\n')

    def test_duplicate_and_empty_headers_are_errors(self):
        for header in (HEADER + ',price_eur', HEADER + ','):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, 'header'):
                self.read(header + '\nX,Athens,100,200\n')

    def test_required_header_missing(self):
        with self.assertRaisesRegex(ValueError, 'required header missing'):
            self.read('listing_id,municipality,plot_area_m2\nX,Athens,200\n')

    def test_wrong_row_width_is_error(self):
        for row in ('X,Athens,100', 'X,Athens,100,200,EXTRA'):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, 'CSV line 2: expected 4 cells'):
                self.read(HEADER + '\n' + row + '\n')

    def test_unclosed_quotes_are_error(self):
        with self.assertRaisesRegex(ValueError, 'malformed CSV'):
            self.read(HEADER + '\nX,"Athens,100,200\n')

    def test_empty_and_header_only_are_errors(self):
        for text in ('', HEADER + '\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read(text)

    def test_multiline_cells_use_physical_start_lines(self):
        rows = self.read(HEADER + ',description\nX,Athens,100,200,"first\nsecond"\n\nY,Athens,100,200,ok\n')
        self.assertEqual([line for line, _ in rows], [2, 5])
        self.assertEqual(rows[0][1].description, 'first\nsecond')
        self.assertEqual(rows[1][1].input_line, 5)

    def test_invalid_dates_are_blank_with_reason(self):
        _, item = self.read(HEADER + ',observed_at,far_date\nX,Athens,100,200,2026-02-30,20261123\n')[0]
        self.assertEqual(item.observed_at, '')
        self.assertEqual(item.far_date, '')
        self.assertEqual(len(item.raw_errors), 2)
        self.assertIn('YYYY-MM-DD', item.raw_errors[0])

    def test_valid_dates_are_preserved(self):
        _, item = self.read(HEADER + ',observed_at,far_date\nX,Athens,100,200,2026-11-23,2024-02-29\n')[0]
        self.assertEqual(item.observed_at, '2026-11-23')
        self.assertEqual(item.far_date, '2024-02-29')

    def test_empty_record_is_preserved(self):
        rows = self.read(HEADER + '\n,,,\n')
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0][1].price_eur)

    def test_delimiter_must_be_explicitly_supported(self):
        with self.assertRaisesRegex(ValueError, 'delimiter'):
            self.read(HEADER + '\nX,Athens,100,200\n', delimiter='|')


if __name__ == '__main__':
    unittest.main()
