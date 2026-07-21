"""
================================================================================
THESIS PIPELINE - STEP 3C: WEIGHTED CUMULATIVE IMPACT & MOSAICKING
Targets: Walleye, Yellow Perch, Lake Whitefish
Description:
* METHODOLOGY UPDATE: Added Threat Inversion. Multiplies raw impact scores
  by -1 so severe invaders result in intuitively high positive Threat Scores.
================================================================================
"""

import arcpy
import os
import pandas as pd

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
KDE_DIR_BASE = os.path.join(PROJECT_DIR, "Rasters", "AIS_KDE")
IMPACTS_DIR = os.path.join(PROJECT_DIR, "Data_Raw", "Impacts")
FINAL_IMPACT_DIR = os.path.join(PROJECT_DIR, "Rasters", "AIS_Cumulative_Impact")
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")

SPORT_FISH = ["Walleye", "Yellow_Perch", "Lake_Whitefish"]
LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]

IMPACT_FILES = {
    "Walleye": "Scored_Impact_Data_Walleye.csv",
    "Yellow_Perch": "Scored_Impact_Data_Perch.csv",
    "Lake_Whitefish": "Scored_Impact_Data_Whitefish.csv",
}

CELL_SIZE = 1800

if not os.path.exists(FINAL_IMPACT_DIR):
    os.makedirs(FINAL_IMPACT_DIR)

arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def run_cumulative_impact_mosaicking():
    print("--- Phase 3c: Weighted Cumulative Impact (Threat Inverted) ---")

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    for target in SPORT_FISH:
        print(f"\n============================================================")
        print(f"🗺️ SYNTHESIZING CUMULATIVE THREAT FOR: {target.replace('_', ' ')}")
        print(f"============================================================")

        in_kde_dir = os.path.join(KDE_DIR_BASE, target)
        out_target_dir = os.path.join(FINAL_IMPACT_DIR, target)

        if not os.path.exists(in_kde_dir):
            print(f"  ❌ ERROR: The folder {in_kde_dir} does not exist!")
            continue

        if not os.path.exists(out_target_dir):
            os.makedirs(out_target_dir)

        arcpy.env.workspace = in_kde_dir

        # --- 1. LOAD TARGET'S SPECIFIC IMPACT DICTIONARY ---
        impact_csv_path = os.path.join(IMPACTS_DIR, IMPACT_FILES[target])
        if not os.path.exists(impact_csv_path):
            print(
                f"  ❌ ERROR: Cannot find Impact data at {impact_csv_path}. Skipping."
            )
            continue

        try:
            impact_df = pd.read_csv(impact_csv_path)
            score_col = next(
                (
                    c
                    for c in impact_df.columns
                    if "score" in c.lower() or "impact" in c.lower()
                ),
                None,
            )
            sci_col = next(
                (
                    c
                    for c in impact_df.columns
                    if "scientific" in c.lower() or "species" in c.lower()
                ),
                None,
            )

            impact_df["safe_name"] = (
                impact_df[sci_col]
                .astype(str)
                .str.replace(" ", "_")
                .str.replace("(", "")
                .str.replace(")", "")
                .str.replace(".", "")
            )
            impact_df[score_col] = pd.to_numeric(impact_df[score_col], errors="coerce")
        except Exception as e:
            print(f"  ❌ ERROR reading dictionary: {e}")
            continue

        lake_mosaics = []

        # --- 2. CALCULATE CUMULATIVE THREAT PER LAKE ---
        for lake in LAKES:
            print(f"\n  🌊 Stacking and Weighting Lake {lake}...")

            lake_rasters = arcpy.ListRasters(f"{lake}_*.tif")
            weighted_rasters_to_sum = []

            if lake_rasters:
                for raster_name in lake_rasters:
                    raster_path = os.path.join(in_kde_dir, raster_name)

                    species_safe_name = raster_name.replace(f"{lake}_", "").split(
                        "_KDE_"
                    )[0]

                    match = impact_df[impact_df["safe_name"] == species_safe_name]
                    if not match.empty:
                        score = match.iloc[0][score_col]
                        if pd.notna(score):
                            # 🔥 THE THREAT INVERSION 🔥
                            # Multiplies the score by -1 to turn negative impacts into positive threats
                            threat_weight = float(score) * -1

                            weighted = arcpy.sa.Raster(raster_path) * threat_weight
                            weighted_rasters_to_sum.append(weighted)
                            print(
                                f"    -> 🧮 Converted Impact ({score}) to Threat Weight (+{threat_weight}) for {species_safe_name}"
                            )
                    else:
                        print(
                            f"    -> ⚠️ WARNING: {species_safe_name} not found in dictionary."
                        )

            # 🛑 ZERO-PATCHING SAFETY NET 🛑
            if not weighted_rasters_to_sum:
                print(
                    f"    -> ⚠️ No impact rasters. Generating a ZERO pressure baseline for {lake}."
                )
                lake_shp = os.path.join(
                    DATA_RAW, "Lake_Boundaries", lake, f"{lake}.shp"
                )

                if arcpy.Exists(lake_shp):
                    lake_out_path = os.path.join(
                        out_target_dir, f"{lake}_Cumulative_Impact.tif"
                    )
                    temp_shp = f"memory/{lake}_proj"
                    arcpy.management.Project(lake_shp, temp_shp, usgs_albers)

                    arcpy.management.AddField(temp_shp, "ZeroVal", "SHORT")
                    arcpy.management.CalculateField(temp_shp, "ZeroVal", "0")

                    arcpy.env.extent = temp_shp
                    arcpy.env.mask = temp_shp

                    arcpy.conversion.PolygonToRaster(
                        in_features=temp_shp,
                        value_field="ZeroVal",
                        out_rasterdataset=lake_out_path,
                        cell_assignment="MAXIMUM_AREA",
                        cellsize=CELL_SIZE,
                    )

                    lake_mosaics.append(lake_out_path)
                    print(
                        f"    -> ✅ Successfully patched {lake} with baseline 0 impact."
                    )

                    arcpy.management.Delete(temp_shp)
                    arcpy.env.extent = None
                    arcpy.env.mask = None
                else:
                    print(f"    -> ❌ Cannot patch: Missing shapefile {lake_shp}")

            else:
                try:
                    lake_cumulative = arcpy.sa.CellStatistics(
                        weighted_rasters_to_sum, "SUM", "DATA"
                    )
                    lake_out_path = os.path.join(
                        out_target_dir, f"{lake}_Cumulative_Impact.tif"
                    )
                    lake_cumulative.save(lake_out_path)

                    lake_mosaics.append(lake_out_path)
                    print(f"    -> ✅ Successfully generated {lake} Cumulative Threat")
                except Exception as e:
                    print(
                        f"    -> ❌ Error calculating cumulative statistics for {lake}: {e}"
                    )

        # --- 3. MOSAIC THE LAKES INTO A BASIN-WIDE LAYER ---
        if lake_mosaics:
            print(
                f"\n  🧩 Mosaicking {len(lake_mosaics)} lakes into Basin-Wide layer..."
            )

            basin_out_name = f"Basin_Wide_AIS_Impact_{target}.tif"

            try:
                arcpy.env.extent = None
                arcpy.env.mask = None

                arcpy.management.MosaicToNewRaster(
                    input_rasters=lake_mosaics,
                    output_location=out_target_dir,
                    raster_dataset_name_with_extension=basin_out_name,
                    coordinate_system_for_the_raster=usgs_albers,
                    pixel_type="32_BIT_FLOAT",
                    cellsize=CELL_SIZE,
                    number_of_bands=1,
                    mosaic_method="MAXIMUM",
                    mosaic_colormap_mode="FIRST",
                )
                print(f"  🏆 MASTER SAVED: {basin_out_name} completed!")
            except Exception as e:
                print(f"  ❌ Error mosaicking basin for {target}: {e}")

    print("\n==================================================")
    print("🏆 PHASE 3C COMPLETE: Basin-Wide Threat Maps are ready.")
    print("==================================================")


if __name__ == "__main__":
    run_cumulative_impact_mosaicking()
