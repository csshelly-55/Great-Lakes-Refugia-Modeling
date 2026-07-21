"""
================================================================================
THESIS PIPELINE - STEP 2C: CARTOGRAPHIC ZERO-PATCHING
Description:
Sweeps through the Final HSI models and converts any leftover NoData patches
(caused by raster resolution boundary clashing) into a strict score of 0.
This standardizes the final cartographic symbology from 0 to 10.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")
FINAL_DIR = os.path.join(PROJECT_DIR, "Rasters", "Final_Models")

arcpy.env.workspace = FINAL_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def zero_out_nodata():
    print("--- Phase 2c: Cartographic Zero-Patching ---")
    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    # Use Master Depth to ensure we only put 0s in the water, not on the land
    basin_mask = os.path.join(ENV_DIR, "Depth_Surface_Binational.tif")
    if arcpy.Exists(basin_mask):
        arcpy.env.mask = basin_mask
        arcpy.env.extent = basin_mask
    else:
        print("  ❌ ERROR: Master basin mask not found.")
        return

    species_list = ["Walleye", "Yellow_Perch", "Lake_Whitefish"]

    for species in species_list:
        file_name = f"FINAL_HSI_{species}.tif"
        file_path = os.path.join(FINAL_DIR, file_name)
        temp_path = os.path.join(FINAL_DIR, f"temp_{file_name}")

        if arcpy.Exists(file_path):
            try:
                print(f"  🩹 Scanning {species} for NoData gaps...")

                # Logic: If pixel is NoData, give it a 0. Otherwise, keep original HSI score.
                patched = arcpy.sa.Con(arcpy.sa.IsNull(file_path), 0, file_path)
                patched.save(temp_path)

                # Release memory lock
                del patched

                # Safely overwrite original using CopyRaster
                arcpy.management.CopyRaster(temp_path, file_path)
                arcpy.management.Delete(temp_path)

                print(f"    -> ✅ Converted empty patches to 0 in {file_name}")
            except Exception as e:
                print(f"    -> ❌ Error patching {file_name}: {e}")
        else:
            print(f"    -> ⚠️ Could not find {file_name}")

    # Cleanup environment
    arcpy.env.mask = None
    arcpy.env.extent = None

    print("\n==================================================")
    print("🏆 STEP 2C COMPLETE: Final Models Cartographically Polished.")
    print("==================================================")


if __name__ == "__main__":
    zero_out_nodata()
