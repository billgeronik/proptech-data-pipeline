# Proposed next milestone: hypothetical development scenarios

**Historical design proposal (retained for reference).** The smaller five-case symmetric comparison is now implemented as Milestone 2A; see `docs/scenarios.md`. The single-plot FAR sensitivity experiments below remain illustrative and are **not** implemented. All amounts and assumptions below are synthetic, created for a reproducible arithmetic example. They are not market estimates or Leadership ATE data. The company has not been represented as testing or adopting this tool.

## The question

What arithmetic follows from a stated set of plot, floor-area, cost and sale-price assumptions, and how much does the result change when one assumption changes?

Keep supplied listing information separate from editable scenario assumptions. For example, a listing's `far` and an experiment's `assumed_far` must remain separate fields. A hypothetical FAR does not establish that a particular building can lawfully be constructed.

## Small proposed scope

Add one scenario CSV, one calculation module, one scenario report and tests reproducing these worked examples. Reference each plot by source and listing ID, together with a unique scenario ID. Record the assumption source, date and explanatory notes; these examples would use `synthetic exercise` as their source.

No dashboard, integration, optimization engine or acquisition recommendation is needed. Missing, invalid or non-finite inputs should prevent dependent calculations with a clear explanation, using the same principles as the first milestone.

## Explicit model

| Symbol | Input | Unit |
|---|---|---|
| P | Plot area | m² |
| f | Assumed FAR | Dimensionless |
| s | Separately assumed saleable fraction | Fraction from 0 to 1 |
| c | Construction allowance per modeled floor-area unit | EUR/m² |
| p | Assumed sale price per assumed saleable-area unit | EUR/m² |
| L | Land asking price | EUR |
| O | Other project-cost allowance | EUR |

Calculate:

```text
scenario_floor_area_proxy = P × f
assumed_saleable_area_proxy = scenario_floor_area_proxy × s
modeled_construction_cost = scenario_floor_area_proxy × c
modeled_sales_proceeds = assumed_saleable_area_proxy × p
simplified_residual = modeled_sales_proceeds − modeled_construction_cost − L − O
```

For this deliberately small model, construction costing uses the same area as the floor-area proxy. That is an explicit simplification: basements, parking and other constructed spaces could require separate area and cost assumptions in a real study. Multiplication by FAR does not establish actual gross constructed or saleable area.

Call the final quantity **simplified residual before financing, taxes and omitted costs**, not project profit or a valuation. `O` is a stated synthetic allowance, not a complete cost estimate. Costs and proceeds use a common fictional basis for this exercise; no tax or market assumptions are inferred.

## Checked worked example

| Input or calculation | Hypothetical plot A | Hypothetical plot B |
|---|---:|---:|
| Plot area P | 500 m² | 600 m² |
| Assumed FAR f | 1.20 | 1.00 |
| Floor-area proxy | 600 m² | 600 m² |
| Assumed saleable fraction s | 80% | 80% |
| Assumed saleable-area proxy | 480 m² | 480 m² |
| Construction allowance c | EUR 1,800/m² | EUR 1,750/m² |
| Assumed sale price p | EUR 4,000/m² | EUR 3,900/m² |
| Land asking price L | EUR 350,000 | EUR 300,000 |
| Other-cost allowance O | EUR 120,000 | EUR 130,000 |
| Modeled construction cost | EUR 1,080,000 | EUR 1,050,000 |
| Modeled sales proceeds | EUR 1,920,000 | EUR 1,872,000 |
| **Simplified residual** | **EUR 370,000** | **EUR 392,000** |

For A:

```text
500 × 1.20 = 600 m² floor-area proxy
600 × 0.80 = 480 m² assumed saleable-area proxy
600 × EUR 1,800 = EUR 1,080,000 construction allowance
480 × EUR 4,000 = EUR 1,920,000 modeled proceeds
EUR 1,920,000 − 1,080,000 − 350,000 − 120,000 = EUR 370,000
```

For B:

```text
600 × 1.00 × 0.80 × EUR 3,900 = EUR 1,872,000 modeled proceeds
600 × 1.00 × EUR 1,750 = EUR 1,050,000 construction allowance
EUR 1,872,000 − 1,050,000 − 300,000 − 130,000 = EUR 392,000
```

B's residual is EUR 22,000 higher under this input set. This does not establish that B is a better acquisition.

## Change one assumption at a time

Keep B fixed at its base assumptions. Change only the listed input for A:

| A scenario | A's simplified residual | Change from A's base |
|---|---:|---:|
| Base | EUR 370,000 | — |
| Assumed FAR decreases to 1.00 | EUR 230,000 | −EUR 140,000 |
| Assumed FAR increases to 1.30 | EUR 440,000 | +EUR 70,000 |
| Construction allowance increases 10% to EUR 1,980/m² | EUR 262,000 | −EUR 108,000 |
| Assumed sale price decreases 10% to EUR 3,600/m² | EUR 178,000 | −EUR 192,000 |
| Assumed saleable fraction decreases to 70% | EUR 130,000 | −EUR 240,000 |

At assumed FAR 1.30, A's area proxy becomes 650 m² and assumed saleable-area proxy becomes 520 m². Proceeds become EUR 2,080,000 and construction allowance becomes EUR 1,170,000. The residual is EUR 440,000, which exceeds B's unchanged EUR 392,000 by EUR 48,000. **The change reverses the arithmetic ordering without establishing that FAR 1.30 is legally available.**

These examples change one input at a time to make effects easy to understand. They do not model correlations, probabilities, time, financing or an expected return.

## Verification and limits

The base and sensitivity calculations were executed using Python's standard-library `decimal.Decimal`; both base residuals were also asserted against the expected values. No scenario feature was added to the pipeline. The arithmetic can be checked with the formulas and intermediate results above.

The model contains no verified planning rules, building design, construction schedule, structural or geotechnical assessment, legal review, taxes, financing, market evidence or complete project cost estimate. Outputs are scenario comparisons, not verified buildability, saleable floor area, formal valuations or investment advice. Source provenance and limitations must remain visible in any later implementation.
