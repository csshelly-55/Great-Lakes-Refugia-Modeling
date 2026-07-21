"""
================================================================================
THESIS PIPELINE - STEP 1C: GEOSTATISTICAL INTERPOLATION (EBK)
Target: Physical Environmental Baselines
Description:
Converts discrete water quality point data into continuous raster surfaces using
Empirical Bayesian Kriging (EBK).
* METHODOLOGY:
  1. Iterates through the 5 decoupled Great Lakes CSVs.
  2. Isolates Temp, DO, and pH.
  3. Projects to Albers Equal Area for accurate distance mathematics.
  4. Runs EBK with a 1800m cell size, masked strictly to the lake shoreline.
  5. Mosaics the 5 decoupled lakes back into a single Master Binational Raster.
================================================================================
"""

import arcpy
import os
import pandas as pd

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
CLEAN_DIR = os.path.join(PROJECT_DIR, "Data_Clean")
OUT_FOLDER = os.path.join(PROJECT_DIR, "Rasters", "Environmental")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
VARIABLES = ["Temp", "DO", "pH"]

if not os.path.exists(OUT_FOLDER):
    os.makedirs(OUT_FOLDER)

# ArcPy Environments
arcpy.env.workspace = OUT_FOLDER
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_lake_by_lake_rasters():
    print("--- Phase 1c: Generating Decoupled Environmental Rasters ---")

    # The License Fix!
    try:
        arcpy.CheckOutExtension("Spatial")
        arcpy.CheckOutExtension("GeoStats")
        print("✅ Spatial & Geostatistical Analyst Licenses: SECURED")
    except Exception as e:
        print(f"❌ ERROR: Could not check out licenses. {e}")
        return

    for var in VARIABLES:
        print(f"\n🎬 Processing Variable: {var}")
        lake_rasters = []

        # ----------------------------------------------------------------------
        # STEP 2: THE LAKE-BY-LAKE LOOP
        # ----------------------------------------------------------------------
        for lake in LAKES:
            csv_path = os.path.join(CLEAN_DIR, f"{lake}_WQ_Clean.csv")
            lake_shp = os.path.join(
                PROJECT_DIR, rf"Data_Raw\Lake_Boundaries\{lake}\{lake}.shp"
            )

            if not os.path.exists(csv_path) or not arcpy.Exists(lake_shp):
                print(f"  ⚠️ Missing CSV or Shapefile for {lake}. Skipping.")
                continue

            # Load the pre-split CSV and filter for the current variable
            df = pd.read_csv(csv_path, low_memory=False)
            var_df = df[df["Variable"] == var].copy()
            pt_count = len(var_df)

            if pt_count > 10:
                print(f"  🌊 Interpolating {lake}... ({pt_count:,} points)")

                # Write to temp CSV for ArcPy conversion
                temp_csv = os.path.join(CLEAN_DIR, f"temp_{lake}_{var}.csv")
                var_df.to_csv(temp_csv, index=False)

                # Generate spatial points and project to Albers
                pts_wgs = f"memory/pts_wgs_{lake}_{var}"
                pts_albers = f"memory/pts_albers_{lake}_{var}"

                arcpy.management.XYTableToPoint(
                    in_table=temp_csv,
                    out_feature_class=pts_wgs,
                    x_field="LONGITUDE_DD",
                    y_field="LATITUDE_DD",
                    coordinate_system=arcpy.SpatialReference(4326),
                )
                arcpy.management.Project(pts_wgs, pts_albers, usgs_albers)
                os.remove(temp_csv)

                # SET THE MASK: Forces Kriging to perfectly trace the lake shoreline
                arcpy.env.mask = lake_shp
                arcpy.env.extent = lake_shp

                temp_raster = os.path.join(OUT_FOLDER, f"temp_{lake}_{var}.tif")

                try:
                    # Execute EBK
                    arcpy.ga.EmpiricalBayesianKriging(
                        in_features=pts_albers,
                        z_field="ResultMeasureValue",
                        out_raster=temp_raster,
                        cell_size=1800,
                        transformation_type="NONE",
                        semivariogram_model_type="POWER",
                    )
                    lake_rasters.append(temp_raster)
                    print(f"    -> ✅ Success.")
                except Exception as e:
                    print(f"    -> ❌ EBK Failed: {e}")
                finally:
                    # Clear RAM and reset environments
                    arcpy.management.Delete(pts_wgs)
                    arcpy.management.Delete(pts_albers)
                    arcpy.env.mask = None
                    arcpy.env.extent = None
            else:
                print(f"  🌊 Skipping {lake} (Only {pt_count} points for {var}).")

        # ----------------------------------------------------------------------
        # STEP 3: MOSAIC THE BASIN
        # ----------------------------------------------------------------------
        if lake_rasters:
            print(
                f"  🧩 Mosaicing {len(lake_rasters)} lakes into final {var} surface..."
            )

            final_out = f"{var}_Surface_Binational.tif"
            if arcpy.Exists(final_out):
                arcpy.management.Delete(final_out)

            try:
                arcpy.management.MosaicToNewRaster(
                    input_rasters=lake_rasters,
                    output_location=OUT_FOLDER,
                    raster_dataset_name_with_extension=final_out,
                    pixel_type="32_BIT_FLOAT",
                    number_of_bands=1,
                    mosaic_method="MAXIMUM",
                )
                print(f"  🏆 MASTER SAVED: {final_out}")
            except Exception as e:
                print(f"  ❌ ERROR mosaicing {var}: {e}")

            # Clean up the individual temp rasters to save space
            for lr in lake_rasters:
                if arcpy.Exists(lr):
                    arcpy.management.Delete(lr)
        else:
            print(f"  ❌ No valid lake rasters generated for {var}.")

    print("\n==================================================")
    print("🏆 STEP 1C COMPLETE: All Environmental Surfaces Ready.")
    print("==================================================")


if __name__ == "__main__":
    generate_lake_by_lake_rasters()
