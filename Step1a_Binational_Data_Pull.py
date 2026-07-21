"""
================================================================================
THESIS PIPELINE - STEP 1A: BINATIONAL DATA HARMONIZATION & QA/QC
Target Species: Walleye (Physical Baseline)
Description:
Synthesizes U.S. (WQP), Canadian (ECCC), and EPA GLENDA databases.
* RESTORED: EPA GLENDA data ingestion to solve offshore data sparsity in Huron.
* UPGRADE: Features a dynamic "Omni-Parser" that can seamlessly ingest both
  Wide-Format (Lab Chemistry) and Long-Format (CTD Sensor Profile) EPA files.
* PATCH: Resolves Pandas mixed-format Date collision by pre-parsing GLENDA dates.
================================================================================
"""

import pandas as pd
import os
import warnings

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# --- 1. SETTINGS & DIRECTORY TREE ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
DATA_RAW = os.path.join(PROJECT_DIR, "Data_Raw")
CLEAN_DIR = os.path.join(PROJECT_DIR, "Data_Clean")

US_DIR = os.path.join(DATA_RAW, "CSVs_US")
CA_DIR = os.path.join(DATA_RAW, "CSVs_Canada")
GLENDA_DIR = os.path.join(DATA_RAW, "GLENDA")

OUT_FILE = os.path.join(CLEAN_DIR, "Master_Binational_WQ_Clean.csv")


def run_binational_pull():
    print("--- Phase 1a: Standardizing & Cleaning Mixed-Unit Binational Data ---")
    full_df = pd.DataFrame()

    # --------------------------------------------------------------------------
    # STEP 2: PROCESS U.S. DATA (WQP)
    # --------------------------------------------------------------------------
    us_res_file = os.path.join(US_DIR, "resultphyschem.csv")
    us_sta_file = os.path.join(US_DIR, "station.csv")

    if os.path.exists(us_res_file) and os.path.exists(us_sta_file):
        print("  -> Loading U.S. WQP Data...")
        res_cols = [
            "MonitoringLocationIdentifier",
            "ActivityStartDate",
            "CharacteristicName",
            "ResultMeasureValue",
            "ResultMeasure/MeasureUnitCode",
        ]
        site_cols = [
            "MonitoringLocationIdentifier",
            "LatitudeMeasure",
            "LongitudeMeasure",
        ]

        us_res = pd.read_csv(
            us_res_file, usecols=lambda c: c in res_cols, low_memory=False
        )
        us_sites = pd.read_csv(
            us_sta_file, usecols=lambda c: c in site_cols, low_memory=False
        )

        us_res = us_res.merge(us_sites, on="MonitoringLocationIdentifier", how="inner")
        us_res = us_res.rename(
            columns={
                "LatitudeMeasure": "LATITUDE_DD",
                "LongitudeMeasure": "LONGITUDE_DD",
                "ActivityStartDate": "Date",
            }
        )
        us_res = us_res.loc[:, ~us_res.columns.duplicated()]

        us_map = {
            "Oxygen": "DO",
            "Temperature": "Temp",
            "pH": "pH",
            "Chlorophyll": "Chlorophyll",
            "Depth": "Depth",
        }
        for pattern, clean_name in us_map.items():
            mask = (
                us_res["CharacteristicName"]
                .astype(str)
                .str.contains(pattern, case=False, na=False)
            )
            us_res.loc[mask, "Variable"] = clean_name

        us_res = us_res.dropna(subset=["Variable"])
        full_df = pd.concat([full_df, us_res], ignore_index=True)
        print(f"    -> Extracted {len(us_res):,} relevant U.S. WQP records.")

    # --------------------------------------------------------------------------
    # STEP 3: PROCESS CANADIAN DATA (ECCC)
    # --------------------------------------------------------------------------
    if os.path.exists(CA_DIR):
        print("  -> Loading Canadian ECCC Data...")
        ca_files = [
            os.path.join(CA_DIR, f) for f in os.listdir(CA_DIR) if f.endswith(".csv")
        ]
        ca_vars = {
            "OXYGEN": "DO",
            "TEMPERATURE": "Temp",
            "PH": "pH",
            "CHLOROPHYLL": "Chlorophyll",
            "CHL": "Chlorophyll",
        }

        ca_records = 0
        for f in ca_files:
            temp = pd.read_csv(f, low_memory=False)

            name_col = next(
                (
                    c
                    for c in [
                        "FULL_NAME",
                        "VARIABLE_NAME",
                        "VARIABLE",
                        "PARAM",
                        "CharacteristicName",
                    ]
                    if c in temp.columns
                ),
                None,
            )
            val_col = next(
                (
                    c
                    for c in [
                        "RESULT_VALUE",
                        "VALUE",
                        "RESULT",
                        "MEASUREMENT_VALUE",
                        "MEASURE",
                    ]
                    if c in temp.columns
                ),
                None,
            )
            unit_col = next(
                (
                    c
                    for c in ["UNITS", "UNIT", "UNIT_CODE", "MEASURE_UNIT"]
                    if c in temp.columns
                ),
                None,
            )
            lat_col = next(
                (
                    c
                    for c in ["LATITUDE_DD", "LAT_DD", "LATITUDE", "LAT"]
                    if c in temp.columns
                ),
                None,
            )
            lon_col = next(
                (
                    c
                    for c in ["LONGITUDE_DD", "LON_DD", "LONGITUDE", "LON", "LONG"]
                    if c in temp.columns
                ),
                None,
            )
            date_col = next(
                (
                    c
                    for c in [
                        "STN_DATE",
                        "DATE",
                        "SAMPLE_DATE",
                        "Date",
                        "ActivityStartDate",
                    ]
                    if c in temp.columns
                ),
                None,
            )

            if all([name_col, val_col, lat_col, lon_col, date_col]):
                rename_dict = {
                    val_col: "ResultMeasureValue",
                    lat_col: "LATITUDE_DD",
                    lon_col: "LONGITUDE_DD",
                    name_col: "CharacteristicName",
                    date_col: "Date",
                }
                if unit_col:
                    rename_dict[unit_col] = "ResultMeasure/MeasureUnitCode"

                temp = temp.rename(columns=rename_dict)
                for pattern, clean_name in ca_vars.items():
                    mask = (
                        temp["CharacteristicName"]
                        .astype(str)
                        .str.contains(pattern, case=False, na=False)
                    )
                    temp.loc[mask, "Variable"] = clean_name

                temp = temp.dropna(subset=["Variable"])
                full_df = pd.concat([full_df, temp], ignore_index=True)
                ca_records += len(temp)

        print(f"    -> Extracted {ca_records:,} relevant Canadian records.")

    # --------------------------------------------------------------------------
    # STEP 4: PROCESS EPA GLENDA DATA (DYNAMIC OMNI-PARSER)
    # --------------------------------------------------------------------------
    if os.path.exists(GLENDA_DIR):
        print("  -> Loading EPA GLENDA Data...")
        glenda_files = [
            os.path.join(GLENDA_DIR, f)
            for f in os.listdir(GLENDA_DIR)
            if f.endswith(".csv")
        ]
        glenda_records = 0

        for f in glenda_files:
            temp = pd.read_csv(f, low_memory=False)

            # Format 1: Wide Format (Lab Chemistry like pH, Chloride, etc.)
            if all(
                col in temp.columns
                for col in ["LATITUDE", "LONGITUDE", "SAMPLING_DATE, GMT"]
            ):
                keep_cols = ["LATITUDE", "LONGITUDE", "SAMPLING_DATE, GMT"]
                available_vars = {}
                if "pH" in temp.columns:
                    available_vars["pH"] = "pH"
                if "Dissolved Oxygen, mg/L" in temp.columns:
                    available_vars["Dissolved Oxygen, mg/L"] = "DO"
                elif "DO, mg/L" in temp.columns:
                    available_vars["DO, mg/L"] = "DO"
                if "Temperature, C" in temp.columns:
                    available_vars["Temperature, C"] = "Temp"
                elif "Temp, C" in temp.columns:
                    available_vars["Temp, C"] = "Temp"

                for raw_var, clean_var in available_vars.items():
                    var_df = temp[keep_cols + [raw_var]].copy()
                    var_df = var_df.rename(
                        columns={
                            "LATITUDE": "LATITUDE_DD",
                            "LONGITUDE": "LONGITUDE_DD",
                            "SAMPLING_DATE, GMT": "Date",
                            raw_var: "ResultMeasureValue",
                        }
                    )
                    var_df["Variable"] = clean_var
                    if clean_var == "pH":
                        var_df["ResultMeasure/MeasureUnitCode"] = "none"
                    if clean_var == "DO":
                        var_df["ResultMeasure/MeasureUnitCode"] = "mg/l"
                    if clean_var == "Temp":
                        var_df["ResultMeasure/MeasureUnitCode"] = "deg c"

                    var_df = var_df.dropna(subset=["ResultMeasureValue"])

                    # Pre-parse Dates to avoid Pandas collision
                    var_df["Date"] = pd.to_datetime(var_df["Date"], errors="coerce")

                    full_df = pd.concat([full_df, var_df], ignore_index=True)
                    glenda_records += len(var_df)

            # Format 2: Long Format (CTD Sensor Data like GLENDA_Temp_DO.csv)
            elif all(
                col in temp.columns
                for col in [
                    "LATITUDE",
                    "LONGITUDE",
                    "SAMPLING_DATE",
                    "ANL_CODE_1",
                    "VALUE_1",
                ]
            ):
                df1 = temp[
                    [
                        "LATITUDE",
                        "LONGITUDE",
                        "SAMPLING_DATE",
                        "ANL_CODE_1",
                        "VALUE_1",
                        "UNITS_1",
                    ]
                ].copy()
                df1.columns = [
                    "LATITUDE_DD",
                    "LONGITUDE_DD",
                    "Date",
                    "CharacteristicName",
                    "ResultMeasureValue",
                    "ResultMeasure/MeasureUnitCode",
                ]

                # Check for second column of parameters
                if "ANL_CODE_2" in temp.columns and "VALUE_2" in temp.columns:
                    df2 = temp[
                        [
                            "LATITUDE",
                            "LONGITUDE",
                            "SAMPLING_DATE",
                            "ANL_CODE_2",
                            "VALUE_2",
                            "UNITS_2",
                        ]
                    ].copy()
                    df2.columns = [
                        "LATITUDE_DD",
                        "LONGITUDE_DD",
                        "Date",
                        "CharacteristicName",
                        "ResultMeasureValue",
                        "ResultMeasure/MeasureUnitCode",
                    ]
                    df2 = df2.dropna(subset=["CharacteristicName"])
                    long_df = pd.concat([df1, df2], ignore_index=True)
                else:
                    long_df = df1

                glenda_vars = {
                    "OXYGEN": "DO",
                    "DO": "DO",
                    "O2DISS": "DO",
                    "TEMP": "Temp",
                    "PH": "pH",
                    "CHLOROPHYLL": "Chlorophyll",
                    "SECCHI": "Secchi",
                }
                for pattern, clean_name in glenda_vars.items():
                    mask = (
                        long_df["CharacteristicName"]
                        .astype(str)
                        .str.contains(pattern, case=False, na=False)
                    )
                    long_df.loc[mask, "Variable"] = clean_name

                long_df = long_df.dropna(subset=["Variable", "ResultMeasureValue"])
                long_df = long_df[
                    long_df["ResultMeasureValue"].astype(str).str.strip()
                    != "No result reported."
                ]

                # Pre-parse Dates to avoid Pandas collision
                long_df["Date"] = pd.to_datetime(long_df["Date"], errors="coerce")

                full_df = pd.concat([full_df, long_df], ignore_index=True)
                glenda_records += len(long_df)

        print(f"    -> Extracted {glenda_records:,} relevant EPA GLENDA records.")

    # --------------------------------------------------------------------------
    # STEP 5: NUMERIC COERCION & UNIT NORMALIZATION
    # --------------------------------------------------------------------------
    if not full_df.empty:
        print("\n  -> Cleaning numeric artifacts and applying Unit Rules...")
        full_df["ResultMeasureValue"] = (
            full_df["ResultMeasureValue"]
            .astype(str)
            .str.replace(r"[<>\s]", "", regex=True)
        )
        full_df["ResultMeasureValue"] = pd.to_numeric(
            full_df["ResultMeasureValue"], errors="coerce"
        )
        full_df["LATITUDE_DD"] = pd.to_numeric(full_df["LATITUDE_DD"], errors="coerce")
        full_df["LONGITUDE_DD"] = pd.to_numeric(
            full_df["LONGITUDE_DD"], errors="coerce"
        )
        full_df = full_df.dropna(
            subset=["ResultMeasureValue", "LATITUDE_DD", "LONGITUDE_DD"]
        )

        unit_rules = {
            "DO": ["mg/l"],
            "Temp": ["deg c", "°c", "c"],
            "pH": ["std units", "none", "ph", "unitless"],
            "Chlorophyll": ["ug/l", "µg/l", "mg/m3", "mg/l"],
            "Depth": ["m", "ft"],
        }

        final_list = []
        for var, units in unit_rules.items():
            var_df = full_df[full_df["Variable"] == var].copy()
            u_col = "ResultMeasure/MeasureUnitCode"

            if u_col in var_df.columns:
                u_norm = var_df[u_col].astype(str).str.lower().str.strip()
                # Allow empty units for GLENDA/ECCC assuming metric standard
                valid_mask = (
                    u_norm.isin(units)
                    | u_norm.isin(["nan", "", "none", "null"])
                    | var_df[u_col].isna()
                )
                if var != "pH":
                    var_df = var_df[valid_mask]

                u_norm = var_df[u_col].astype(str).str.lower().str.strip()
                var_df.loc[u_norm == "ft", "ResultMeasureValue"] *= 0.3048
                if var == "Chlorophyll":
                    var_df.loc[u_norm == "mg/l", "ResultMeasureValue"] *= 1000

            final_list.append(var_df)

        final_df = pd.concat(final_list, ignore_index=True)

        # --------------------------------------------------------------------------
        # STEP 6: QA/QC FILTERING
        # --------------------------------------------------------------------------
        print("\n  ✂️ Applying QA/QC Filters...")
        initial_count = len(final_df)

        final_df = final_df[
            (final_df["LATITUDE_DD"] >= 41.0)
            & (final_df["LATITUDE_DD"] <= 49.5)
            & (final_df["LONGITUDE_DD"] >= -93.0)
            & (final_df["LONGITUDE_DD"] <= -75.0)
        ]

        if "Date" in final_df.columns:
            final_df["Date"] = pd.to_datetime(final_df["Date"], errors="coerce")
            final_df = final_df.dropna(subset=["Date"])
            final_df = final_df[final_df["Date"].dt.month.between(6, 9)]

        outlier_masks = [
            (final_df["Variable"] == "Temp")
            & (
                (final_df["ResultMeasureValue"] < 0)
                | (final_df["ResultMeasureValue"] > 35)
            ),
            (final_df["Variable"] == "DO")
            & (
                (final_df["ResultMeasureValue"] < 0)
                | (final_df["ResultMeasureValue"] > 25)
            ),
            (final_df["Variable"] == "pH")
            & (
                (final_df["ResultMeasureValue"] < 4)
                | (final_df["ResultMeasureValue"] > 10)
            ),
        ]

        combined_mask = pd.concat(outlier_masks, axis=1).any(axis=1)
        final_df = final_df[~combined_mask]

        print(f"    -> Records processed before QA/QC: {initial_count:,}")
        print(f"    -> Records surviving QA/QC: {len(final_df):,}")

        final_export = final_df[
            [
                "Date",
                "LATITUDE_DD",
                "LONGITUDE_DD",
                "Variable",
                "ResultMeasureValue",
                "ResultMeasure/MeasureUnitCode",
            ]
        ]
        final_export.to_csv(OUT_FILE, index=False)

        print(f"\n🏆 STEP 1A COMPLETE: Cleaned data saved to Data_Clean folder!")
    else:
        print("❌ CRITICAL: No data survived.")


if __name__ == "__main__":
    run_binational_pull()
