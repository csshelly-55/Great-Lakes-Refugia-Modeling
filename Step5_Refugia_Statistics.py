"""
================================================================================
THESIS PIPELINE - STEP 6: MULTI-SCENARIO STATISTICAL EXTRACTION
Targets: Walleye, Yellow Perch, Lake Whitefish
Scenarios: Liberal, Moderate, Strict
================================================================================
"""

import arcpy
import os
import pandas as pd

# --- SETTINGS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
REF_DIR_BASE = os.path.join(PROJECT_DIR, "Rasters", "Refugia")
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Final_Models")
LAKE_BOUNDS = os.path.join(PROJECT_DIR, "Data_Raw", "Lake_Boundaries")
OUT_CSV = os.path.join(PROJECT_DIR, "Final_Thesis_MultiScenario_Stats.csv")

SPORT_FISH = ["Walleye", "Yellow_Perch", "Lake_Whitefish"]
LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
SCENARIOS = ["Liberal", "Moderate", "Strict"]
PIXEL_AREA_SQKM = 3.24

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True


def get_table_value(table, field):
    """Utility to read Zonal Stats results."""
    try:
        with arcpy.da.SearchCursor(table, [field]) as cursor:
            for row in cursor:
                return float(row[0]) if row[0] is not None else 0.0
    except:
        return 0.0
    return 0.0


def run_multi_stats():
    print("--- Phase 6: Multi-Scenario Statistical Extraction ---")
    results = []

    for target in SPORT_FISH:
        print(f"\n📈 EXTRACTING DATA: {target}")

        suit_path = os.path.join(SUIT_DIR, f"FINAL_HSI_{target}.tif")
        ras_sr = arcpy.Describe(suit_path).spatialReference

        for scenario in SCENARIOS:
            print(f"  ▶ Scenario: {scenario}")

            # Map paths to the specific scenario files generated in Step 5
            ref_path = os.path.join(
                REF_DIR_BASE, target, f"{target}_Refugia_{scenario}.tif"
            )

            # We need to define "Potential Habitat" for each scenario
            # (since the HSI threshold changes: 7.0, 7.5, 8.0)
            hsi_thresh = (
                7.0 if scenario == "Liberal" else 7.5 if scenario == "Moderate" else 8.0
            )
            pot_suit_binary = arcpy.sa.Con(
                arcpy.sa.Raster(suit_path) >= hsi_thresh, 1, 0
            )

            for lake in LAKES:
                lake_shp = os.path.join(LAKE_BOUNDS, lake, f"{lake}.shp")
                if not arcpy.Exists(lake_shp):
                    continue

                temp_lake = f"memory/lake_{lake}_{scenario}"
                arcpy.management.Project(lake_shp, temp_lake, ras_sr)
                oid = arcpy.Describe(temp_lake).OIDFieldName

                try:
                    # 1. Potential Area for this scenario's HSI threshold
                    t1 = f"memory/t_pot"
                    arcpy.sa.ZonalStatisticsAsTable(
                        temp_lake, oid, pot_suit_binary, t1, "DATA", "SUM"
                    )
                    pot_area = get_table_value(t1, "SUM") * PIXEL_AREA_SQKM

                    # 2. Actual Refugia Area for this scenario
                    t2 = f"memory/t_ref"
                    arcpy.sa.ZonalStatisticsAsTable(
                        temp_lake, oid, ref_path, t2, "DATA", "SUM"
                    )
                    ref_area = get_table_value(t2, "SUM") * PIXEL_AREA_SQKM

                    pct = (ref_area / pot_area * 100) if pot_area > 0 else 0

                    results.append(
                        {
                            "Species": target,
                            "Scenario": scenario,
                            "Lake": lake,
                            "Potential_Habitat_SqKm": round(pot_area, 2),
                            "Refugia_Area_SqKm": round(ref_area, 2),
                            "Pct_Protected": round(pct, 1),
                        }
                    )
                except:
                    pass
                finally:
                    for t in [t1, t2, temp_lake]:
                        if arcpy.Exists(t):
                            arcpy.management.Delete(t)

    # Export to CSV
    df = pd.DataFrame(results)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n🏆 MULTI-SCENARIO STATS SAVED TO: {OUT_CSV}")


if __name__ == "__main__":
    run_multi_stats()
