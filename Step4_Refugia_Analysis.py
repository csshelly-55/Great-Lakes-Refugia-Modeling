"""
================================================================================
THESIS PIPELINE - STEP 5: MULTI-SCENARIO SENSITIVITY ANALYSIS
Targets: Walleye, Yellow Perch, Lake Whitefish
Scenarios: Liberal, Moderate, Strict
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
SUITABILITY_DIR = os.path.join(PROJECT_DIR, "Rasters", "Final_Models")
AIS_DIR = os.path.join(PROJECT_DIR, "Rasters", "AIS_Cumulative_Impact")
OUT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Refugia")
GRID_SHP = os.path.join(
    DATA_RAW, "Great_Lakes_Grid_Cells", "Great_Lakes_Grid_Cells.shp"
)

# --- 2. DEFINE SCENARIOS ---
# Format: "Name": (Suitability_Min, AIS_Max)
SCENARIOS = {"Liberal": (7.0, 3.0), "Moderate": (7.5, 2.0), "Strict": (8.0, 1.0)}

SPORT_FISH = ["Walleye", "Yellow_Perch", "Lake_Whitefish"]
PIXEL_AREA = 3.24  # 1800m x 1800m

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True


def run_multi_scenario_analysis():
    print("--- Phase 5: Multi-Scenario Refugia Analysis ---")

    for target in SPORT_FISH:
        print(f"\n" + "=" * 60)
        print(f"🐟 SPECIES: {target.replace('_', ' ')}")
        print("=" * 60)

        suit_raster_path = os.path.join(SUITABILITY_DIR, f"FINAL_HSI_{target}.tif")
        ais_raster_path = os.path.join(
            AIS_DIR, target, f"Basin_Wide_AIS_Impact_{target}.tif"
        )

        if not arcpy.Exists(suit_raster_path) or not arcpy.Exists(ais_raster_path):
            print(f"  ❌ ERROR: Missing rasters for {target}. Skipping.")
            continue

        target_out_dir = os.path.join(OUT_DIR, target)
        if not os.path.exists(target_out_dir):
            os.makedirs(target_out_dir)

        # 1. Normalize AIS once per species
        suit_obj = arcpy.sa.Raster(suit_raster_path)
        ais_obj = arcpy.sa.Raster(ais_raster_path)
        ais_max = float(
            arcpy.management.GetRasterProperties(ais_obj, "MAXIMUM").getOutput(0)
        )
        norm_ais = (ais_obj / ais_max) * 10.0 if ais_max > 0 else ais_obj

        # 2. Setup the Grid for this species
        target_grid = os.path.join(target_out_dir, f"{target}_Comparison_Grid.shp")
        arcpy.management.Project(GRID_SHP, target_grid, suit_raster_path)
        oid_field = arcpy.Describe(target_grid).OIDFieldName

        # 3. Loop through Scenarios
        for name, thresholds in SCENARIOS.items():
            suit_min, ais_max_thresh = thresholds
            print(f"  ▶️ SCENARIO: {name} (Suit >= {suit_min}, AIS <= {ais_max_thresh})")

            # Calculate Binary Raster
            ref_bin = arcpy.sa.Con(
                (suit_obj >= suit_min) & (norm_ais <= ais_max_thresh), 1, 0
            )
            ref_path = os.path.join(target_out_dir, f"{target}_Refugia_{name}.tif")
            ref_bin.save(ref_path)

            # Zonal Statistics to add Area to the Grid
            temp_table = f"memory/stat_{name}"
            arcpy.sa.ZonalStatisticsAsTable(
                target_grid, oid_field, ref_path, temp_table, "DATA", "SUM"
            )

            # Join and create scenario-specific area field
            field_name = f"SqKm_{name[:3]}"  # e.g., SqKm_Lib, SqKm_Mod, SqKm_Str
            arcpy.management.AddField(target_grid, field_name, "DOUBLE")

            # Use a join and calculation to pull the SUM into our grid
            arcpy.management.JoinField(
                target_grid, oid_field, temp_table, oid_field, ["SUM"]
            )
            arcpy.management.CalculateField(
                target_grid,
                field_name,
                f"!SUM! * {PIXEL_AREA} if !SUM! else 0",
                "PYTHON3",
            )
            arcpy.management.DeleteField(target_grid, "SUM")

            print(f"    ✅ {name} results added to grid field: {field_name}")

    print("\n" + "=" * 50)
    print("🏆 MULTI-SCENARIO ANALYSIS COMPLETE!")
    print("Check individual species folders for comparison grids.")
    print("=" * 50)


if __name__ == "__main__":
    run_multi_scenario_analysis()
