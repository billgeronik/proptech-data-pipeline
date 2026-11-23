"""End-to-end behavior, checked examples and failure cases for the CSV milestone."""
import contextlib
import csv
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from main import run
from models.property import PropertyListing

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "source", "listing_id", "title", "municipality", "neighbourhood", "address", "url",
    "price_eur", "plot_area_m2", "existing_building_m2", "far", "coverage_ratio", "frontage_m",
    "corner_plot", "inside_plan", "demolition_candidate", "description", "observed_at",
    "far_source", "far_date", "assumptions",
]
VALID = dict.fromkeys(FIELDS, "")
VALID.update(
    source="SYNTHETIC", listing_id="TEST-01", title="Invented plot", municipality="Example City",
    price_eur="150000", plot_area_m2="250", existing_building_m2="0", far="1.2",
    coverage_ratio="60%", frontage_m="12.5", corner_plot="yes", inside_plan="no",
    demolition_candidate="no",
)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write_input(self, records, name="input.csv", delimiter=","):
        path = self.directory / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(records)
        return path

    def report(self, records):
        source = self.write_input(records)
        destination = self.directory / "report.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            result = run(source, destination)
        self.assertEqual(result, destination)
        with destination.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    def cli(self, *arguments, cwd=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "main.py"), *map(str, arguments)],
            cwd=cwd or self.directory, text=True, capture_output=True, check=False,
        )

    def test_valid_record_matches_hand_calculation(self):
        row = self.report([VALID])[0]
        self.assertEqual(row["validation_status"], "OK")
        self.assertEqual(row["warning_count"], "0")
        self.assertEqual(row["warning_reasons"], "")
        self.assertEqual(row["price_per_land_m2"], "600.00")
        self.assertEqual(row["indicative_floor_area_m2"], "300.00")
        self.assertEqual(row["price_per_indicative_floor_m2"], "500.00")
        self.assertEqual(row["corner_plot"], "true")
        self.assertEqual(row["inside_plan"], "false")

    def test_valid_optional_zero_is_not_missing(self):
        row = self.report([{**VALID, "coverage_ratio": "0", "existing_building_m2": "0"}])[0]
        self.assertEqual(float(row["coverage_ratio"]), 0)
        self.assertEqual(float(row["existing_building_m2"]), 0)
        self.assertEqual(row["validation_status"], "OK")

    def test_missing_id_stays_missing_even_with_url(self):
        row = self.report([{**VALID, "listing_id": "", "url": "https://example.invalid/plot/123"}])[0]
        self.assertEqual(row["listing_id"], "")
        self.assertIn("listing_id", row["warning_reasons"])
        self.assertIn("missing", row["warning_reasons"].lower())

    def test_missing_location_is_explained(self):
        row = self.report([{**VALID, "municipality": ""}])[0]
        self.assertIn("municipality", row["warning_reasons"])

    def test_missing_price_and_far_do_not_become_zero(self):
        row = self.report([{**VALID, "price_eur": "", "far": ""}])[0]
        fields = ("price_eur", "far", "price_per_land_m2", "indicative_floor_area_m2", "price_per_indicative_floor_m2")
        for field in fields:
            self.assertEqual(row[field], "", field)
        self.assertIn("price_eur", row["warning_reasons"])
        self.assertIn("far", row["warning_reasons"])

    def test_missing_far_keeps_valid_land_ratio(self):
        row = self.report([{**VALID, "far": ""}])[0]
        self.assertEqual(row["price_per_land_m2"], "600.00")
        self.assertEqual(row["indicative_floor_area_m2"], "")
        self.assertEqual(row["price_per_indicative_floor_m2"], "")

    def test_missing_optional_dimensions_do_not_claim_metrics_are_blocked(self):
        row = self.report([{**VALID, "existing_building_m2": "", "coverage_ratio": "", "frontage_m": ""}])[0]
        self.assertEqual(row["price_per_land_m2"], "600.00")
        self.assertEqual(row["indicative_floor_area_m2"], "300.00")
        self.assertEqual(row["price_per_indicative_floor_m2"], "500.00")
        self.assertIn("unknown, not zero", row["warning_reasons"])
        self.assertNotIn("metrics remain blank", row["warning_reasons"])

    def test_invalid_numeric_values_are_blank_and_explained(self):
        cases = [
            ("price_eur", "-1"), ("price_eur", "0"), ("price_eur", "NaN"),
            ("price_eur", "Infinity"), ("price_eur", "200.000"),
            ("plot_area_m2", "-2"), ("plot_area_m2", "0"), ("plot_area_m2", "abc"),
            ("far", "-1"), ("far", "0"), ("far", "nan"),
            ("coverage_ratio", "-0.1"), ("coverage_ratio", "1.2"),
            ("coverage_ratio", "60"), ("existing_building_m2", "-10"),
            ("frontage_m", "0"), ("frontage_m", "-2"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                row = self.report([{**VALID, field: value}])[0]
                self.assertEqual(row[field], "")
                self.assertEqual(row["validation_status"], "WARNING")
                self.assertIn(field, row["warning_reasons"])
                self.assertEqual(json.loads(row["raw_input"])[field], value)
                if field in ("price_eur", "plot_area_m2"):
                    self.assertEqual(row["price_per_land_m2"], "")
                if field in ("plot_area_m2", "far"):
                    self.assertEqual(row["indicative_floor_area_m2"], "")

    def test_unknown_booleans_are_distinct_from_false(self):
        row = self.report([{**VALID, "corner_plot": "maybe", "inside_plan": "", "demolition_candidate": "no"}])[0]
        self.assertEqual(row["corner_plot"], "unknown")
        self.assertEqual(row["inside_plan"], "unknown")
        self.assertEqual(row["demolition_candidate"], "false")
        self.assertIn("corner_plot", row["warning_reasons"])
        self.assertIn("inside_plan", row["warning_reasons"])

    def test_duplicate_id_flags_every_occurrence_and_retains_rows(self):
        rows = self.report([VALID, {**VALID, "title": "Different data", "price_eur": "180000"}])
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("duplicate", row["warning_reasons"].lower())
            self.assertEqual(row["validation_status"], "WARNING")

    def test_duplicates_are_found_across_input_files(self):
        first = self.write_input([VALID], "first.csv")
        second = self.write_input([{**VALID, "price_eur": "180000"}], "second.csv")
        destination = self.directory / "combined.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            run([first, second], destination)
        with destination.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("duplicate" in row["warning_reasons"].lower() for row in rows))
        self.assertNotEqual(rows[0]["input_file"], rows[1]["input_file"])

    def test_identical_record_with_different_ids_is_flagged(self):
        rows = self.report([VALID, {**VALID, "listing_id": "TEST-02"}])
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("duplicate" in row["warning_reasons"].lower() for row in rows))

    def test_reused_url_is_flagged_with_different_ids(self):
        first = {**VALID, "url": "https://example.invalid/test"}
        second = {**first, "listing_id": "TEST-02", "price_eur": "180000"}
        rows = self.report([first, second])
        self.assertTrue(all("duplicate" in row["warning_reasons"].lower() for row in rows))

    def test_same_id_from_different_sources_is_not_automatically_duplicate(self):
        rows = self.report([VALID, {**VALID, "source": "OTHER-SYNTHETIC", "price_eur": "180000"}])
        self.assertTrue(all(row["validation_status"] == "OK" for row in rows))

    def test_source_and_metadata_are_preserved(self):
        record = {
            **VALID, "source": " synthetic ", "observed_at": "2026-11-01",
            "far_source": "Invented classroom exercise", "far_date": "2026-10-31",
            "assumptions": "FAR is illustrative only", "description": "Synthetic description",
        }
        row = self.report([record])[0]
        self.assertEqual(row["source"], "SYNTHETIC")
        for field in ("observed_at", "far_source", "far_date", "assumptions", "description"):
            self.assertEqual(row[field], record[field])
        self.assertEqual(json.loads(row["raw_input"])["source"], " synthetic ")

    def test_malformed_row_preserves_existing_report(self):
        source = self.write_input([VALID])
        with source.open("a", encoding="utf-8") as handle:
            handle.write("wrong,number,of,cells\n")
        destination = self.directory / "report.csv"
        destination.write_text("previous report\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            run(source, destination)
        self.assertEqual(destination.read_text(), "previous report\n")

    def test_bad_header_does_not_create_report(self):
        source = self.directory / "input.csv"
        source.write_text("listing_id,misspelled_price\nA,123\n", encoding="utf-8")
        destination = self.directory / "report.csv"
        with self.assertRaises(ValueError):
            run(source, destination)
        self.assertFalse(destination.exists())

    def test_later_invalid_file_cannot_create_partial_report(self):
        first = self.write_input([VALID])
        destination = self.directory / "report.csv"
        with self.assertRaises((OSError, ValueError)):
            run([first, self.directory / "missing.csv"], destination)
        self.assertFalse(destination.exists())

    def test_input_and_hardlinked_input_cannot_be_overwritten(self):
        source = self.write_input([VALID])
        before = source.read_bytes()
        with self.assertRaises(ValueError):
            run(source, source)
        self.assertEqual(source.read_bytes(), before)
        alias = self.directory / "alias.csv"
        try:
            os.link(source, alias)
        except (OSError, NotImplementedError):
            self.skipTest("Hard-link check unavailable on this filesystem; direct-path check ran")
        with self.assertRaises(ValueError):
            run(source, alias)
        self.assertEqual(source.read_bytes(), before)

    def test_report_is_deterministic(self):
        source = self.write_input([VALID, {**VALID, "listing_id": "B", "price_eur": ""}])
        first, second = self.directory / "one.csv", self.directory / "two.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            run(source, first)
            run(source, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_supplied_example_matches_checked_expected_csv(self):
        destination = self.directory / "report.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            run(ROOT / "fixtures" / "manual_seed.csv", destination)
        self.assertEqual(destination.read_bytes(), (ROOT / "fixtures" / "expected_report.csv").read_bytes())

    def test_config_paths_are_relative_to_config_location(self):
        self.write_input([VALID], "input.csv", delimiter=";")
        config = self.directory / "config.json"
        config.write_text(json.dumps({"input_files": ["input.csv"], "output_file": "reports/output.csv", "delimiter": ";"}))
        elsewhere = self.directory / "elsewhere"
        elsewhere.mkdir()
        result = self.cli("--config", config, cwd=elsewhere)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (self.directory / "reports/output.csv").open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["validation_status"], "OK")

    def test_cli_inputs_and_output_override_config(self):
        source = self.write_input([VALID])
        config = self.directory / "config.json"
        config.write_text(json.dumps({"input_files": ["not-used.csv"], "output_file": "not-used-report.csv", "delimiter": ","}))
        result = self.cli("--config", config, "--input", source.name, "--output", "actual.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.directory / "actual.csv").exists())
        self.assertFalse((self.directory / "not-used-report.csv").exists())

    def test_default_config_is_found_from_another_directory(self):
        destination = self.directory / "default.csv"
        result = self.cli("--output", destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(destination.exists())
        self.assertIn("Processed", result.stdout)

    def test_cli_missing_input_returns_error_without_report(self):
        destination = self.directory / "output.csv"
        result = self.cli("--input", "missing.csv", "--output", destination)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(result.stderr.strip())
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(destination.exists())

    def test_invalid_config_fails_clearly(self):
        config = self.directory / "bad.json"
        config.write_text("not json", encoding="utf-8")
        result = self.cli("--config", config, "--output", self.directory / "out.csv")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.directory / "out.csv").exists())

    def test_fail_on_warnings_writes_report_and_returns_one(self):
        source = self.write_input([{**VALID, "far": ""}])
        destination = self.directory / "warnings.csv"
        strict = self.cli("--input", source, "--output", destination, "--fail-on-warnings")
        self.assertEqual(strict.returncode, 1, strict.stderr)
        self.assertTrue(destination.exists())
        relaxed = self.cli("--input", source, "--output", destination)
        self.assertEqual(relaxed.returncode, 0, relaxed.stderr)

    def test_fail_on_warnings_returns_zero_for_valid_rows(self):
        source = self.write_input([VALID])
        result = self.cli("--input", source, "--output", self.directory / "valid.csv", "--fail-on-warnings")
        self.assertEqual(result.returncode, 0, result.stderr)


class CalculationTests(unittest.TestCase):
    def test_recalculation_clears_old_metrics(self):
        item = PropertyListing(price_eur=150000.0, plot_area_m2=250.0, far=1.2)
        item.calculate()
        self.assertEqual(item.indicative_floor_area_m2, 300)
        item.plot_area_m2 = None
        item.calculate()
        self.assertIsNone(item.price_per_land_m2)
        self.assertIsNone(item.indicative_floor_area_m2)
        self.assertIsNone(item.price_per_indicative_floor_m2)

    def test_nonfinite_inputs_cannot_produce_metrics(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                item = PropertyListing(price_eur=value, plot_area_m2=value, far=value)
                item.calculate()
                self.assertIsNone(item.price_per_land_m2)
                self.assertIsNone(item.indicative_floor_area_m2)
                self.assertIsNone(item.price_per_indicative_floor_m2)

    def test_arithmetic_overflow_is_not_reported_as_infinity(self):
        item = PropertyListing(price_eur=1e308, plot_area_m2=1e308, far=1e308)
        item.calculate()
        self.assertEqual(item.price_per_land_m2, 1)
        self.assertIsNone(item.indicative_floor_area_m2)
        self.assertIsNone(item.price_per_indicative_floor_m2)
        tiny = PropertyListing(price_eur=1e308, plot_area_m2=1e-300, far=1.0)
        tiny.calculate()
        self.assertIsNone(tiny.price_per_land_m2)
        self.assertIsNone(tiny.price_per_indicative_floor_m2)


if __name__ == "__main__":
    unittest.main()
