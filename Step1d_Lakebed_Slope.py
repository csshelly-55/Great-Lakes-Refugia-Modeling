"""
================================================================================
THESIS PIPELINE - STEP 1D: GEOMORPHOLOGY (LAKEBED SLOPE)
Target Species: Walleye (10% HSM Weight)
Description:
Ingests individual lake bathymetry DEMs, calculates the topographic gradient
(Slope in Degrees), clips them precisely to the shoreline mask, and mosaics
them into a single binational physical surface.
================================================================================
"""

import arcpy
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
SHP_DIR = os.path.join(DATA_RAW, "Lake_Boundaries")
OUT_FOLDER = os.path.join(PROJECT_DIR, "Rasters", "Environmental")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]

if not os.path.exists(OUT_FOLDER):
    os.makedirs(OUT_FOLDER)

# ArcPy Environments
arcpy.env.workspace = OUT_FOLDER
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_slope_surfaces():
    print("--- Phase 1d: Generating Lakebed Topography (Slope) ---")

    try:
        arcpy.CheckOutExtension("Spatial")
        print("  ✅ Spatial Analyst License: SECURED")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    lake_slope_rasters = []

    # --------------------------------------------------------------------------
    # STEP 1: CALCULATE SLOPE LAKE-BY-LAKE
    # --------------------------------------------------------------------------
    for lake in LAKES:
        # Navigate into the specific bathymetry folder (e.g., Erie_Bathymetry/erie_lld.tif)
        bathy_folder = os.path.join(DATA_RAW, f"{lake}_Bathymetry")
        bathy_name = f"{lake.lower()}_lld.tif"
        bathy_tif = os.path.join(bathy_folder, bathy_name)

        # Matches standard shapefile structure established in earlier steps
        lake_shp = os.path.join(SHP_DIR, lake, f"{lake}.shp")

        if not arcpy.Exists(bathy_tif):
            print(
                f"  ⚠️ Missing Bathymetry for {lake}. Expected: {bathy_tif}. Skipping."
            )
            continue

        print(f"\n  🌊 Processing Geomorphology for {lake}...")

        # Set the mask so the slope raster perfectly matches the Temp/DO boundaries
        if arcpy.Exists(lake_shp):
            arcpy.env.mask = lake_shp
            arcpy.env.extent = lake_shp
        else:
            print(f"    -> Warning: No shapefile mask found for {lake} at {lake_shp}.")

        out_slope_path = os.path.join(OUT_FOLDER, f"temp_Slope_{lake}.tif")

        try:
            # Calculate Slope (in Degrees)
            slope_raster = arcpy.sa.Slope(
                in_raster=bathy_tif,
                output_measurement="DEGREE",
                z_factor=1,
                method="PLANAR",
            )
            slope_raster.save(out_slope_path)
            lake_slope_rasters.append(out_slope_path)
            print(f"    -> ✅ Slope successfully calculated.")

        except Exception as e:
            print(f"    -> ❌ Failed to calculate slope for {lake}: {e}")

        finally:
            arcpy.env.mask = None
            arcpy.env.extent = None

    # --------------------------------------------------------------------------
    # STEP 2: MOSAIC INTO BINATIONAL SURFACE
    # --------------------------------------------------------------------------
    if len(lake_slope_rasters) > 0:
        print(
            f"\n  🧩 Mosaicing {len(lake_slope_rasters)} lakes into final Slope surface..."
        )
        final_slope_out = "Slope_Surface_Binational.tif"

        if arcpy.Exists(final_slope_out):
            arcpy.management.Delete(final_slope_out)

        try:
            arcpy.management.MosaicToNewRaster(
                input_rasters=lake_slope_rasters,
                output_location=OUT_FOLDER,
                raster_dataset_name_with_extension=final_slope_out,
                pixel_type="32_BIT_FLOAT",
                number_of_bands=1,
                mosaic_method="MAXIMUM",
            )
            print(f"  🏆 MASTER SAVED: {final_slope_out}")
        except Exception as e:
            print(f"  ❌ ERROR mosaicing Slope: {e}")

        # Clean up temporary individual lake rasters to save hard drive space
        for lr in lake_slope_rasters:
            if arcpy.Exists(lr):
                arcpy.management.Delete(lr)
    else:
        print(
            "\n  ❌ No valid slope rasters were generated. Check your Data_Raw folder."
        )

    print("\n==================================================")
    print("🏆 STEP 1D COMPLETE: Geomorphology Surfaces Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_slope_surfaces()
