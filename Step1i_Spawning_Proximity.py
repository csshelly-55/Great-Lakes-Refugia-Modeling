"""
================================================================================
THESIS PIPELINE - STEP 1G FIX: BASIN-WIDE SPAWNING DISTANCE
Description:
1. Filters the Goodyear Atlas specifically for Lake Whitefish using the 'FISH' column.
2. Merges it with the legacy Erie CSV.
3. Generates a biologically accurate, continuous distance raster.
================================================================================
"""

import arcpy
import pandas as pd
import os

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
ENV_DIR = os.path.join(PROJECT_DIR, "Rasters", "Environmental")

# 🚨 UPDATE THESE TWO NAMES TO MATCH YOUR EXACT CSV FILES IN DATA_RAW 🚨
ERIE_CSV = os.path.join(DATA_RAW, "Historic_Spawning\Whitefish_Historic_Spawning.csv")
GOODYEAR_CSV = os.path.join(
    DATA_RAW, "Historic_Spawning\Great_Lakes_Goodyear_Spawning_Atlas.csv"
)

# 🚨 UPDATED FILTER SETTINGS 🚨
GOODYEAR_SPECIES_COL = "FISH"
GOODYEAR_SPECIES_NAME = "Lake whitefish"

# ArcPy Environments
arcpy.env.workspace = ENV_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
wgs84 = arcpy.SpatialReference(4326)  # GPS Lat/Lon
arcpy.env.outputCoordinateSystem = usgs_albers


def rebuild_spawning_distance():
    print("--- Phase 1g Fix: Rebuilding Basin-Wide Spawning Distance ---")

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    print("  📊 Reading CSVs...")
    df_list = []

    # ---------------------------------------------------------
    # 1. Process the Goodyear Atlas (Requires Filtering)
    # ---------------------------------------------------------
    if os.path.exists(GOODYEAR_CSV):
        try:
            df_gy = pd.read_csv(GOODYEAR_CSV, encoding="utf-8")
        except UnicodeDecodeError:
            df_gy = pd.read_csv(GOODYEAR_CSV, encoding="cp1252")

        print(
            f"    -> Goodyear Atlas loaded: {len(df_gy)} total multi-species records."
        )

        # Ensure the column exists
        if GOODYEAR_SPECIES_COL in df_gy.columns:
            # Filter for Whitefish (case-insensitive)
            df_gy_filtered = df_gy[
                df_gy[GOODYEAR_SPECIES_COL].str.contains(
                    GOODYEAR_SPECIES_NAME, case=False, na=False
                )
            ]
            print(
                f"    -> Filtered down to {len(df_gy_filtered)} '{GOODYEAR_SPECIES_NAME}' records."
            )

            # Find Lat/Lon columns
            lat_col = [
                col
                for col in df_gy_filtered.columns
                if "lat" in col.lower() or col.lower() == "y"
            ][0]
            lon_col = [
                col
                for col in df_gy_filtered.columns
                if "lon" in col.lower() or col.lower() == "x"
            ][0]

            gy_final = df_gy_filtered[[lon_col, lat_col]].copy()
            gy_final.columns = ["Longitude", "Latitude"]
            df_list.append(gy_final)
        else:
            print(
                f"    -> ❌ ERROR: Could not find column '{GOODYEAR_SPECIES_COL}' in Goodyear Atlas."
            )
    else:
        print(f"    -> ⚠️ Missing CSV: {GOODYEAR_CSV}")

    # ---------------------------------------------------------
    # 2. Process the Erie CSV (Already Whitefish only)
    # ---------------------------------------------------------
    if os.path.exists(ERIE_CSV):
        try:
            df_erie = pd.read_csv(ERIE_CSV, encoding="utf-8")
        except UnicodeDecodeError:
            df_erie = pd.read_csv(ERIE_CSV, encoding="cp1252")

        lat_col = [
            col for col in df_erie.columns if "lat" in col.lower() or col.lower() == "y"
        ][0]
        lon_col = [
            col for col in df_erie.columns if "lon" in col.lower() or col.lower() == "x"
        ][0]

        erie_final = df_erie[[lon_col, lat_col]].copy()
        erie_final.columns = ["Longitude", "Latitude"]
        df_list.append(erie_final)
        print(
            f"    -> Loaded {len(erie_final)} records from {os.path.basename(ERIE_CSV)}."
        )
    else:
        print(f"    -> ⚠️ Missing CSV: {ERIE_CSV}")

    # ---------------------------------------------------------
    # 3. Merge and Execute Map Algebra
    # ---------------------------------------------------------
    if not df_list:
        print("  ❌ ERROR: No valid records found to process.")
        return

    master_df = pd.concat(df_list, ignore_index=True).dropna()
    print(
        f"\n  🗺️ Merged a total of {len(master_df)} Whitefish spawning points basin-wide."
    )

    mem_points = r"memory\Master_Spawning_Points"
    arcpy.management.CreateFeatureclass(
        "memory", "Master_Spawning_Points", "POINT", spatial_reference=wgs84
    )
    arcpy.management.AddField(mem_points, "Longitude", "DOUBLE")
    arcpy.management.AddField(mem_points, "Latitude", "DOUBLE")

    print("  📍 Converting coordinates to GIS features...")
    with arcpy.da.InsertCursor(
        mem_points, ["SHAPE@XY", "Longitude", "Latitude"]
    ) as cursor:
        for idx, row in master_df.iterrows():
            cursor.insertRow(
                [(row["Longitude"], row["Latitude"]), row["Longitude"], row["Latitude"]]
            )

    print("  📏 Calculating Basin-Wide Euclidean Distance...")
    basin_mask = os.path.join(ENV_DIR, "Depth_Surface_Binational.tif")
    if arcpy.Exists(basin_mask):
        arcpy.env.mask = basin_mask
        arcpy.env.extent = basin_mask

    mem_points_albers = r"memory\Points_Albers"
    arcpy.management.Project(mem_points, mem_points_albers, usgs_albers)

    out_distance = arcpy.sa.EucDistance(
        mem_points_albers, maximum_distance=1000000, cell_size=1800
    )
    out_path = os.path.join(ENV_DIR, "Spawning_Distance_Binational.tif")
    out_distance.save(out_path)

    print("  🏆 MASTER SAVED: Spawning_Distance_Binational.tif")

    arcpy.management.Delete(mem_points)
    arcpy.management.Delete(mem_points_albers)


if __name__ == "__main__":
    rebuild_spawning_distance()
