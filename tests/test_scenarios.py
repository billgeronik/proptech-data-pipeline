"""Independent arithmetic and workflow checks for the five scenario comparison."""
import csv
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from analysis.scenarios import SCENARIOS, evaluate, main, make_report, read_inputs

ROOT = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.plots = read_inputs(ROOT / "fixtures/scenario_inputs.csv")

    def test_five_exact_scenarios(self):
        self.assertEqual([s[0] for s in SCENARIOS], [
            "base", "construction_plus_10pct", "sales_minus_10pct",
            "combined_stress", "favorable",
        ])

    def test_checked_residuals_and_same_shocks(self):
        expected = [
            ("370000.00", "392000.00"),
            ("262000.00", "287000.00"),
            ("178000.00", "204800.00"),
            ("70000.00", "99800.00"),
            ("670000.00", "684200.00"),
        ]
        rows = make_report(self.plots)
        self.assertEqual(len(rows), 10)
        for i, (a, b) in enumerate(expected):
            self.assertEqual(rows[2*i]["simplified_residual_eur"], a)
            self.assertEqual(rows[2*i+1]["simplified_residual_eur"], b)
            self.assertEqual(rows[2*i]["comparison"], "B")
            self.assertEqual(rows[2*i+1]["comparison"], "B")
            self.assertEqual(rows[2*i]["construction_change_pct"], rows[2*i+1]["construction_change_pct"])
            self.assertEqual(rows[2*i]["sale_price_change_pct"], rows[2*i+1]["sale_price_change_pct"])

    def test_base_intermediate_values(self):
        self.assertEqual(evaluate(self.plots[0], Decimal(0), Decimal(0)),
                         (Decimal(600), Decimal(480), Decimal(1080000), Decimal(1920000), Decimal(370000)))
        self.assertEqual(evaluate(self.plots[1], Decimal(0), Decimal(0)),
                         (Decimal(600), Decimal(480), Decimal(1050000), Decimal(1872000), Decimal(392000)))

    def test_tie_is_reported_not_forced(self):
        equal = [dict(self.plots[0]), dict(self.plots[0])]
        equal[1]["plot_id"] = "B"
        self.assertEqual(make_report(equal)[0]["comparison"], "TIE")

    def test_invalid_input_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.csv"
            original = (ROOT / "fixtures/scenario_inputs.csv").read_text()
            for invalid in ("NaN", "-500", "1.50", "not-a-number"):
                modified = original.replace(",0.80,", f",{invalid},", 1)
                path.write_text(modified)
                with self.assertRaises(ValueError):
                    read_inputs(path)

    def test_duplicate_ids_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.csv"
            original = (ROOT / "fixtures/scenario_inputs.csv").read_text()
            path.write_text(original.replace("\nB,600", "\nA,600"))
            with self.assertRaises(ValueError):
                read_inputs(path)

    def test_cli_output_matches_expected_bytes(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.csv"
            self.assertEqual(main(["--output", str(output)]), 0)
            self.assertEqual(output.read_bytes(), (ROOT / "fixtures/expected_scenario_report.csv").read_bytes())

    def test_bad_input_preserves_existing_report(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            output = Path(tmp) / "existing.csv"
            path.write_text("invalid,header\n")
            output.write_text("preserve me")
            self.assertEqual(main(["--input", str(path), "--output", str(output)]), 2)
            self.assertEqual(output.read_text(), "preserve me")

    def test_reject_input_output_collision(self):
        with self.assertRaises(SystemExit) as context:
            main(["--input", str(ROOT / "fixtures/scenario_inputs.csv"),
                  "--output", str(ROOT / "fixtures/scenario_inputs.csv")])
        self.assertEqual(context.exception.code, 2)

    def test_header_mismatch_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrong.csv"
            path.write_text("plot_id,price\nA,100\nB,200\n")
            with self.assertRaises(ValueError):
                read_inputs(path)


if __name__ == "__main__":
    unittest.main()
