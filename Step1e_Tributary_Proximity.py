"""
================================================================================
THESIS PIPELINE - STEP 1E: PROXIMITY TO TRIBUTARIES
Target Species: Walleye (20% HSM Weight)
Description:
Calculates the continuous Euclidean distance from Great Lakes rivermouths/tributaries,
masks the distances strictly to the open waters, and immediately reclassifies
them into Walleye Habitat Suitability scores based on potamodromous staging logic.
* UPGRADE: Now explicitly exports and mosaics the intermediate continuous distance
  raster (in meters) for QA/QC and physical baseline visualization.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
SHP_DIR = os.path.join(DATA_RAW, "Lake_Boundaries")

# Tributary Shapefile
TRIBUTARY_SHP = os.path.join(
    DATA_RAW, "Tributaries", "Great_Lakes_Tributaries_Fish_Access.shp"
)

# Outputs
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Suitability")

for folder in [ENV_DIR, SUIT_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
TARGET_SPECIES = "Walleye"

# ArcPy Environments
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_tributary_suitability():
    print("--- Phase 1e: Proximity to Tributaries ---")

    if not arcpy.Exists(TRIBUTARY_SHP):
        print(f"  ❌ ERROR: Tributary Shapefile not found at {TRIBUTARY_SHP}")
        print("     Please update Line 21 with your exact file path!")
        return

    try:
        arcpy.CheckOutExtension("Spatial")
        print("  ✅ Spatial Analyst License: SECURED")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    print(f"  🌊 Ingesting Tributary Shapefile: {os.path.basename(TRIBUTARY_SHP)}")

    # We will track both the raw distances and the suitability scores
    lake_dist_rasters = []
    lake_suit_rasters = []

    # --------------------------------------------------------------------------
    # STEP 1: CALCULATE DISTANCE & SUITABILITY LAKE-BY-LAKE
    # --------------------------------------------------------------------------
    for lake in LAKES:
        lake_shp = os.path.join(SHP_DIR, lake, f"{lake}.shp")

        if not arcpy.Exists(lake_shp):
            print(f"  ⚠️ Missing Lake Boundary for {lake}. Skipping.")
            continue

        print(f"\n  📏 Calculating Tributary Distance for {lake}...")

        # Set the mask so distance perfectly terminates at the shoreline
        arcpy.env.mask = lake_shp
        arcpy.env.extent = lake_shp

        temp_dist = os.path.join(ENV_DIR, f"temp_Dist_{lake}.tif")
        temp_suit = os.path.join(SUIT_DIR, f"temp_Suit_{lake}.tif")

        try:
            # 1. Calculate Continuous Euclidean Distance (1800m resolution)
            dist_raster = arcpy.sa.EucDistance(TRIBUTARY_SHP, cell_size=1800)
            dist_raster.save(temp_dist)
            lake_dist_rasters.append(temp_dist)

            # 2. HSM Logic: Closer is better. <2km: 10; 2-5km: 7; 5-10km: 4; >10km: 2
            trib_remap = arcpy.sa.RemapRange(
                [
                    [0, 2000, 10],
                    [2000.01, 5000, 7],
                    [5000.01, 10000, 4],
                    [10000.01, 5000000, 2],  # Max distance catch-all
                ]
            )

            suit_raster = arcpy.sa.Reclassify(
                dist_raster, "VALUE", trib_remap, "NODATA"
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
    # STEP 2: MOSAIC INTO BINATIONAL SURFACES
    # --------------------------------------------------------------------------
    if len(lake_dist_rasters) > 0 and len(lake_suit_rasters) > 0:
        print(f"\n  🧩 Mosaicing lakes into final surfaces...")

        final_dist_out = os.path.join(ENV_DIR, "Tributary_Distance_Binational.tif")
        final_suit_out = os.path.join(
            SUIT_DIR, f"{TARGET_SPECIES}_Tributary_Suitability.tif"
        )

        for f in [final_dist_out, final_suit_out]:
            if arcpy.Exists(f):
                arcpy.management.Delete(f)

        try:
            # Mosaic the Continuous Distance Raster (32-bit float for precise meters)
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_dist_rasters,
                output_location=ENV_DIR,
                raster_dataset_name_with_extension="Tributary_Distance_Binational.tif",
                pixel_type="32_BIT_FLOAT",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER DISTANCE SAVED: {final_dist_out}")

            # Mosaic the Suitability Raster (8-bit unsigned for whole numbers 1-10)
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_suit_rasters,
                output_location=SUIT_DIR,
                raster_dataset_name_with_extension=f"{TARGET_SPECIES}_Tributary_Suitability.tif",
                pixel_type="8_BIT_UNSIGNED",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER SUITABILITY SAVED: {final_suit_out}")

        except Exception as e:
            print(f"  ❌ ERROR during mosaicing: {e}")

        # Clean up temporary individual lake rasters
        for lr in lake_dist_rasters + lake_suit_rasters:
            if arcpy.Exists(lr):
                arcpy.management.Delete(lr)
    else:
        print("\n  ❌ No valid rasters were generated.")

    print("\n==================================================")
    print("🏆 STEP 1E COMPLETE: Proximity Models Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_tributary_suitability()
