"""Local CSV -> normalization -> validation -> deterministic CSV report."""

import argparse
from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path
import sys
import tempfile

from collectors.manual_seed import listings_from_manual_seed
from analysis.quality import evaluate_data_quality

ROOT = Path(__file__).resolve().parent
METRICS = ("price_per_land_m2", "indicative_floor_area_m2", "price_per_indicative_floor_m2")
BOOLEANS = ("corner_plot", "inside_plan", "demolition_candidate")
COLUMNS = [
    "input_file", "input_line", "source", "listing_id", "title", "municipality",
    "neighbourhood", "address", "url", "observed_at", "price_eur", "plot_area_m2",
    "existing_building_m2", "far", "far_source", "far_date", "coverage_ratio", "frontage_m",
    *BOOLEANS, *METRICS, "assumptions", "description", "validation_status", "warning_count",
    "warning_reasons", "raw_input",
]


def duplicate_warnings(listings):
    """Mark every matching row, including the first, without deleting anything."""
    by_id, by_url, by_record = defaultdict(list), defaultdict(list), defaultdict(list)
    for index, (_, item) in enumerate(listings):
        if item.listing_id:
            by_id[(item.source, item.listing_id)].append(index)
        if item.url:
            by_url[item.url].append(index)
        # Original strings avoid treating two different invalid numbers as equal None.
        record = tuple(sorted((key, value.strip()) for key, value in item.raw_values.items()
                              if key != "listing_id"))
        if any(value for key, value in record if key != "source"):
            by_record[record].append(index)

    warnings = defaultdict(list)
    for groups, label in (
        (by_id, "listing_id: duplicate source + listing_id"),
        (by_url, "url: duplicate nonempty URL"),
        (by_record, "record: duplicate content excluding listing_id"),
    ):
        for indices in groups.values():
            if len(indices) > 1:
                locations = ", ".join(
                    f"{listings[i][1].input_file}:{listings[i][0]}" for i in indices
                )
                for index in indices:
                    warnings[index].append(f"{label}; matches {locations}; all occurrences retained")
    return warnings


def report_rows(listings):
    """Validate operands first, calculate only available metrics, then explain warnings."""
    duplicates = duplicate_warnings(listings)
    rows = []
    for index, (line, item) in enumerate(listings):
        issues = evaluate_data_quality(item)
        item.calculate()
        issues.extend(item.calculation_warnings)
        issues.extend(duplicates[index])
        values = {name: getattr(item, name, "") for name in COLUMNS}
        values.update(
            input_line=line,
            validation_status="WARNING" if issues else "OK",
            warning_count=len(issues),
            warning_reasons=" | ".join(issues),
            raw_input=json.dumps(item.raw_values, ensure_ascii=False, sort_keys=True),
        )
        for name, value in list(values.items()):
            if name in BOOLEANS:
                values[name] = "unknown" if value is None else ("true" if value else "false")
            elif value is None:
                values[name] = ""
            elif name in METRICS:
                values[name] = f"{value:.2f}"
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Internal error: non-finite report value for {name}")
        rows.append(values)
    return rows


def _write_report(input_paths, output_path, delimiter):
    """Read every input before creating output; replace an old report only on success."""
    output = Path(output_path)
    for source in input_paths:
        if source.resolve() == output.resolve() or (
            source.exists() and output.exists() and os.path.samefile(source, output)
        ):
            raise ValueError("Input and output refer to the same file; choose a separate output")

    listings = []
    for source in input_paths:
        try:
            listings.extend(listings_from_manual_seed(source, delimiter=delimiter))
        except (ValueError, csv.Error) as error:
            raise ValueError(f"{source}: {error}") from error
    rows = report_rows(listings)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=".report-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            # Output is always comma-delimited, whatever delimiter the input used.
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    warned = sum(row["validation_status"] == "WARNING" for row in rows)
    print(f"Processed {len(rows)} rows: {len(rows) - warned} OK, {warned} WARNING. Wrote {output}")
    return output, warned


def run(input_path, output_path, delimiter=","):
    """Public entry point retained from the earlier milestone; one file or a list."""
    inputs = [input_path] if isinstance(input_path, (str, Path)) else list(input_path)
    if not inputs:
        raise ValueError("At least one input file is required")
    return _write_report([Path(p) for p in inputs], output_path, delimiter)[0]


def load_config(path):
    """JSON keeps configuration real and the project dependency-free."""
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    unknown = set(config) - {"input_files", "output_file", "delimiter"}
    if unknown:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    inputs = config.get("input_files")
    output = config.get("output_file")
    delimiter = config.get("delimiter", ",")
    if not isinstance(inputs, list) or not inputs or any(
        not isinstance(p, str) or not p.strip() for p in inputs
    ):
        raise ValueError("config input_files must be a nonempty list of paths")
    if not isinstance(output, str) or not output.strip():
        raise ValueError("config output_file must be a nonempty path")
    if delimiter not in (",", ";"):
        raise ValueError("config delimiter must be ',' or ';'")
    # Absolute paths remain absolute; relative config paths follow the config file.
    return [path.parent / p for p in inputs], path.parent / output, delimiter


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local plot CSV screening; synthetic example included")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--input", nargs="+", type=Path, help="one or more CSVs; replaces configured inputs")
    parser.add_argument("--output", type=Path, help="report path; relative to current directory")
    parser.add_argument("--delimiter", choices=[",", ";"], help="input delimiter (output always uses comma)")
    parser.add_argument("--fail-on-warnings", action="store_true", help="write report, then exit 1 if any row warns")
    args = parser.parse_args(argv)
    try:
        inputs, output, delimiter = load_config(args.config)
        inputs = args.input if args.input is not None else inputs
        output = args.output if args.output is not None else output
        delimiter = args.delimiter if args.delimiter is not None else delimiter
        _, warned = _write_report(inputs, output, delimiter)
        return 1 if warned and args.fail_on_warnings else 0
    except (OSError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
