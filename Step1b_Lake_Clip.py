"""
================================================================================
THESIS PIPELINE - STEP 1B: LAKE-BY-LAKE SPATIAL PRUNING
Target Species: Walleye (Physical Baseline)
Description:
Takes the harmonized Master CSV and physically intersects it with the 5 Great
Lakes boundaries.
* METHODOLOGY:
  1. Converts coordinates to GIS points.
  2. Applies a 1km tolerance buffer to the lake shapefiles to retain nearshore points.
  3. Extracts points falling exclusively within each lake.
  4. Exports 5 pristine, lake-specific CSVs ready for Geostatistical kriging.
================================================================================
"""

import os
import pandas as pd
import arcpy

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
CLEAN_DIR = os.path.join(PROJECT_DIR, "Data_Clean")
MASTER_CSV = os.path.join(CLEAN_DIR, "Master_Binational_WQ_Clean.csv")

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]

# ArcPy Environments
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
wgs84 = arcpy.SpatialReference(4326)


def run_lake_split():
    print("--- Phase 1b: Spatial Pruning (Cookie-Cutter Intersect) ---")

    if not os.path.exists(MASTER_CSV):
        print("❌ ERROR: Master CSV not found! Run Step 1a first.")
        return

    # 1. Load data and assign a Unique ID to track points through ArcPy
    print("  -> Loading Master CSV and tracking identifiers...")
    df = pd.read_csv(MASTER_CSV)
    df["TEMP_UID"] = range(len(df))

    temp_csv = os.path.join(CLEAN_DIR, "temp_uid.csv")
    df.to_csv(temp_csv, index=False)

    # 2. Transfer to GIS Memory
    print("  🌍 Transferring 180k+ points into ArcPy Memory (This takes a moment)...")
    master_pts_wgs = "memory/master_pts_wgs"
    master_pts_albers = "memory/master_pts_albers"

    arcpy.management.XYTableToPoint(
        in_table=temp_csv,
        out_feature_class=master_pts_wgs,
        x_field="LONGITUDE_DD",
        y_field="LATITUDE_DD",
        coordinate_system=wgs84,
    )

    arcpy.management.Project(master_pts_wgs, master_pts_albers, usgs_albers)
    os.remove(temp_csv)  # Clean up temp file

    total_retained = 0

    # 3. Loop Through Each Lake Boundary
    for lake in LAKES:
        lake_shp = os.path.join(
            PROJECT_DIR, rf"Data_Raw\Lake_Boundaries\{lake}\{lake}.shp"
        )

        if arcpy.Exists(lake_shp):
            print(f"\n  ✂️ Processing Lake {lake}...")

            # Project Lake to Albers
            lake_shp_albers = f"memory/shp_{lake}_albers"
            arcpy.management.Project(lake_shp, lake_shp_albers, usgs_albers)

            # Create a 1km buffer to capture near-shore samples
            lake_buffer = f"memory/buf_{lake}_albers"
            arcpy.analysis.PairwiseBuffer(lake_shp_albers, lake_buffer, "1 Kilometers")

            # Make a layer from the master points to allow selection
            pts_layer = f"lyr_pts_{lake}"
            arcpy.management.MakeFeatureLayer(master_pts_albers, pts_layer)

            # Select by Location
            arcpy.management.SelectLayerByLocation(
                in_layer=pts_layer,
                overlap_type="INTERSECT",
                select_features=lake_buffer,
            )

            # Read the selected UIDs back out of ArcPy
            valid_uids = [
                row[0] for row in arcpy.da.SearchCursor(pts_layer, "TEMP_UID")
            ]

            # Filter the original Pandas dataframe
            lake_df = df[df["TEMP_UID"].isin(valid_uids)].copy()
            lake_df = lake_df.drop(columns=["TEMP_UID"])  # Clean up the tracking column

            # Save the final Lake-Specific CSV
            out_file = os.path.join(CLEAN_DIR, f"{lake}_WQ_Clean.csv")
            lake_df.to_csv(out_file, index=False)

            retained_count = len(lake_df)
            total_retained += retained_count
            print(
                f"    -> ✅ Captured {retained_count:,} strict nearshore/pelagic points for {lake}."
            )

            # Memory Cleanup
            arcpy.management.Delete(pts_layer)
            arcpy.management.Delete(lake_shp_albers)
            arcpy.management.Delete(lake_buffer)
        else:
            print(f"  ❌ Missing shapefile for {lake}. Expected at: {lake_shp}")

    # 4. Final Readout
    inland_dropped = len(df) - total_retained
    print("\n==================================================")
    print(f"🏆 STEP 1B COMPLETE: Data perfectly decoupled by lake.")
    print(f"   -> Retained Great Lakes Points: {total_retained:,}")
    print(f"   -> Dropped Inland/River Points: {inland_dropped:,}")
    print("==================================================")

    # Final wipe of master memory layer
    arcpy.management.Delete("memory")


if __name__ == "__main__":
    run_lake_split()
