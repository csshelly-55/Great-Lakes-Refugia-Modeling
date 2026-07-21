"""
================================================================================
THESIS PIPELINE - STEP 3B: INDIVIDUAL SPECIES KDE (SEVERE IMPACTORS ONLY)
Targets: Walleye, Yellow Perch, Lake Whitefish
Description:
* METHODOLOGY UPDATE: Re-enabled the deep Filter Diagnostics block so we can
  see exactly why valid species are being dropped during dictionary cross-referencing.
================================================================================
"""

import arcpy
import os
import pandas as pd
import glob

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
SHP_DIR_BASE = os.path.join(PROJECT_DIR, "Shapefiles")
KDE_DIR_BASE = os.path.join(PROJECT_DIR, "Rasters", "AIS_KDE")
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
AIS_DIR = os.path.join(DATA_RAW, "AIS_Data")
IMPACTS_DIR = os.path.join(DATA_RAW, "Impacts")

SPORT_FISH = {
    "Walleye": "Final_Species_List_Walleye.csv",
    "Yellow_Perch": "Final_Species_List_Perch.csv",
    "Lake_Whitefish": "Final_Species_List_Whitefish.csv",
}

IMPACT_FILES = {
    "Walleye": "Scored_Impact_Data_Walleye.csv",
    "Yellow_Perch": "Scored_Impact_Data_Perch.csv",
    "Lake_Whitefish": "Scored_Impact_Data_Whitefish.csv",
}

LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]
SEARCH_RADIUS = 20000
CELL_SIZE = 1800

arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def run_diagnostic_kde():
    print("--- Phase 3b: Diagnostic Impact-Filtered KDE (Severe Impactors) ---")

    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    for target, csv_filename in SPORT_FISH.items():
        print(f"\n============================================================")
        print(f"🔥 GENERATING FILTERED HEATMAPS FOR: {target.replace('_', ' ')}")
        print(f"============================================================")

        in_shp_dir = os.path.join(SHP_DIR_BASE, target)
        out_kde_dir = os.path.join(KDE_DIR_BASE, target)

        if not os.path.exists(out_kde_dir):
            os.makedirs(out_kde_dir)

        # 🧹 CLEANUP
        old_files = glob.glob(os.path.join(out_kde_dir, "*AIS_Pressure*.tif"))
        for old_file in old_files:
            try:
                os.remove(old_file)
            except:
                pass

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
            sci_col_impact = next(
                (
                    c
                    for c in impact_df.columns
                    if "scientific" in c.lower() or "species" in c.lower()
                ),
                None,
            )

            if not score_col or not sci_col_impact:
                print(f"  ❌ ERROR: Columns missing. Found: {list(impact_df.columns)}")
                continue

            impact_df[score_col] = pd.to_numeric(impact_df[score_col], errors="coerce")
        except Exception as e:
            print(f"  ❌ ERROR reading {IMPACT_FILES[target]}: {e}")
            continue

        # --- 2. FILTER THE QUALIFYING GLANSIS LIST ---
        SPECIES_LIST = os.path.join(AIS_DIR, csv_filename)
        approved_target_ais = []

        if os.path.exists(SPECIES_LIST):
            try:
                ais_list_df = pd.read_csv(SPECIES_LIST)
                sci_col_csv = next(
                    (
                        c
                        for c in ais_list_df.columns
                        if "scientific" in c.lower() or "species" in c.lower()
                    ),
                    "Scientific Name",
                )
                base_ais_list = ais_list_df[sci_col_csv].dropna().unique()

                print("\n  🔎 --- FILTER DIAGNOSTICS ---")
                for ais in base_ais_list:
                    ais_clean = str(ais).strip()

                    if target == "Walleye" and "Faxonius rusticus" in ais_clean:
                        approved_target_ais.append(ais_clean)
                        print(f"    -> 🟢 APPROVED (VIP Exception): {ais_clean}")
                        continue

                    match = impact_df[
                        impact_df[sci_col_impact]
                        .astype(str)
                        .str.contains(ais_clean, case=False, na=False, regex=False)
                    ]
                    if not match.empty:
                        score = match.iloc[0][score_col]
                        if pd.notna(score):
                            if score <= -10:
                                approved_target_ais.append(ais_clean)
                                print(
                                    f"    -> 🟢 APPROVED: {ais_clean} (Score: {score})"
                                )
                            else:
                                print(
                                    f"    -> 🔴 REJECTED: {ais_clean} (Score: {score} is not <= -10)"
                                )
                        else:
                            print(
                                f"    -> 🔴 REJECTED: {ais_clean} (Score parsed as blank or NaN)"
                            )
                    else:
                        print(f"    -> ❓ NOT FOUND IN DICTIONARY: '{ais_clean}'")
                print("  -----------------------------")

                print(
                    f"  ✅ {len(approved_target_ais)} species passed the severe dictionary filter."
                )
            except Exception as e:
                print(f"  ❌ Error filtering target list: {e}")
                continue
        else:
            print(f"  ❌ ERROR: Missing observation list {csv_filename}.")
            continue

        # --- 3. PROCESS THE LAKES & RUN KDE ---
        for lake in LAKES:
            in_shp = os.path.join(in_shp_dir, f"{lake}_Qualifying_AIS_Merged.shp")
            lake_shp = os.path.join(DATA_RAW, "Lake_Boundaries", lake, f"{lake}.shp")

            if not arcpy.Exists(in_shp):
                continue

            print(f"\n  📍 Processing Lake {lake}...")

            temp_pts = f"memory/pts_{target}_{lake}"
            arcpy.management.Project(in_shp, temp_pts, usgs_albers)

            if arcpy.Exists(lake_shp):
                temp_mask = f"memory/mask_{target}_{lake}"
                arcpy.management.Project(lake_shp, temp_mask, usgs_albers)
                arcpy.env.mask = temp_mask
                arcpy.env.extent = temp_mask

            text_fields = [
                f.name for f in arcpy.ListFields(temp_pts) if f.type == "String"
            ]
            sci_col_shp = next(
                (
                    f
                    for f in text_fields
                    if any(sub in f.lower() for sub in ["sci", "spec", "name", "fish"])
                    and "id" not in f.lower()
                ),
                None,
            )

            unique_species = set(
                [row[0] for row in arcpy.da.SearchCursor(temp_pts, [sci_col_shp])]
            )

            lyr_name = f"lyr_{lake}"
            arcpy.management.MakeFeatureLayer(temp_pts, lyr_name)

            for species in unique_species:
                if not species:
                    continue

                species_clean = str(species).strip()
                if species_clean not in approved_target_ais:
                    continue

                safe_name = (
                    species_clean.replace(" ", "_")
                    .replace("(", "")
                    .replace(")", "")
                    .replace(".", "")
                )
                query = f"\"{sci_col_shp}\" = '{species}'"
                arcpy.management.SelectLayerByAttribute(
                    lyr_name, "NEW_SELECTION", query
                )

                count = int(arcpy.management.GetCount(lyr_name).getOutput(0))

                if count == 0:
                    print(
                        f"    -> ⚠️ Skipped KDE: 0 points found for {species_clean} inside the {lake} mask."
                    )
                    continue

                out_name = f"{lake}_{safe_name}_KDE_{int(SEARCH_RADIUS / 1000)}km.tif"
                out_path = os.path.join(out_kde_dir, out_name)

                try:
                    kde_raster = arcpy.sa.KernelDensity(
                        in_features=lyr_name,
                        population_field="NONE",
                        cell_size=CELL_SIZE,
                        search_radius=SEARCH_RADIUS,
                        area_unit_scale_factor="SQUARE_KILOMETERS",
                    )

                    kde_raster.save(out_path)
                    print(
                        f"    -> ✅ Saved KDE: {out_name} (Calculated using {count} points)"
                    )

                except Exception as e:
                    print(f"    -> ❌ Error generating KDE for {species_clean}: {e}")

            arcpy.management.Delete(lyr_name)

            arcpy.env.mask = None
            arcpy.env.extent = None

            if arcpy.Exists(temp_mask):
                arcpy.management.Delete(temp_mask)
            if arcpy.Exists(temp_pts):
                arcpy.management.Delete(temp_pts)

    print("\n==================================================")
    print("🏆 PHASE 3B COMPLETE: Filtered Species Heatmaps Generated.")
    print("==================================================")


if __name__ == "__main__":
    run_diagnostic_kde()
