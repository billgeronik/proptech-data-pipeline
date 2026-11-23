"""Five transparent, symmetric hypothetical development scenarios.

Run from the repository root: python -m analysis.scenarios
No live property data, planning verification or investment recommendation.
"""

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    ("base", Decimal("0"), Decimal("0")),
    ("construction_plus_10pct", Decimal("0.10"), Decimal("0")),
    ("sales_minus_10pct", Decimal("0"), Decimal("-0.10")),
    ("combined_stress", Decimal("0.10"), Decimal("-0.10")),
    ("favorable", Decimal("-0.10"), Decimal("0.10")),
)
FIELDS = (
    "plot_id", "plot_area_m2", "assumed_far", "assumed_saleable_fraction",
    "construction_eur_per_floor_m2", "sale_price_eur_per_saleable_m2",
    "land_price_eur", "other_costs_eur", "assumption_source", "assumption_notes",
)
OUTPUT_FIELDS = (
    "scenario", "construction_change_pct", "sale_price_change_pct",
    "plot_id", "floor_area_proxy_m2", "saleable_area_proxy_m2",
    "construction_cost_eur", "modeled_sales_eur", "land_price_eur",
    "other_costs_eur", "simplified_residual_eur", "comparison", "difference_eur",
)


def read_inputs(path):
    """Read exactly two unique synthetic plot IDs and validate all assumptions."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV header is missing or has duplicate columns")
        if set(reader.fieldnames) != set(FIELDS):
            raise ValueError(f"CSV columns must be exactly: {', '.join(FIELDS)}")
        plots = []
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Line {line}: inconsistent CSV column count")
            plot_id = row["plot_id"].strip()
            if not plot_id:
                raise ValueError(f"Line {line}: empty plot_id")
            if not row["assumption_source"].strip():
                raise ValueError(f"Line {line}: assumption_source is required")
            parsed = {"plot_id": plot_id}
            for field in FIELDS[1:8]:
                raw = row[field].strip()
                try:
                    number = Decimal(raw)
                except (InvalidOperation, ValueError):
                    raise ValueError(f"Line {line}: {field} must be a decimal number") from None
                if not number.is_finite():
                    raise ValueError(f"Line {line}: {field} must be finite")
                if field in ("other_costs_eur",) and number < 0:
                    raise ValueError(f"Line {line}: {field} cannot be negative")
                if field not in ("other_costs_eur",) and number <= 0:
                    raise ValueError(f"Line {line}: {field} must be positive")
                if field == "assumed_saleable_fraction" and number > 1:
                    raise ValueError(f"Line {line}: assumed_saleable_fraction cannot exceed 1")
                parsed[field] = number
            plots.append(parsed)
    if len(plots) != 2 or plots[0]["plot_id"] == plots[1]["plot_id"]:
        raise ValueError("Provide exactly two rows with distinct plot_id values")
    return plots


def evaluate(plot, construction_change, sales_change):
    """All arithmetic is Decimal; both plots receive identical percentage changes."""
    floor = plot["plot_area_m2"] * plot["assumed_far"]
    saleable = floor * plot["assumed_saleable_fraction"]
    construction = floor * plot["construction_eur_per_floor_m2"] * (1 + construction_change)
    sales = saleable * plot["sale_price_eur_per_saleable_m2"] * (1 + sales_change)
    residual = sales - construction - plot["land_price_eur"] - plot["other_costs_eur"]
    return floor, saleable, construction, sales, residual


def fmt(value):
    return f"{value:.2f}"


def make_report(plots):
    records = []
    for name, construction_change, sales_change in SCENARIOS:
        results = [evaluate(p, construction_change, sales_change) for p in plots]
        a, b = results[0][-1], results[1][-1]
        winner = plots[0]["plot_id"] if a > b else plots[1]["plot_id"] if b > a else "TIE"
        difference = abs(a - b)
        for plot, values in zip(plots, results):
            floor, saleable, construction, sales, residual = values
            records.append({
                "scenario": name,
                "construction_change_pct": fmt(construction_change * 100),
                "sale_price_change_pct": fmt(sales_change * 100),
                "plot_id": plot["plot_id"],
                "floor_area_proxy_m2": fmt(floor),
                "saleable_area_proxy_m2": fmt(saleable),
                "construction_cost_eur": fmt(construction),
                "modeled_sales_eur": fmt(sales),
                "land_price_eur": fmt(plot["land_price_eur"]),
                "other_costs_eur": fmt(plot["other_costs_eur"]),
                "simplified_residual_eur": fmt(residual),
                "comparison": winner,
                "difference_eur": fmt(difference),
            })
    return records


def write_report(records, output):
    """Refuse to overwrite inputs; write CSV only after successful validation."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "fixtures/scenario_inputs.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "output/scenario_report.csv")
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files")
    try:
        plots = read_inputs(args.input)
        records = make_report(plots)
        write_report(records, args.output)
    except (OSError, ValueError) as exc:
        print(f"Scenario input error: {exc}", file=sys.stderr)
        return 2
    print(f"Generated {len(SCENARIOS)} scenarios for {len(plots)} plots: {args.output}")
    for i in range(0, len(records), 2):
        first, second = records[i:i + 2]
        print(f"{first['scenario']}: {first['plot_id']} EUR {first['simplified_residual_eur']}; "
              f"{second['plot_id']} EUR {second['simplified_residual_eur']}; "
              f"higher residual: {first['comparison']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
