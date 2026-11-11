import os
import yaml
from collectors.manual_seed import listings_from_manual_seed
from analysis.quality import evaluate_data_quality

def main():
    if not os.path.exists("config.yaml"):
        print("[ERROR] config.yaml not found.")
        return

    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_properties = []

    for source in config.get("sources", []):
        if not source.get("enabled", False):
            continue
        
        mode = source.get("mode")
        if mode == "manual_seed":
            for seed_file in source.get("seed_files", []):
                try:
                    properties = listings_from_manual_seed(seed_file)
                    all_properties.extend(properties)
                except Exception as e:
                    print(f"[ERROR] Manual seed source {source['name']}: {e}")

    print(f"\nProcessed {len(all_properties)} canonical listings:")
    for prop in all_properties:
        issues = evaluate_data_quality(prop)
        prop.reasons = ", ".join(issues) if issues else "OK"
        
        print("-----------------------------------")
        print("Source:", prop.source)
        print("ID:", prop.listing_id)
        print("Περιοχή:", prop.municipality, f"({prop.neighbourhood})")
        print("Τιμή:", prop.price_eur, "€")
        print("Οικόπεδο:", prop.plot_area_m2, "m²")
        print("Σ.Δ. (FAR):", prop.far if prop.far is not None else "ΑΓΝΩΣΤΟ")
        print("€/m² Οικοπέδου:", round(prop.price_per_land_m2, 2) if prop.price_per_land_m2 else "N/A")
        print("Status:", prop.status)
        print("Reasons/Flags:", prop.reasons)

if __name__ == "__main__":
    main()
