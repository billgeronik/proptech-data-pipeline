"""One normalized listing. Missing numbers and unknown booleans stay None."""

from dataclasses import dataclass, field
import math


@dataclass
class PropertyListing:
    source: str = "MANUAL"
    listing_id: str = ""
    url: str = ""
    title: str = ""
    municipality: str = ""
    neighbourhood: str = ""
    address: str = ""
    price_eur: float | None = None
    plot_area_m2: float | None = None
    existing_building_m2: float | None = None
    far: float | None = None
    coverage_ratio: float | None = None
    frontage_m: float | None = None
    corner_plot: bool | None = None
    inside_plan: bool | None = None
    demolition_candidate: bool | None = None
    description: str = ""
    observed_at: str = ""
    far_source: str = ""
    far_date: str = ""
    assumptions: str = ""
    input_file: str = ""
    input_line: int = 0
    raw_values: dict[str, str] = field(default_factory=dict)
    raw_errors: list[str] = field(default_factory=list)
    calculation_warnings: list[str] = field(default_factory=list)
    price_per_land_m2: float | None = None
    indicative_floor_area_m2: float | None = None
    price_per_indicative_floor_m2: float | None = None

    def calculate(self):
        """Screening arithmetic only; FAR is supplied, never legally verified.

        Reset results so changing an input cannot leave a stale calculation.
        Guard results as well as inputs: finite inputs can still overflow.
        """
        self.price_per_land_m2 = None
        self.indicative_floor_area_m2 = None
        self.price_per_indicative_floor_m2 = None
        self.calculation_warnings.clear()

        def positive(value):
            return value is not None and not isinstance(value, bool) and math.isfinite(value) and value > 0

        def store_result(name, value):
            if math.isfinite(value) and value > 0:
                setattr(self, name, value)
            else:
                self.calculation_warnings.append(
                    f"{name}: numeric overflow or underflow; result left blank"
                )

        if positive(self.price_eur) and positive(self.plot_area_m2):
            store_result("price_per_land_m2", self.price_eur / self.plot_area_m2)
        if positive(self.plot_area_m2) and positive(self.far):
            store_result("indicative_floor_area_m2", self.plot_area_m2 * self.far)
        if positive(self.price_eur) and positive(self.indicative_floor_area_m2):
            store_result("price_per_indicative_floor_m2", self.price_eur / self.indicative_floor_area_m2)
