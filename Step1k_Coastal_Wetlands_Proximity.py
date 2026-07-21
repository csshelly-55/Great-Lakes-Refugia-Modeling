"""
================================================================================
THESIS PIPELINE - STEP 1K: COASTAL WETLANDS PROXIMITY
Targets: Yellow Perch
Description:
Calculates continuous Euclidean distance (1800m res) from the Great Lakes
Coastal Wetlands shapefile, strictly masked to the waterbodies.
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
WETLANDS_SHP = os.path.join(
    DATA_RAW, "Great_Lakes_Coastal_Wetlands", "Great_Lakes_Coastal_Wetlands.shp"
)

arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def process_wetlands_baselines():
    print("--- Phase 1k: Coastal Wetlands Proximity ---")

    if not arcpy.Exists(WETLANDS_SHP):
        print(f"  ❌ ERROR: Wetlands Shapefile not found at {WETLANDS_SHP}")
        return

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    lake_veg_rasters = []

    # 1. Process Lake-by-Lake
    for lake in LAKES:
        print(f"\n  📏 Calculating Wetlands Distance for {lake}...")
        lake_shp = os.path.join(SHP_DIR, lake, f"{lake}.shp")
        if not arcpy.Exists(lake_shp):
            continue

        arcpy.env.mask = lake_shp
        arcpy.env.extent = lake_shp

        temp_veg = os.path.join(ENV_DIR, f"temp_VegDist_{lake}.tif")
        try:
            arcpy.sa.EucDistance(WETLANDS_SHP, cell_size=1800).save(temp_veg)
            lake_veg_rasters.append(temp_veg)
            print("    -> ✅ Extracted successfully.")
        except Exception as e:
            print(f"    -> ❌ Failed to calculate: {e}")

        arcpy.env.mask = None
        arcpy.env.extent = None

    # 2. Mosaic
    if lake_veg_rasters:
        print("\n  🧩 Mosaicing Vegetation Baselines...")
        try:
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_veg_rasters,
                output_location=ENV_DIR,
                raster_dataset_name_with_extension="Vegetation_Distance_Binational.tif",
                coordinate_system_for_the_raster=usgs_albers,
                pixel_type="32_BIT_FLOAT",
                number_of_bands=1,
                mosaic_method="MINIMUM",
            )
            print("  🏆 MASTER SAVED: Vegetation_Distance_Binational.tif")
            for r in lake_veg_rasters:
                if arcpy.Exists(r):
                    arcpy.management.Delete(r)
        except Exception as e:
            print(f"  ❌ ERROR Mosaicing: {e}")


if __name__ == "__main__":
    process_wetlands_baselines()
