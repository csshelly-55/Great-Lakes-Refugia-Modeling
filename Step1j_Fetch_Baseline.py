"""
================================================================================
THESIS PIPELINE - STEP 1J: WIND EXPOSURE (FETCH)
Targets: Yellow Perch (Spawning Habitat Stability)
Description:
Ingests the high-resolution (30m) Effective Fetch rasters (Mason et al. 2018)
for each individual lake and mosaics them into a single binational surface.
* UPGRADE: Handles mismatched historical year suffixes across the Great Lakes.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]

# Mapping the specific years available in the Mason et al. dataset
fetch_years = {
    "Erie": "2014",
    "Huron": "2012",
    "Michigan": "2014",
    "Ontario": "2014",
    "Superior": "2010",
}

# ArcPy Environments
arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def process_fetch_baselines():
    print("--- Phase 1j: Wind Exposure (Fetch) ---")

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    lake_fetch_rasters = []

    for lake in LAKES:
        year = fetch_years[lake]
        fetch_tif = os.path.join(
            DATA_RAW, "Great_Lakes_Fetch", lake, f"{lake}_fetch_{year}.tif"
        )

        if arcpy.Exists(fetch_tif):
            print(f"  🌬️ Found Fetch raster for {lake} ({year})...")
            lake_fetch_rasters.append(fetch_tif)
        else:
            print(f"  ⚠️ Missing Fetch raster for {lake} at {fetch_tif}")

    # Mosaic them together
    if lake_fetch_rasters:
        print("\n  🧩 Mosaicing Fetch Baselines into Binational Surface...")
        try:
            out_name = "Fetch_Surface_Binational.tif"
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_fetch_rasters,
                output_location=ENV_DIR,
                raster_dataset_name_with_extension=out_name,
                coordinate_system_for_the_raster=usgs_albers,
                pixel_type="32_BIT_FLOAT",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER SAVED: {out_name}")
        except Exception as e:
            print(f"  ❌ ERROR Mosaicing: {e}")
    else:
        print("\n  ❌ No Fetch rasters found to mosaic.")


if __name__ == "__main__":
    process_fetch_baselines()
