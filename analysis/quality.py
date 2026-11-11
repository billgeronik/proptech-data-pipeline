def evaluate_data_quality(property_item):
    reasons = []
    if not property_item.municipality:
        reasons.append("MISSING_LOCATION")
    if (
        property_item.price_eur is None
        or property_item.price_eur <= 0
    ):
        reasons.append("MISSING_PRICE")
    if (
        property_item.plot_area_m2 is None
        or property_item.plot_area_m2 <= 0
    ):
        reasons.append("MISSING_PLOT_AREA")
    if (
        property_item.far is None
        or property_item.far <= 0
    ):
        reasons.append("MISSING_FAR")
    if property_item.coverage_ratio is None:
        reasons.append("MISSING_COVERAGE")
    if property_item.frontage_m is None:
        reasons.append("MISSING_FRONTAGE")
    return reasons
