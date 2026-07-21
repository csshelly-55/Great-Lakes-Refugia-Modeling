"""
================================================================================
THESIS PIPELINE - STEP 3A: AIS SPATIAL THINNING & LAKE-BY-LAKE SPLIT (MULTI-SPECIES)
Targets: Walleye, Yellow Perch, Lake Whitefish
Description:
* METHODOLOGY UPDATE: Variables for Buffer Distance and Thinning Distance
  moved to global settings for easy adjustment.
================================================================================
"""

import os
import pandas as pd
import arcpy
import warnings

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# --- SETTINGS ---
SPORT_FISH = {
    "Walleye": "Final_Species_List_Walleye.csv",
    "Yellow_Perch": "Final_Species_List_Perch.csv",
    "Lake_Whitefish": "Final_Species_List_Whitefish.csv",
}

MIN_POINTS_PER_LAKE = 3

# 🔥 NEW ADJUSTABLE SPATIAL RULES 🔥
BUFFER_DISTANCE = (
    "15 Kilometers"  # Increased from 2km to catch deeper coastal/tributary points
)
THINNING_DISTANCE = "250 Meters"  # Points within this distance are merged into 1

PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
BASE_DIR = os.path.join(PROJECT_DIR, "Code")
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
AIS_DIR = os.path.join(DATA_RAW, "AIS_Data")
GLANSIS_RAW = os.path.join(DATA_RAW, "GLANSIS_Full_Export.csv")
LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

os.chdir(BASE_DIR)
arcpy.env.overwriteOutput = True
wgs84 = arcpy.SpatialReference(4326)
usgs_albers = arcpy.SpatialReference(102039)


def run_multi_species_thinning():
    print(f"--- Phase 3a: Lake-by-Lake Spatial Thinning & CSV Extraction ---")

    print("\n -> Loading and Pre-Filtering GLANSIS Data...")
    glansis_df = pd.read_csv(GLANSIS_RAW, low_memory=False)

    sci_col = next(
        (
            c
            for c in ["ScientificName", "Scientific Name", "scientific_name", "Species"]
            if c in glansis_df.columns
        ),
        None,
    )
    lat_col = next(
        (
            c
            for c in ["Latitude", "decimalLatitude", "Lat", "LATITUDE"]
            if c in glansis_df.columns
        ),
        None,
    )
    lon_col = next(
        (
            c
            for c in ["Longitude", "decimalLongitude", "Lon", "LONGITUDE"]
            if c in glansis_df.columns
        ),
        None,
    )

    glansis_df[lat_col] = pd.to_numeric(glansis_df[lat_col], errors="coerce")
    glansis_df[lon_col] = pd.to_numeric(glansis_df[lon_col], errors="coerce")
    glansis_df = glansis_df.dropna(subset=[lat_col, lon_col])

    # Bounding Box Pre-Filter
    glansis_df = glansis_df[
        (glansis_df[lat_col] >= 41.0)
        & (glansis_df[lat_col] <= 49.5)
        & (glansis_df[lon_col] >= -93.0)
        & (glansis_df[lon_col] <= -75.0)
    ].copy()

    # 2. Iterate through each Sport Fish
    for target, csv_filename in SPORT_FISH.items():
        print(f"\n============================================================")
        print(f"🐟 PROCESSING AIS THREATS FOR: {target.replace('_', ' ')}")
        print(f"============================================================")

        SHP_DIR = os.path.join(PROJECT_DIR, "Shapefiles", target)
        if not os.path.exists(SHP_DIR):
            os.makedirs(SHP_DIR)

        CSV_DIR = os.path.join(DATA_RAW, "Processed_AIS_CSVs", target)
        if not os.path.exists(CSV_DIR):
            os.makedirs(CSV_DIR)

        arcpy.env.workspace = SHP_DIR

        SPECIES_LIST = os.path.join(AIS_DIR, csv_filename)
        if not os.path.exists(SPECIES_LIST):
            print(f"  ❌ ERROR: Could not find {csv_filename} at {SPECIES_LIST}")
            continue

        try:
            ais_list_df = pd.read_csv(SPECIES_LIST)
            target_ais = ais_list_df["Scientific Name"].dropna().unique()
        except Exception as e:
            print(f"  ❌ Error loading species list for {target}: {e}")
            continue

        # 3. Lake-by-Lake Processing Loop
        for lake in LAKES:
            lake_shp = os.path.join(DATA_RAW, "Lake_Boundaries", lake, f"{lake}.shp")

            if not arcpy.Exists(lake_shp):
                print(f"  ⚠️ Missing {lake} shapefile at {lake_shp}. Skipping...")
                continue

            print(f"\n  🌊 {lake.upper()} INVASIONS")

            lake_qualifying_fcs = []
            pts_saved = 0

            lake_shp_albers = f"memory/shp_{lake}_albers"
            arcpy.management.Project(lake_shp, lake_shp_albers, usgs_albers)
            lake_buffer = f"memory/buf_{lake}_albers"

            # 🔥 Applies the variable buffer distance
            arcpy.analysis.PairwiseBuffer(lake_shp_albers, lake_buffer, BUFFER_DISTANCE)

            for ais in target_ais:
                safe_name = (
                    str(ais)
                    .replace(" ", "_")
                    .replace("(", "")
                    .replace(")", "")
                    .replace(".", "")
                    .replace("-", "_")
                )
                ais_data = glansis_df[glansis_df[sci_col] == ais].copy()

                if ais_data.empty:
                    continue

                temp_csv = os.path.join(BASE_DIR, f"temp_{safe_name}.csv")
                ais_data.to_csv(temp_csv, index=False)

                try:
                    pts = "memory/pts_layer"
                    if arcpy.Exists(pts):
                        arcpy.management.Delete(pts)
                    arcpy.management.XYTableToPoint(
                        temp_csv, pts, lon_col, lat_col, "", wgs84
                    )

                    pts_albers = "memory/pts_albers"
                    if arcpy.Exists(pts_albers):
                        arcpy.management.Delete(pts_albers)
                    arcpy.management.Project(pts, pts_albers, usgs_albers)

                    arcpy.management.MakeFeatureLayer(pts_albers, "lyr_pts")
                    arcpy.management.SelectLayerByLocation(
                        in_layer="lyr_pts",
                        overlap_type="INTERSECT",
                        select_features=lake_buffer,
                    )

                    if int(arcpy.management.GetCount("lyr_pts")[0]) == 0:
                        arcpy.management.Delete("lyr_pts")
                        continue

                    lake_species_fc = os.path.join(SHP_DIR, f"{lake}_{safe_name}.shp")
                    arcpy.management.CopyFeatures("lyr_pts", lake_species_fc)
                    arcpy.management.Delete("lyr_pts")

                    # 🔥 Applies the variable thinning distance
                    arcpy.management.DeleteIdentical(
                        lake_species_fc, ["Shape"], THINNING_DISTANCE
                    )

                    final_count = int(arcpy.management.GetCount(lake_species_fc)[0])

                    if final_count >= MIN_POINTS_PER_LAKE:
                        print(f"    ✅ {ais} qualifies ({final_count} points)")
                        lake_qualifying_fcs.append(lake_species_fc)
                        pts_saved += final_count
                    else:
                        print(
                            f"    ⏭️ {ais} dropped (Only {final_count} points after thinning)"
                        )
                        arcpy.management.Delete(lake_species_fc)

                except Exception as e:
                    print(f"    ❌ Error processing {ais}: {e}")
                finally:
                    if os.path.exists(temp_csv):
                        os.remove(temp_csv)

            arcpy.management.Delete(lake_shp_albers)
            arcpy.management.Delete(lake_buffer)

            # 4. Merge Qualifying Shapefiles & Export to CSV
            if lake_qualifying_fcs:
                out_merged = os.path.join(SHP_DIR, f"{lake}_Qualifying_AIS_Merged.shp")
                arcpy.management.Merge(lake_qualifying_fcs, out_merged)

                out_csv = os.path.join(CSV_DIR, f"{lake}_Thinned_AIS_Data.csv")

                temp_wgs_merge = "memory/wgs_merge"
                arcpy.management.Project(out_merged, temp_wgs_merge, wgs84)

                arcpy.management.AddGeometryAttributes(temp_wgs_merge, "POINT_X_Y_Z_M")
                arcpy.conversion.TableToTable(
                    temp_wgs_merge, CSV_DIR, f"{lake}_Thinned_AIS_Data.csv"
                )
                arcpy.management.Delete(temp_wgs_merge)

                print(f"    -> 💾 Shapefile Saved: {os.path.basename(out_merged)}")
                print(
                    f"    -> 📊 CSV Extracted: {os.path.basename(out_csv)} (Total valid points: {pts_saved})"
                )

                for fc in lake_qualifying_fcs:
                    if arcpy.Exists(fc):
                        arcpy.management.Delete(fc)
            else:
                print(
                    f"    ❌ No species met the N={MIN_POINTS_PER_LAKE} threshold in {lake}."
                )

    print(
        f"\n--- PHASE 3A COMPLETE: All targets processed. Ready for Kernel Density! ---"
    )


if __name__ == "__main__":
    run_multi_species_thinning()
