# Milestone 2A — Five symmetric development scenarios

**Status:** Implemented as a separate local command. This is a transparent educational arithmetic comparison, not verified legal buildability, formal valuation, project profit or investment advice. All inputs are synthetic. Leadership ATE has not supplied data, tested or adopted this tool.

## Run

From the repository root with Python 3.10+ (no third-party dependencies):

```bash
python -m analysis.scenarios
python -m unittest discover -s tests -v
```

The scenario command reads `fixtures/scenario_inputs.csv`, prints five comparisons and writes `output/scenario_report.csv`. To use a different synthetic CSV or output:

```bash
python -m analysis.scenarios --input fixtures/scenario_inputs.csv --output output/another_report.csv
```

The original `python main.py` command and its CSV input/report remain unchanged.

## Input contract

Exactly two rows with distinct `plot_id` values and the exact header from `fixtures/scenario_inputs.csv`. Numeric values use dot-decimal notation without thousands separators or currency symbols. All numeric inputs must be finite. Plot area, assumed FAR, assumed saleable fraction, construction rate, assumed sale price and land price must be positive. Saleable fraction must not exceed 1. Other costs may be zero. `assumption_source` is required. The synthetic input records its provenance as `synthetic exercise`.

## Explicit equations

Let `P` be plot area, `f` assumed FAR, `s` assumed saleable fraction, `c` construction allowance per modeled floor m², `p` assumed sale price per saleable m², `L` land asking price, and `O` other-cost allowance.

- Floor-area proxy: `F = P * f`
- Saleable-area proxy: `S = F * s`
- Modeled construction cost: `C = F * c * (1 + construction_change)`
- Modeled sales: `R = S * p * (1 + sales_change)`
- Simplified residual: `R - C - L - O`

The **same** construction and sales percentage changes are applied to A and B for each scenario. Land and other-cost allowances stay fixed. The output includes both plots' residuals and their difference; it does not select a recommended acquisition.

## Checked synthetic example

| Input | A | B |
|---|---:|---:|
| Plot area (m²) | 500 | 600 |
| Assumed FAR | 1.20 | 1.00 |
| Assumed saleable fraction | 0.80 | 0.80 |
| Construction allowance (EUR / floor-area-proxy m²) | 1,800 | 1,750 |
| Assumed sale price (EUR / saleable-area-proxy m²) | 4,000 | 3,900 |
| Land asking price (EUR) | 350,000 | 300,000 |
| Other-cost allowance (EUR) | 120,000 | 130,000 |

Both plots have `F = 600 m²` and `S = 480 m²` under these assumptions.

For A, the base residual is `480*4000 - 600*1800 - 350000 - 120000 = EUR 370,000`.
For B, the base residual is `480*3900 - 600*1750 - 300000 - 130000 = EUR 392,000`.

| Scenario | Construction change (both) | Sale price change (both) | A residual (EUR) | B residual (EUR) | Larger residual |
|---|---:|---:|---:|---:|---|
| base | 0% | 0% | 370,000 | 392,000 | B |
| construction_plus_10pct | +10% | 0% | 262,000 | 287,000 | B |
| sales_minus_10pct | 0% | -10% | 178,000 | 204,800 | B |
| combined_stress | +10% | -10% | 70,000 | 99,800 | B |
| favorable | -10% | +10% | 670,000 | 684,200 | B |

All ten amounts are checked in `tests/test_scenarios.py` and stored in `fixtures/expected_scenario_report.csv`. The original 55 tests are retained.

## Limitations

- `P * f` is a **hypothetical floor-area proxy**, not verified building permission or constructed area. FAR, setbacks, height, coverage, site geometry and zoning need independent professional verification.
- The saleable fraction is an **assumption**, not measured or legally verified saleable floor area.
- Construction cost is charged against the modeled floor-area proxy, not a full quantity survey. Basements, parking, foundations, excavation, site conditions and unusual work may change actual costs.
- Land and other-cost allowances are illustrative. Financing, taxes, time value, sales timing, contingencies and omitted expenses are not modeled.
- The resulting **simplified residual** is not profit, valuation, feasibility approval or investment advice.
- Only two plots, five deterministic scenarios and uniform percentage shocks are supported. No probabilities, simulation, live market prices or real company data are involved.
- CSV writes are not transactional in the event of a disk write failure; inputs are validated before writing, and the input path cannot equal the output path.
