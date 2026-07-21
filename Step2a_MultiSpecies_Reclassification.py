"""
================================================================================
THESIS PIPELINE - STEP 2A: MULTI-SPECIES RECLASSIFICATION & GAP PATCHING
Targets: Walleye, Yellow Perch, Lake Whitefish
Description:
1. Iterates through the Environmental Warehouse and applies species-specific
   biological rubrics to convert raw physical units into 1-10 Suitability Scores.
2. INTEGRATED NODATA PATCHER: Finds unmapped gaps in satellite data (Kd490)
   and shapefiles (Substrate), filling them with a neutral biological score (5)
   so the downstream Weighted Sum Map Algebra does not delete the final models.
   * UPGRADE: Uses temp files to safely bypass ArcPy read-locks during patching.
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

arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def reclassify_and_patch():
    print("--- Phase 2a: Multi-Species Biological Reclassification ---")
    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    # ==========================================================================
    # PART 1: RECLASSIFICATION
    # ==========================================================================
    species_rubrics = {
        "Walleye": {
            "Temp_Surface_Binational.tif": [
                [-10, 12.9, 1],
                [13, 15.9, 4],
                [16, 18.9, 7],
                [19, 23.0, 10],
                [23.1, 25.9, 7],
                [26, 27.9, 4],
                [28, 50, 1],
            ],
            "Kd490_Surface_Binational.tif": [
                [0.0, 0.19, 3],
                [0.2, 0.39, 7],
                [0.4, 0.99, 10],
                [1.0, 2.49, 6],
                [2.5, 50.0, 2],
            ],
            "DO_Surface_Binational.tif": [
                [0, 1.99, 1],
                [2.0, 2.99, 4],
                [3.0, 5.0, 10],
                [5.01, 8.0, 7],
                [8.01, 50, 5],
            ],
            "Slope_Surface_Binational.tif": [
                [0, 0.99, 3],
                [1.0, 5.0, 10],
                [5.01, 10.0, 5],
                [10.01, 90.0, 2],
            ],
            "Tributary_Distance_Binational.tif": [
                [0, 2000, 10],
                [2000.01, 5000, 7],
                [5000.01, 10000, 4],
                [10000.01, 999999, 2],
            ],
            "Runoff_Distance_Binational.tif": [
                [0, 1000, 1],
                [1000.01, 2000, 3],
                [2000.01, 5000, 6],
                [5000.01, 999999, 10],
            ],
        },
        "Yellow_Perch": {
            "Temp_Surface_Binational.tif": [
                [-10, 14.9, 2],
                [15, 17.9, 5],
                [18, 20.9, 8],
                [21, 25.0, 10],
                [25.1, 27.0, 8],
                [27.1, 50, 2],
            ],
            "DO_Surface_Binational.tif": [
                [0, 1.99, 2],
                [2.0, 3.99, 5],
                [4.0, 6.0, 10],
                [6.01, 50, 7],
            ],
            "Fetch_Surface_Binational.tif": [
                [0, 1000, 10],
                [1000.01, 5000, 7],
                [5000.01, 15000, 4],
                [15000.01, 999999, 2],
            ],
            "Runoff_Distance_Binational.tif": [
                [0, 1000, 1],
                [1000.01, 2000, 3],
                [2000.01, 5000, 6],
                [5000.01, 999999, 10],
            ],
            "Vegetation_Distance_Binational.tif": [
                [0, 1000, 10],
                [1000.01, 3000, 7],
                [3000.01, 5000, 4],
                [5000.01, 999999, 1],
            ],
        },
        "Lake_Whitefish": {
            "Temp_Surface_Binational.tif": [
                [-10, 11.9, 10],
                [12, 14.9, 7],
                [15, 17.9, 4],
                [18, 50, 1],
            ],
            "DO_Surface_Binational.tif": [[0, 4.9, 1], [5.0, 6.9, 5], [7.0, 50, 10]],
            "Depth_Surface_Binational.tif": [
                [-500.0, -50.01, 10],  # 10: > 50m deep (Negative 50 to 500)
                [-50.0, -30.01, 7],  # 7: 30-50m deep
                [-30.0, -15.01, 4],  # 4: 15-30m deep
                [-15.0, 0.0, 1],  # 1: 0-15m deep (Too shallow)
                [0.01, 200.0, 1],  # 1: Above water surface / Land anomalies
            ],
            "Spawning_Distance_Binational.tif": [
                [0, 2000, 10],
                [2000.01, 5000, 7],
                [5000.01, 10000, 4],
                [10000.01, 999999, 1],
            ],
        },
    }

    for species, layers in species_rubrics.items():
        print(f"\n🐟 GENERATING SUITABILITY FOR: {species.replace('_', ' ')}")
        for raster_name, logic in layers.items():
            in_raster = os.path.join(ENV_DIR, raster_name)
            var_name = raster_name.split("_")[0]
            out_name = f"{species}_{var_name}_Suitability.tif"
            out_raster = os.path.join(SUIT_DIR, out_name)

            if not arcpy.Exists(in_raster):
                continue

            try:
                remap_logic = arcpy.sa.RemapRange(logic)
                suitability_raster = arcpy.sa.Reclassify(
                    in_raster, "VALUE", remap_logic, "NODATA"
                )
                suitability_raster.save(out_raster)
                print(f"  ✅ SAVED: {out_name}")
            except Exception as e:
                print(f"  ❌ Failed to reclassify {var_name}: {e}")

    # ==========================================================================
    # PART 2: INTEGRATED NODATA PATCHER (BULLETPROOF SWAP)
    # ==========================================================================
    print("\n🩹 SCANNING FOR NODATA INFECTIONS (Unmapped Gaps)...")

    basin_mask = os.path.join(ENV_DIR, "Depth_Surface_Binational.tif")
    if arcpy.Exists(basin_mask):
        arcpy.env.mask = basin_mask
        arcpy.env.extent = basin_mask

    problem_rasters = [
        "Lake_Whitefish_Substrate_Suitability.tif",
        "Walleye_Kd490_Suitability.tif",
        "Walleye_Substrate_Suitability.tif",
        "Walleye_Slope_Suitability.tif",
    ]

    for r_name in problem_rasters:
        r_path = os.path.join(SUIT_DIR, r_name)
        temp_path = os.path.join(SUIT_DIR, f"temp_{r_name}")

        if arcpy.Exists(r_path):
            try:
                # 1. Calculate patch and save to temp
                patched_raster = arcpy.sa.Con(arcpy.sa.IsNull(r_path), 5, r_path)
                patched_raster.save(temp_path)
                del patched_raster  # Force ArcPy to release memory lock

                # 2. Safely overwrite the original using CopyRaster
                arcpy.management.CopyRaster(temp_path, r_path)
                arcpy.management.Delete(temp_path)

                print(f"    -> ✅ Patched holes in {r_name}")
            except Exception as e:
                print(f"    -> ❌ Failed to patch {r_name}: {e}")

    arcpy.env.mask = None
    arcpy.env.extent = None

    print("\n==================================================")
    print("🏆 STEP 2A COMPLETE: All Suitability Models Reclassified and Patched.")
    print("==================================================")


if __name__ == "__main__":
    reclassify_and_patch()
