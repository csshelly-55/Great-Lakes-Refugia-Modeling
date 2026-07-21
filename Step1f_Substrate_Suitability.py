"""
================================================================================
THESIS PIPELINE - STEP 1F: SUBSTRATE SUITABILITY
Target Species: Walleye & Lake Whitefish
Description:
Reads the GLAHF Great Lakes Substrate Polygon shapefile, evaluates the 'glahf_subs'
field against spawning biology, assigns a 1-10 Suitability Score, and
rasterizes the result for each lake.
* Hard (10), Unknown (5), Sand (3), Mud (1), Clay (1).
* Automatically clones the final output for Lake Whitefish.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
SHP_DIR = os.path.join(DATA_RAW, "Lake_Boundaries")

# Substrate Shapefile
SUBSTRATE_SHP = os.path.join(
    DATA_RAW, "Great_Lakes_Substrate", "Great_Lakes_Substrate_Polygons.shp"
)

# Output Directory
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Suitability")
if not os.path.exists(SUIT_DIR):
    os.makedirs(SUIT_DIR)

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
TARGET_SPECIES = "Walleye"

# ArcPy Environments
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_substrate_suitability():
    print("--- Phase 1f: Substrate Suitability ---")

    if not arcpy.Exists(SUBSTRATE_SHP):
        print(f"  ❌ ERROR: Substrate Shapefile not found at {SUBSTRATE_SHP}")
        return

    try:
        arcpy.CheckOutExtension("Spatial")
        print("  ✅ Spatial Analyst License: SECURED")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    # --------------------------------------------------------------------------
    # STEP 1: PREPARE DATA IN MEMORY (Don't modify the raw data!)
    # --------------------------------------------------------------------------
    print(f"  🪨 Loading Substrate Polygons into memory...")
    mem_shp = r"memory\Substrate_Temp"

    if arcpy.Exists(mem_shp):
        arcpy.management.Delete(mem_shp)

    arcpy.management.CopyFeatures(SUBSTRATE_SHP, mem_shp)

    print("  🧮 Calculating Substrate Suitability Scores (1-10)...")
    arcpy.management.AddField(mem_shp, "SuitScore", "SHORT")

    # Update cursor to assign scores based on the glahf_subs string
    with arcpy.da.UpdateCursor(mem_shp, ["glahf_subs", "SuitScore"]) as cursor:
        for row in cursor:
            sub_type = str(row[0]).lower().strip()

            if sub_type == "hard":
                row[1] = 10
            elif sub_type == "unknown":
                row[1] = 5
            elif sub_type == "sand":
                row[1] = 3
            elif sub_type in ["mud", "clay"]:
                row[1] = 1
            else:
                row[1] = 5  # Catch-all for any weirdly formatted strings

            cursor.updateRow(row)

    lake_suit_rasters = []

    # --------------------------------------------------------------------------
    # STEP 2: RASTERIZE & MASK LAKE-BY-LAKE
    # --------------------------------------------------------------------------
    for lake in LAKES:
        lake_shp = os.path.join(SHP_DIR, lake, f"{lake}.shp")

        if not arcpy.Exists(lake_shp):
            continue

        print(f"\n  🌊 Rasterizing Substrate for {lake}...")

        arcpy.env.mask = lake_shp
        arcpy.env.extent = lake_shp

        temp_suit = os.path.join(SUIT_DIR, f"temp_SubSuit_{lake}.tif")

        try:
            # Convert Polygon to Raster (Using 300m resolution to capture finer shoreline gravel patches)
            arcpy.conversion.PolygonToRaster(
                in_features=mem_shp,
                value_field="SuitScore",
                out_rasterdataset=temp_suit,
                cell_assignment="MAXIMUM_AREA",
                cellsize=300,
            )
            lake_suit_rasters.append(temp_suit)
            print(f"    -> ✅ Substrate rasterized successfully.")

        except Exception as e:
            print(f"    -> ❌ Failed to process {lake}: {e}")

        finally:
            arcpy.env.mask = None
            arcpy.env.extent = None

    # --------------------------------------------------------------------------
    # STEP 3: MOSAIC INTO BINATIONAL SURFACE & CLONE FOR WHITEFISH
    # --------------------------------------------------------------------------
    if len(lake_suit_rasters) > 0:
        print(f"\n  🧩 Mosaicing lakes into final Substrate surface...")

        final_suit_out = os.path.join(
            SUIT_DIR, f"{TARGET_SPECIES}_Substrate_Suitability.tif"
        )

        if arcpy.Exists(final_suit_out):
            arcpy.management.Delete(final_suit_out)

        try:
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_suit_rasters,
                output_location=SUIT_DIR,
                raster_dataset_name_with_extension=f"{TARGET_SPECIES}_Substrate_Suitability.tif",
                coordinate_system_for_the_raster=usgs_albers,
                pixel_type="8_BIT_UNSIGNED",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER SUITABILITY SAVED: {final_suit_out}")

            # --- NEW: Clone for Lake Whitefish ---
            whitefish_out = os.path.join(
                SUIT_DIR, "Lake_Whitefish_Substrate_Suitability.tif"
            )
            if arcpy.Exists(whitefish_out):
                arcpy.management.Delete(whitefish_out)

            print(f"  🧬 Cloning raster for Lake Whitefish...")
            arcpy.management.CopyRaster(final_suit_out, whitefish_out)
            print(f"  🏆 CLONE SAVED: {whitefish_out}")

        except Exception as e:
            print(f"  ❌ ERROR mosaicing or cloning: {e}")

        # Cleanup
        for lr in lake_suit_rasters:
            if arcpy.Exists(lr):
                arcpy.management.Delete(lr)

    if arcpy.Exists(mem_shp):
        arcpy.management.Delete(mem_shp)

    print("\n==================================================")
    print("🏆 STEP 1F COMPLETE: Substrate Suitability Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_substrate_suitability()
