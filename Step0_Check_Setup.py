"""
================================================================================
THESIS PIPELINE - STEP 0.0: WORKSPACE SETUP & DIAGNOSTICS
Description:
Initializes the granular, species-specific directory architecture. Verifies ArcPy
licenses and coordinates. Conducts a strict "File Inventory Check" to validate
the existence of all required individual lake boundaries, CSVs, satellite imagery,
and biological data prior to running the harmonization pipeline.
================================================================================
"""

import os
import arcpy

# --- 1. SETTINGS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"

TARGET_SPECIES_LIST = ["Walleye"]
LAKES = ["Erie", "Huron", "Michigan", "Ontario", "Superior"]


def initialize_workspace():
    print("--- STEP 0.0: THESIS WORKSPACE DIAGNOSTICS & SETUP ---")

    # 1. Build the Core Directory Architecture
    folders = [
        "Code",
        r"Data_Raw\CSVs_US",
        r"Data_Raw\CSVs_Canada",
        r"Data_Raw\Satellite",
        "Data_Clean",
        r"Rasters\Environmental",
        r"Rasters\Invasion",
        "Final_Products",
    ]

    # Dynamically generate the Lake_Boundaries folder structure
    for lake in LAKES:
        folders.append(rf"Data_Raw\Lake_Boundaries\{lake}")

    # Dynamically generate Species-Specific folder structures
    for species in TARGET_SPECIES_LIST:
        folders.append(rf"Data_Raw\AIS_Data\{species}")
        folders.append(rf"Data_Raw\Impacts\{species}")
        folders.append(rf"Rasters\Suitability\{species}")

    print("\n📁 Verifying Directory Architecture...")
    for folder in folders:
        full_path = os.path.join(PROJECT_DIR, folder)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            print(f"  -> Created: {folder}")
        else:
            print(f"  -> Exists:  {folder}")

    # 2. Check Spatial Analyst License
    print("\n🔑 Verifying ArcPy Licenses...")
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("  -> ✅ Spatial Analyst License: CHECKED OUT")
    else:
        print("  -> ❌ ERROR: Spatial Analyst License UNAVAILABLE. Pipeline will fail.")

    # 3. Check Coordinate System Access
    print("\n🌍 Verifying Coordinate Systems...")
    try:
        usgs_albers = arcpy.SpatialReference(102039)
        print(f"  -> ✅ Standard Projection Loaded: {usgs_albers.name}")
    except Exception as e:
        print(f"  -> ❌ ERROR loading Spatial Reference: {e}")

    # 4. MASTER FILE INVENTORY CHECK
    print("\n📋 Conducting Master File Inventory Check...")

    missing_files = 0

    # A. Check Lake Boundaries
    print("\n  🗺️ Checking Lake Boundaries:")
    for lake in LAKES:
        shp_path = os.path.join(
            PROJECT_DIR, rf"Data_Raw\Lake_Boundaries\{lake}\{lake}.shp"
        )
        if os.path.exists(shp_path):
            print(f"    -> ✅ {lake}.shp: FOUND")
        else:
            print(f"    -> ❌ {lake}.shp: MISSING")
            missing_files += 1

    # B. Check Physical Water Quality Data
    print("\n  💧 Checking Physical/Chemical CSVs:")
    us_res = os.path.join(PROJECT_DIR, r"Data_Raw\CSVs_US\resultphyschem.csv")
    us_sta = os.path.join(PROJECT_DIR, r"Data_Raw\CSVs_US\station.csv")

    print(
        f"    -> {'✅' if os.path.exists(us_res) else '❌'} US Results (resultphyschem.csv)"
    )
    print(
        f"    -> {'✅' if os.path.exists(us_sta) else '❌'} US Stations (station.csv)"
    )
    if not os.path.exists(us_res):
        missing_files += 1
    if not os.path.exists(us_sta):
        missing_files += 1

    for lake in LAKES:
        ca_wq = os.path.join(PROJECT_DIR, rf"Data_Raw\CSVs_Canada\Lake_{lake}_WQ.csv")
        if os.path.exists(ca_wq):
            print(f"    -> ✅ CA Water Quality (Lake_{lake}_WQ.csv)")
        else:
            # We flag it as a warning since sometimes a lake might not have CA data depending on your pull
            print(
                f"    -> ⚠️ CA Water Quality (Lake_{lake}_WQ.csv): MISSING (Check if expected)"
            )

    # C. Check Satellite Data
    print("\n  🛰️ Checking Satellite Imagery:")
    sat_file = os.path.join(PROJECT_DIR, r"Data_Raw\Satellite\CoastWatch_Kd490.tif")
    if os.path.exists(sat_file):
        print("    -> ✅ NOAA Kd490 GeoTIFF: FOUND")
    else:
        print("    -> ❌ NOAA Kd490 GeoTIFF: MISSING")
        missing_files += 1

    # D. Check Biological Threat Data
    print("\n  🦠 Checking Biological Threat Data:")
    for species in TARGET_SPECIES_LIST:
        glansis = os.path.join(
            PROJECT_DIR, rf"Data_Raw\AIS_Data\{species}\GLANSIS_Full_Export.csv"
        )
        rubric = os.path.join(
            PROJECT_DIR, rf"Data_Raw\Impacts\{species}\{species}_impacts.csv"
        )

        print(
            f"    -> {'✅' if os.path.exists(glansis) else '❌'} {species} GLANSIS Data"
        )
        print(
            f"    -> {'✅' if os.path.exists(rubric) else '❌'} {species} Rubric Data"
        )
        if not os.path.exists(glansis):
            missing_files += 1
        if not os.path.exists(rubric):
            missing_files += 1

    # 5. Final Diagnostic Report
    print("\n==================================================")
    if missing_files == 0:
        print("🎉 ALL SYSTEMS GO! Every raw file is exactly where it belongs.")
        print("   You are cleared to run Step 1a.")
    else:
        print(f"🛑 WARNING: {missing_files} critical files are missing.")
        print(
            "   Please review the ❌ marks above and drop the files into their folders."
        )
    print("==================================================")


if __name__ == "__main__":
    initialize_workspace()
