# PropTech Data Pipeline — first working milestone

A small Python workflow for preliminary plot comparisons: **CSV input → normalization → validation → CSV report**. The examples are entirely synthetic. The project does not access Leadership ATE's private records or claim company testing or adoption.

## Implemented now

- Read one or more local CSV files; preserve every data row, its location and original values.
- Parse numeric formats with explicit units and three-state booleans; explain missing, malformed, ambiguous, out-of-range and duplicate values.
- Calculate asking price per plot m², indicative floor area and asking price per indicative floor m² when their inputs are valid.
- Write a reproducible report, with sample input, a checked-in expected output and automated tests.
- Read an active JSON configuration, with command-line overrides. Python 3.10+ and its standard library are sufficient.

**These calculations do not establish verified building rights, saleable floor area, zoning compliance, structural safety, a formal valuation or an investment recommendation.** An `OK` row passes this program's data checks; it is not an engineering or planning approval.

## 1. Install and run

### From the supplied milestone archive

Extract the archive, open Terminal in its `proptech-data-pipeline` directory, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

`requirements.txt` intentionally lists no third-party packages. On Windows use `py -3 -m venv .venv` and `.venv\Scripts\activate` in Command Prompt, then the same `python` commands.

### From a fresh GitHub clone

This milestone is supplied as an archive and a patch; do not assume GitHub's default branch already contains it. Until the changes are merged, apply the supplied patch to a clean clone:

```bash
git clone https://github.com/billgeronik/proptech-data-pipeline.git
cd proptech-data-pipeline
git apply --check /path/to/milestone-1.patch
git apply /path/to/milestone-1.patch
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

Replace `/path/to/milestone-1.patch` with the downloaded patch's actual path. The patch was prepared against upstream commit `4efd10f696d44eb5119a70b98d6f498ee2cf67c7`. If `git apply --check` fails, inspect the differences; do not force it over newer work. Once merged, skip both patch commands.

The default run reads `fixtures/manual_seed.csv` and writes `output/report.csv`. Its expected summary is `Processed 8 rows: 2 OK, 6 WARNING.` followed by the report path. The synthetic rows include valid, incomplete, malformed, ambiguous and duplicate examples. Open the report as UTF-8, comma-delimited CSV.

## 2. Configuration and command-line options

`config.json` is actually read by the program:

```json
{
  "input_files": ["fixtures/manual_seed.csv"],
  "output_file": "output/report.csv",
  "delimiter": ","
}
```

The CLI always reads the configuration, even when you supply overrides. Paths inside a configuration file are relative to that file. Explicit CLI paths are relative to your current working directory. The earlier informational `config.yaml` has been replaced; YAML is not used.

```bash
python main.py --input fixtures/manual_seed.csv --output output/check.csv
python main.py --input first.csv second.csv --output output/combined.csv
python main.py --input my-plots.csv --delimiter ';'
python main.py --config /path/to/config.json
python main.py --fail-on-warnings
python main.py --help
```

`--input`, `--output` and `--delimiter` override their configured values. Explicitly select `;` for semicolon-delimited inputs; the program does not guess the delimiter. Reports always use commas.

| Exit code | Meaning |
|---|---|
| `0` | Report completed, possibly with row warnings. |
| `1` | Report completed with warnings and `--fail-on-warnings` was requested. |
| `2` | File, CSV structure or configuration error; no replacement report is written. |

An existing report is preserved when input processing fails. Row-level bad data is retained in a warning row; a broken file structure fails the run instead of silently shifting columns.

## 3. Input contract

Use UTF-8 (a UTF-8 BOM is accepted). Header names are case-sensitive, with surrounding spaces trimmed. Required headers are `listing_id`, `municipality`, `price_eur` (or `price`) and `plot_area_m2` (or `plot_area`). Missing required headers, duplicate or unsupported headers, inconsistent row widths and files containing no records are file errors. Cells may be blank; missing numeric values and unknown booleans produce warnings, including optional fields.

| Field | Unit and accepted range | Legacy alias |
|---|---|---|
| `price_eur` | EUR, greater than zero | `price` |
| `plot_area_m2` | m², greater than zero | `plot_area` |
| `existing_building_m2` | m², zero or greater | `existing_building` |
| `far` | Dimensionless assumed/supplied ratio, greater than zero | — |
| `coverage_ratio` | Fraction from 0 to 1, or explicit 0% to 100% | `coverage` |
| `frontage_m` | m, greater than zero | `frontage` |
| `corner_plot` | True, false or unknown | `corner` |
| `inside_plan` | True, false or unknown | — |
| `demolition_candidate` | True, false or unknown | `demolition` |

Also supported: `source`, `url`, `title`, `neighbourhood`, `address`, `description`, `observed_at`, `far_source`, `far_date` and `assumptions`. Dates use the strict calendar format `YYYY-MM-DD`. Text records provenance and assumptions as supplied; the program does not verify them. A blank source becomes `MANUAL`; source names are uppercased. Missing IDs remain missing. Conflicting populated aliases generate warnings instead of choosing a value silently.

### Numbers: Greek and English formats

| Input | Interpretation |
|---|---|
| `1234` | Integer 1234 |
| `1234.56` or `1234,56` | Decimal 1234.56 |
| `1.234,56` | Greek grouping and decimal separator: 1234.56 |
| `1,234.56` | English grouping and decimal separator: 1234.56 |
| `1.234.567` or `1,234,567` | Correctly grouped integer 1234567 |
| `1 234,56` | Correctly grouped spaces: 1234.56; nonbreaking spaces also supported |
| `60%` in `coverage_ratio` | Fraction 0.6 |
| `60` in `coverage_ratio` | Invalid; never automatically interpreted as 60% |
| `1.234`, `1,234`, `0.800` | Ambiguous single separator; warning, value left blank |

A single separator with one to three digits before it and exactly three after it is deliberately ambiguous. Enter the intended integer without grouping (`1234`) or an unambiguous decimal (`1.2340`). Quote values containing the delimiter: `"450.000,00"` in a comma-delimited CSV.

Scientific notation, currency symbols, embedded units, invalid grouping, `NaN` and infinity are rejected. Percentages are accepted only for coverage, not FAR, prices or dimensions. Missing and rejected numbers remain blank in normalized output, never zero. Original strings remain available in `raw_input`.

### Booleans and duplicates

Booleans accept `yes/no`, `y/n`, `true/false`, `1/0` and `ναι/όχι` (case-insensitive). Blank, `unknown`, `?` and `n/a` mean unknown. Other tokens produce an invalid-boolean warning. Unknown is written as `unknown`, distinctly from `false`.

Duplicates are flagged on every matching row, across all supplied input files. Checks cover the same nonempty `(source, listing_id)`, the same nonempty URL, and an identical trimmed input row after excluding its ID. Rows are never silently removed. These checks do not establish whether differently described listings represent the same physical plot; there is no fuzzy matching.

## 4. Read and check the report

The report contains normalized plot fields, source-file/row provenance, retained source/date/assumption text, original input as JSON in `raw_input`, calculated metrics, `validation_status` and readable `warning_reasons`. Missing/invalid operands suppress only their dependent calculations.

| Metric | Calculation | Unit |
|---|---|---|
| `price_per_land_m2` | Asking price ÷ plot area | EUR/m² of plot |
| `indicative_floor_area_m2` | Plot area × supplied FAR | Indicative m² |
| `price_per_indicative_floor_m2` | Asking price ÷ indicative floor area | EUR/indicative m² |

Metrics use finite, positive operands and are displayed to two decimals. Calculations use Python's binary floating-point arithmetic; this is not an exact-decimal accounting ledger. Numeric input is already in the stated units; the program does not convert acres, square feet or other currencies. FAR is an unverified input. Missing FAR prevents the two FAR-dependent metrics, but a valid asking-price/plot-area ratio can still be reported.

Two hand-checkable examples from the synthetic fixture:

| Example | Price (EUR) | Plot (m²) | FAR | EUR/plot m² | Indicative m² | EUR/indicative m² |
|---|---:|---:|---:|---:|---:|---:|
| A | 300000 | 500 | 1.2 | 600.00 | 600.00 | 500.00 |
| B, Greek numeric input | 450000 | 500.5 | 1.2 | 899.10 | 600.60 | 749.25 |

For A: `300000 / 500 = 600`; `500 * 1.2 = 600`; `300000 / 600 = 500`. The full expected report, including warning reasons, is checked in at `fixtures/expected_report.csv`.

After the default run, compare the complete output exactly:

```bash
python -c "from pathlib import Path; assert Path('output/report.csv').read_bytes() == Path('fixtures/expected_report.csv').read_bytes(); print('Report matches expected output')"
```

Verification on Python 3.12.14 (Linux): **55 tests passed** in a fresh virtual environment. See [verification details](docs/verification.md) and [captured output](docs/test-run.txt).

Tests cover valid, incomplete, malformed, ambiguous and duplicate data, boolean handling, numeric boundaries, configuration, CLI behavior and the frozen report. Run `python -m unittest discover -s tests -v`; a successful run ends with `OK`. Test results apply to the environment and revision actually run, not every possible system or input.

## 5. Understand the code, one file at a time

| File | Purpose/change | How to check it |
|---|---|---|
| `collectors/manual_seed.py` | Reads CSV rows, parses values and preserves reasons/original input. Retains the indentation repair from the earlier milestone. | Inspect sample warning rows; run parsing tests. |
| `models/property.py` | Defines `PropertyListing` and its three guarded calculations. | Hand-check examples A and B; run calculation tests. |
| `analysis/quality.py` | Checks field presence and numeric ranges; blanks rejected values with specific reasons. | Inspect missing/invalid rows and `warning_reasons`. |
| `main.py` | Loads configuration, combines inputs, flags duplicates and writes a reproducible report. | Run the default command and exact output comparison. |
| `config.json` | Supplies real, editable defaults. | Change the output path or override it with `--output`. |
| `requirements.txt` | Records that no third-party dependency is required. | Install in a fresh virtual environment. |
| `fixtures/manual_seed.csv` | Eight entirely synthetic examples. | Open the input alongside the report. |
| `fixtures/expected_report.csv` | Frozen full expected result, including warning explanations. | Run the exact comparison above. |
| `tests/` | Automated checks of parsing, validation, calculations and workflow failures. | Run the test discovery command. |
| `docs/scenario_proposal.md` | Checked, hypothetical next-step model and sensitivity example. | Recalculate its worked examples; no extension code is active. |

## 6. Limits and next milestone

This is a local data-screening tool. Missing evidence remains missing; input sources and dates are not independently authenticated. Duplicate checks are conservative comparisons, not cadastral identity checks. The CSV dialect and number formats above are the supported contract; other formats need explicit conversion.

**Historical proposal:** the original scenario design is archived in [docs/scenario_proposal.md](docs/scenario_proposal.md). The smaller five-case implementation is described below; broader FAR sensitivity experiments remain unimplemented.

Gmail, Google Sheets, dashboards, scraping, machine learning, structural analysis and drawing checking are outside this milestone. No external integration is implemented or claimed as tested. No credentials, client records, private plans or company financial records are included.

## Milestone 2A — Five hypothetical development scenarios (implemented)

The original CSV validation pipeline remains available with `python main.py`.
A separate standard-library command compares **exactly two synthetic plots** under five predefined, symmetric changes to construction costs and assumed sale prices:

```bash
python -m analysis.scenarios
python -m unittest discover -s tests -v
```

Inputs: `fixtures/scenario_inputs.csv`. Generated report: `output/scenario_report.csv`. Checked reference: `fixtures/expected_scenario_report.csv`. The five cases are: base, construction cost +10%, sale price -10%, both adverse changes, and construction cost -10% with sale price +10%. Both plots receive the **same percentage changes** in each case.

All ten synthetic residual results and the arithmetic assumptions are explained in [`docs/scenarios.md`](docs/scenarios.md). This is deterministic **scenario arithmetic**, not legal buildability verification, a formal valuation, actual profit or investment advice. No Gmail, Google Sheets, dashboards, structural analysis, drawings, live market data or company-private information are involved. The earlier [`docs/scenario_proposal.md`](docs/scenario_proposal.md) is preserved as the original pre-implementation proposal and includes exploratory ideas that are **not** implemented.
