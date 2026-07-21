"""
================================================================================
THESIS PIPELINE - STEP 2B: WEIGHTED SUM SYNTHESIS (MAP ALGEBRA)
================================================================================
"""

import arcpy
import os
import time

# --- 1. SETTINGS & PATHS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
SUIT_DIR = os.path.join(PROJECT_DIR, "Rasters", "Suitability")
FINAL_DIR = os.path.join(PROJECT_DIR, "Rasters", "Final_Models")

if not os.path.exists(FINAL_DIR):
    os.makedirs(FINAL_DIR)

arcpy.env.workspace = SUIT_DIR
arcpy.env.overwriteOutput = True
usgs_albers = arcpy.SpatialReference(102039)
arcpy.env.outputCoordinateSystem = usgs_albers


def generate_final_hsi_models():
    print("--- Phase 2b: Synthesizing Final HSI Models ---")
    try:
        arcpy.CheckOutExtension("Spatial")
    except Exception as e:
        print(f"  ❌ ERROR: Could not check out Spatial Analyst. {e}")
        return

    model_weights = {
        "Walleye": [
            ["Walleye_Temp_Suitability.tif", "VALUE", 0.30],
            ["Walleye_Kd490_Suitability.tif", "VALUE", 0.20],
            ["Walleye_Tributary_Suitability.tif", "VALUE", 0.20],
            ["Walleye_Slope_Suitability.tif", "VALUE", 0.10],
            ["Walleye_Runoff_Suitability.tif", "VALUE", 0.10],
            ["Walleye_DO_Suitability.tif", "VALUE", 0.10],
        ],
        "Yellow_Perch": [
            ["Yellow_Perch_Vegetation_Suitability.tif", "VALUE", 0.35],
            ["Yellow_Perch_Temp_Suitability.tif", "VALUE", 0.25],
            ["Yellow_Perch_Fetch_Suitability.tif", "VALUE", 0.20],
            ["Yellow_Perch_DO_Suitability.tif", "VALUE", 0.10],
            ["Yellow_Perch_Runoff_Suitability.tif", "VALUE", 0.10],
        ],
        "Lake_Whitefish": [
            ["Lake_Whitefish_Temp_Suitability.tif", "VALUE", 0.35],
            ["Lake_Whitefish_DO_Suitability.tif", "VALUE", 0.25],
            ["Lake_Whitefish_Stressor_Suitability.tif", "VALUE", 0.15],
            ["Lake_Whitefish_Spawning_Suitability.tif", "VALUE", 0.10],
            ["Lake_Whitefish_Substrate_Suitability.tif", "VALUE", 0.075],
            ["Lake_Whitefish_Depth_Suitability.tif", "VALUE", 0.075],
        ],
    }

    for species, layers in model_weights.items():
        print(f"\n🧬 SYNTHESIZING MODEL FOR: {species.replace('_', ' ')}...")

        valid_inputs = []
        missing_layers = False

        for raster_name, field, weight in layers:
            raster_path = os.path.join(SUIT_DIR, raster_name)
            if arcpy.Exists(raster_path):
                valid_inputs.append([raster_path, field, weight])
            else:
                print(f"    -> [X] MISSING: {raster_name}")
                missing_layers = True

        if missing_layers:
            print(f"  ❌ Cannot synthesize {species} model. Missing required layers.")
            continue

        try:
            out_name = f"FINAL_HSI_{species}.tif"
            out_path = os.path.join(FINAL_DIR, out_name)

            # SAFE OVERWRITE: Try to delete the old file first to release locks
            if arcpy.Exists(out_path):
                try:
                    arcpy.management.Delete(out_path)
                except:
                    # If delete fails, try to rename it to a 'trash' name so we can save the new one
                    trash_path = os.path.join(
                        FINAL_DIR, f"trash_{int(time.time())}_{out_name}"
                    )
                    arcpy.management.Rename(out_path, trash_path)

            ws_object = arcpy.sa.WSTable(valid_inputs)
            final_hsi = arcpy.sa.WeightedSum(ws_object)
            final_hsi.save(out_path)
            print(f"  🏆 MASTER MODEL SAVED: {out_name}")

        except Exception as e:
            print(f"  ❌ ERROR calculating Weighted Sum for {species}: {e}")

    print("\n==================================================")
    print("🏆 PHASE 2B COMPLETE: All Final Thesis Maps Generated.")
    print("==================================================")


if __name__ == "__main__":
    generate_final_hsi_models()
