"""
================================================================================
THESIS PIPELINE - STEP 1H: CLARITY & DEPTH BASELINES
Targets: Walleye, Lake Whitefish, Yellow Perch
Description:
1. Water Clarity: Uses CopyRaster to strip the NOAA corruption bug, projects
   the clean raster to Albers, and uses Spatial Analyst Extract by Mask.
2. Bathymetry: Skips if master surface already exists.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
SHP_DIR = os.path.join(DATA_RAW, "Lake_Boundaries")
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
KD490_IN = os.path.join(DATA_RAW, "CoastWatch_Kd490.tif")

# ArcPy Environments
arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def process_raster_baselines():
    print("--- Phase 1h: Water Clarity & Depth Baselines ---")
    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    # ==========================================================================
    # PART A: WATER CLARITY (Kd490)
    # ==========================================================================
    print("\n  🛰️ Processing Water Clarity (Kd490)...")
    if arcpy.Exists(KD490_IN):
        lake_shps = [os.path.join(SHP_DIR, lake, f"{lake}.shp") for lake in LAKES]
        valid_lakes = [shp for shp in lake_shps if arcpy.Exists(shp)]

        mem_merged = r"memory\Merged_Lakes"
        temp_clean = os.path.join(ENV_DIR, "temp_clean_kd490.tif")
        temp_proj = os.path.join(ENV_DIR, "temp_proj_kd490.tif")
        out_kd490 = os.path.join(ENV_DIR, "Kd490_Surface_Binational.tif")

        try:
            # 1. Merge Lakes for a single master mask
            arcpy.management.Merge(valid_lakes, mem_merged)

            # 2. Strip raw satellite formatting
            print("    -> 🧹 Stripping raw satellite formatting...")
            arcpy.management.CopyRaster(KD490_IN, temp_clean)

            # 3. Project Raster to USGS Albers
            print("    -> 🗺️ Projecting Raster to USGS Albers...")
            arcpy.management.ProjectRaster(temp_clean, temp_proj, usgs_albers)

            # 4. Extract by Mask (Safely snaps pixels to the lake boundaries)
            print("    -> ✂️ Extracting by Mask (Spatial Analyst)...")
            arcpy.env.mask = mem_merged
            arcpy.env.extent = mem_merged
            arcpy.sa.ExtractByMask(temp_proj, mem_merged).save(out_kd490)

            print("    -> 🏆 MASTER SAVED: Kd490_Surface_Binational.tif")

        except Exception as e:
            print(f"    -> ❌ Failed to process Kd490 Clarity: {e}")

        finally:
            # Clean up environment & temp files
            arcpy.env.mask = None
            arcpy.env.extent = None
            for temp_file in [temp_clean, temp_proj]:
                if arcpy.Exists(temp_file):
                    try:
                        arcpy.management.Delete(temp_file)
                    except:
                        pass
            if arcpy.Exists(mem_merged):
                arcpy.management.Delete(mem_merged)
    else:
        print(f"    -> ⚠️ Could not find Clarity raster at {KD490_IN}")

    # ==========================================================================
    # PART B: DEPTH (Bathymetry)
    # ==========================================================================
    print("\n  🌊 Processing Bathymetry (Depth)...")
    out_depth = os.path.join(ENV_DIR, "Depth_Surface_Binational.tif")

    if arcpy.Exists(out_depth):
        print("    -> ✅ Master Depth Surface already exists. Skipping.")
    else:
        print(
            "    -> ⚠️ Depth missing. Please re-run the extraction code block if needed."
        )


if __name__ == "__main__":
    process_raster_baselines()
