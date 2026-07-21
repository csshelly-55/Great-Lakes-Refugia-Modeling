"""
================================================================================
THESIS PIPELINE - STEP 2A.5: COMPOUNDING STRESSOR HOTSPOTS
Targets: Lake Whitefish (Oxythermal Squeeze)
Description:
Uses Boolean Map Algebra (Conditional Statements) to identify areas where high
temperatures and low dissolved oxygen intersect, creating lethal compounding
stressors for cold-water species. Outputs a standard 1-10 Suitability raster.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Suitability")

if not os.path.exists(SUIT_DIR):
    os.makedirs(SUIT_DIR)

TARGET_SPECIES = "Lake_Whitefish"

# ArcPy Environments
arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_compounding_stressors():
    print("--- Phase 2a.5: Lake Whitefish Compounding Stressors ---")

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    # 1. Define inputs
    temp_path = os.path.join(ENV_DIR, "Temp_Surface_Binational.tif")
    do_path = os.path.join(ENV_DIR, "DO_Surface_Binational.tif")
    out_path = os.path.join(SUIT_DIR, f"{TARGET_SPECIES}_Stressor_Suitability.tif")

    if not arcpy.Exists(temp_path) or not arcpy.Exists(do_path):
        print("  ❌ ERROR: Missing Temp or DO baselines in the Environmental folder.")
        return

    print("  🧮 Executing Boolean Map Algebra for Oxythermal Squeeze...")

    # Load as ArcPy Raster Objects for Map Algebra
    temp_raster = arcpy.sa.Raster(temp_path)
    do_raster = arcpy.sa.Raster(do_path)

    try:
        # 2. The Conditional (Con) Logic
        # Condition 1: Extreme Squeeze (Temp > 15 AND DO < 5) -> Score 1
        # Condition 2: Moderate Squeeze (Temp > 12 AND DO < 7) -> Score 4
        # Condition 3: Safe/No Squeeze -> Score 10

        moderate_con = arcpy.sa.Con((temp_raster > 12) & (do_raster < 7), 4, 10)
        extreme_con = arcpy.sa.Con(
            (temp_raster > 15) & (do_raster < 5), 1, moderate_con
        )

        # Save the result
        extreme_con.save(out_path)
        print(f"  ✅ SAVED: {os.path.basename(out_path)}")

    except Exception as e:
        print(f"  ❌ ERROR generating Compounding Stressors: {e}")

    print("\n==================================================")
    print("🏆 STEP 2A.5 COMPLETE: Stressor Hotspot Model Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_compounding_stressors()
