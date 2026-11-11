import csv
import os
import re
from models.property import PropertyListing

def float_or_none(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return None

def int_or_none(val):
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", ".")))
    except ValueError:
        return None

def extract_spitogatos_id(url):
    if not url:
        return None
    match = re.search(r'/aggelia/(\d+)', url)
    if match:
        return match.group(1)
    match_alt = re.search(r'(\d{8,})', url)
    return match_alt.group(1) if match_alt else None

def listings_from_manual_seed(filepath="fixtures/manual_seed.csv"):
    if not os.path.exists(filepath):
        print(f"[WARNING] Seed file not found at {filepath}")
        return []
        
    properties = []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row.get("source", "MANUAL").strip().upper()
            url = row.get("url", "").strip()
            
            listing_id = row.get("listing_id")
            if not listing_id:
                if source == "SPITOGATOS":
                    listing_id = extract_spitogatos_id(url)
                if not listing_id:
                    listing_id = url or "unknown_id"
            
            price_val = row.get("price") or row.get("price_eur")
            plot_val = row.get("plot_area") or row.get("plot_area_m2")
            existing_val = row.get("existing_building") or row.get("existing_building_m2")
            far_val = row.get("far")
            cov_val = row.get("coverage") or row.get("coverage_ratio")
            front_val = row.get("frontage") or row.get("frontage_m")
            
            item = PropertyListing(
                source=source,
                listing_id=str(listing_id),
                url=url,
                title=row.get("title", ""),
                municipality=row.get("municipality", "").strip(),
                neighbourhood=row.get("neighbourhood", "").strip(),
                address=row.get("address", "").strip(),
                price_eur=float_or_none(price_val),
                plot_area_m2=float_or_none(plot_val),
                existing_building_m2=float_or_none(existing_val),
                far=float_or_none(far_val),
                coverage_ratio=float_or_none(cov_val),
                frontage_m=float_or_none(front_val),
                corner_plot=bool(int_or_none(row.get("corner", 0))),
                inside_plan=bool(int_or_none(row.get("inside_plan", 1))),
                demolition_candidate=bool(int_or_none(row.get("demolition", 0))),
                description=row.get("description", "")
            )
            item.calculate()
            properties.append(item)
            
    return properties
