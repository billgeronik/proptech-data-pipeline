"""Explain data problems before calculating; no planning or safety certification."""

import math


def evaluate_data_quality(item, duplicate=False):
    """Return reasons and blank invalid numbers while retaining original input.

    Parsing asks 'is this a number?'; this function asks 'is its value allowed?'.
    A missing value and a supplied invalid value have different explanations.
    """
    issues = list(item.raw_errors)

    def add(reason):
        if reason not in issues:
            issues.append(reason)

    def field_has_issue(name):
        return any(reason.startswith(name + ":") for reason in issues)

    if not item.listing_id:
        add("listing_id: missing; provide a stable identifier; none was invented")
    if duplicate:
        add("listing_id: duplicate source + listing_id; all occurrences retained")
    if not item.municipality:
        add("municipality: missing; location is unknown")

    # Unit and range checks, independent of how the number was formatted.
    rules = {
        "price_eur": (lambda v: v > 0, "greater than zero EUR"),
        "plot_area_m2": (lambda v: v > 0, "greater than zero m2"),
        "existing_building_m2": (lambda v: v >= 0, "nonnegative m2"),
        "far": (lambda v: v > 0, "greater than zero (dimensionless)"),
        "coverage_ratio": (lambda v: 0 <= v <= 1, "between 0 and 1; use % for a percentage"),
        "frontage_m": (lambda v: v > 0, "greater than zero m"),
    }
    for name, (allowed, explanation) in rules.items():
        value = getattr(item, name)
        if value is None:
            if not field_has_issue(name):
                consequence = {
                    "price_eur": "; both asking-price ratios remain blank",
                    "plot_area_m2": "; all three metrics remain blank",
                    "far": "; indicative floor-area metrics remain blank",
                }.get(name, "")
                add(f"{name}: missing; unknown, not zero{consequence}")
        elif isinstance(value, bool) or not math.isfinite(value) or not allowed(value):
            reason = f"{name}: invalid value {value!r}; must be finite and {explanation}; normalized value left blank"
            add(reason)
            if reason not in item.raw_errors:
                item.raw_errors.append(reason)
            setattr(item, name, None)

    for name in ("corner_plot", "inside_plan", "demolition_candidate"):
        if getattr(item, name) is None and not field_has_issue(name):
            add(f"{name}: unknown; not assumed false")
    return issues
