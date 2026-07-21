"""
================================================================================
THESIS PIPELINE - STEP 1G: PROXIMITY TO RUNOFF
Target Species: Walleye (10% HSM Weight)
Description:
Isolates high-risk land cover classes (Agriculture & Developed) from NLCD/North
American Land Cover, calculates continuous distance outward into the lakes, and
reclassifies into spatial deterrent suitability scores.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")

# UPDATE THIS TO YOUR EXACT LAND COVER FILE NAME
LAND_COVER_TIF = os.path.join(DATA_RAW, "Land_Cover", "Land_Cover_2023.tif")
SHP_DIR = os.path.join(DATA_RAW, "Lake_Boundaries")

# Outputs
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Suitability")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
TARGET_SPECIES = "Walleye"

# ArcPy Environments
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_runoff_suitability():
    print("--- Phase 1g: Proximity to Runoff (Ag & Urban) ---")

    if not arcpy.Exists(LAND_COVER_TIF):
        print(f"  ❌ ERROR: Land Cover Raster not found at {LAND_COVER_TIF}")
        return

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    print("  🚜 Isolating Agriculture and Developed land classes basin-wide...")

    # 1. Isolate NLCD Developed (21-24) and Agriculture (81-82) classes
    source_remap = arcpy.sa.RemapValue(
        [[21, 1], [22, 1], [23, 1], [24, 1], [81, 1], [82, 1]]
    )

    # We reclassify the whole basin land cover first so EucDistance can broadcast outward
    runoff_sources = arcpy.sa.Reclassify(
        LAND_COVER_TIF, "VALUE", source_remap, "NODATA"
    )

    lake_dist_rasters = []
    lake_suit_rasters = []

    # --------------------------------------------------------------------------
    # STEP 2: CALCULATE DISTANCE & SUITABILITY LAKE-BY-LAKE
    # --------------------------------------------------------------------------
    for lake in LAKES:
        lake_shp = os.path.join(SHP_DIR, lake, f"{lake}.shp")

        if not arcpy.Exists(lake_shp):
            continue

        print(f"\n  📏 Calculating Runoff Proximity for {lake}...")

        # Setting the mask ensures the EucDistance is ONLY saved within the water boundaries
        arcpy.env.mask = lake_shp
        arcpy.env.extent = lake_shp

        temp_dist = os.path.join(ENV_DIR, f"temp_RunoffDist_{lake}.tif")
        temp_suit = os.path.join(SUIT_DIR, f"temp_RunoffSuit_{lake}.tif")

        try:
            # Calculate distance from the Ag/Developed pixels (1800m resolution)
            dist_raster = arcpy.sa.EucDistance(runoff_sources, cell_size=1800)
            dist_raster.save(temp_dist)
            lake_dist_rasters.append(temp_dist)

            # HSM Logic: Inverse distance penalty (Farther is better from runoff)
            # <1km: 1; 1-2km: 3; 2-5km: 6; >5km: 10
            runoff_remap = arcpy.sa.RemapRange(
                [
                    [0, 1000, 1],
                    [1000.01, 2000, 3],
                    [2000.01, 5000, 6],
                    [5000.01, 5000000, 10],
                ]
            )

            suit_raster = arcpy.sa.Reclassify(
                dist_raster, "VALUE", runoff_remap, "NODATA"
            )
            suit_raster.save(temp_suit)
            lake_suit_rasters.append(temp_suit)

            print(
                f"    -> ✅ Extracted Continuous Distance & Reclassified Suitability."
            )

        except Exception as e:
            print(f"    -> ❌ Failed to process {lake}: {e}")

        finally:
            arcpy.env.mask = None
            arcpy.env.extent = None

    # --------------------------------------------------------------------------
    # STEP 3: MOSAIC INTO BINATIONAL SURFACES
    # --------------------------------------------------------------------------
    if len(lake_dist_rasters) > 0 and len(lake_suit_rasters) > 0:
        print(f"\n  🧩 Mosaicing lakes into final Runoff surfaces...")

        final_dist_out = os.path.join(ENV_DIR, "Runoff_Distance_Binational.tif")
        final_suit_out = os.path.join(
            SUIT_DIR, f"{TARGET_SPECIES}_Runoff_Suitability.tif"
        )

        for f in [final_dist_out, final_suit_out]:
            if arcpy.Exists(f):
                arcpy.management.Delete(f)

        try:
            # Mosaic the Distance Raster
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_dist_rasters,
                output_location=ENV_DIR,
                raster_dataset_name_with_extension="Runoff_Distance_Binational.tif",
                coordinate_system_for_the_raster=usgs_albers,
                pixel_type="32_BIT_FLOAT",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER DISTANCE SAVED: {final_dist_out}")

            # Mosaic the Suitability Raster
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_suit_rasters,
                output_location=SUIT_DIR,
                raster_dataset_name_with_extension=f"{TARGET_SPECIES}_Runoff_Suitability.tif",
                coordinate_system_for_the_raster=usgs_albers,
                pixel_type="8_BIT_UNSIGNED",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER SUITABILITY SAVED: {final_suit_out}")
        except Exception as e:
            print(f"  ❌ ERROR mosaicing: {e}")

        # Clean up memory
        for lr in lake_dist_rasters + lake_suit_rasters:
            if arcpy.Exists(lr):
                arcpy.management.Delete(lr)

    print("\n==================================================")
    print("🏆 STEP 1G COMPLETE: Runoff Suitability Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_runoff_suitability()
