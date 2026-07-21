"""
================================================================================
THESIS PIPELINE - STEP 7: MULTI-SCENARIO VISUALIZATION
Description: Creates comparison plots showing the "Decay" of refugia across
Liberal, Moderate, and Strict scenarios, plus Squeeze and Viability visualiztions.
================================================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- SETTINGS ---
PROJECT_DIR = r"C:\Users\shelly\Desktop\Masters\Analysis"
IN_CSV = os.path.join(PROJECT_DIR, "Final_Thesis_MultiScenario_Stats.csv")
PLOT_DIR = os.path.join(PROJECT_DIR, "Plots")

if not os.path.exists(PLOT_DIR):
    os.makedirs(PLOT_DIR)

# --- Styling ---
sns.set_theme(style="whitegrid")
plt.rcParams["figure.dpi"] = 300


def generate_sensitivity_plots():
    print("--- Phase 7: Generating Sensitivity Plots ---")

    if not os.path.exists(IN_CSV):
        print(f"  ❌ CSV not found at {IN_CSV}")
        return

    df = pd.read_csv(IN_CSV)
    df["Species_Display"] = df["Species"].str.replace("_", " ")

    # Ensure Scenarios are in the correct logical order
    df["Scenario"] = pd.Categorical(
        df["Scenario"], categories=["Liberal", "Moderate", "Strict"], ordered=True
    )

    # --- PLOT 1: THE REFUGIA DECAY (Total Area) ---
    print("  🗺️ Generating Plot 1: Area Comparison...")

    g1 = sns.catplot(
        data=df,
        kind="bar",
        x="Lake",
        y="Refugia_Area_SqKm",
        hue="Scenario",
        col="Species_Display",
        col_wrap=1,
        sharey=False,
        palette="YlGn_r",
        height=4,
        aspect=2,
        edgecolor=".2",
    )

    g1.set_axis_labels("Great Lake", "Refugia Surface Area (km²)")
    g1.set_titles("{col_name}")
    g1.fig.suptitle(
        "Refugia Sensitivity Analysis: Area Loss across Thresholds", y=1.02, fontsize=16
    )

    plt.savefig(
        os.path.join(PLOT_DIR, "Sensitivity_Plot1_Area_Decay.png"), bbox_inches="tight"
    )

    # --- PLOT 2: THE PERCENTAGE SHIFT (Relative Protection) ---
    print("  📊 Generating Plot 2: Percentage Protected...")

    g2 = sns.relplot(
        data=df,
        kind="line",
        x="Scenario",
        y="Pct_Protected",
        hue="Lake",
        col="Species_Display",
        col_wrap=1,
        marker="o",
        linewidth=2.5,
        markersize=8,
        height=3.5,
        aspect=2.5,
        facet_kws={"sharey": False},
    )

    g2.set_axis_labels("Management Scenario", "Percentage Protected (%)")
    g2.set_titles("{col_name}")
    g2.fig.suptitle(
        "Habitat Protection Decay: % of Suitable Area qualifying as Refugia",
        y=1.02,
        fontsize=16,
    )

    plt.savefig(
        os.path.join(PLOT_DIR, "Sensitivity_Plot2_Percentage_Decay.png"),
        bbox_inches="tight",
    )

    # --- PLOT 3: THE HABITAT SQUEEZE ---
    print("  📉 Generating Plot 3: Habitat Squeeze (Moderate Baseline)...")

    # Filter to only show the Moderate scenario for this specific comparison
    df_mod = df[df["Scenario"] == "Moderate"].copy()

    # Restructure data to plot Potential vs Actual side-by-side
    df_melt = pd.melt(
        df_mod,
        id_vars=["Lake", "Species_Display"],
        value_vars=["Potential_Habitat_SqKm", "Refugia_Area_SqKm"],
        var_name="Habitat_Type",
        value_name="Area_SqKm",
    )

    df_melt["Habitat_Type"] = df_melt["Habitat_Type"].map(
        {
            "Potential_Habitat_SqKm": "Potential Habitat",
            "Refugia_Area_SqKm": "Actual Refugia",
        }
    )

    g3 = sns.catplot(
        data=df_melt,
        kind="bar",
        x="Lake",
        y="Area_SqKm",
        hue="Habitat_Type",
        col="Species_Display",
        col_wrap=1,
        sharey=False,
        palette="Set2",
        height=4,
        aspect=2,
        edgecolor=".2",
    )

    g3.set_axis_labels("Great Lake", "Surface Area (km²)")
    g3.set_titles("{col_name}")
    g3.fig.suptitle(
        "The 'Habitat Squeeze': Potential vs. Actual Refugia (Moderate Scenario)",
        y=1.02,
        fontsize=16,
    )

    plt.savefig(
        os.path.join(PLOT_DIR, "Sensitivity_Plot3_Habitat_Squeeze.png"),
        bbox_inches="tight",
    )

    # --- PLOT 4: VIABILITY HEATMAPS ---
    print("  🟩 Generating Plot 4: Viability Heatmaps...")

    for species in df["Species_Display"].unique():
        df_sp = df[df["Species_Display"] == species]

        # Pivot table to make Lakes the rows and Scenarios the columns
        pivot_df = df_sp.pivot(index="Lake", columns="Scenario", values="Pct_Protected")

        plt.figure(figsize=(8, 5))
        sns.heatmap(
            pivot_df,
            annot=True,
            fmt=".1f",
            cmap="YlGnBu",
            cbar_kws={"label": "% Protected"},
        )

        plt.title(f"Refugia Viability Matrix: {species}", fontsize=14)
        plt.ylabel("Great Lake")
        plt.xlabel("Management Scenario")

        plt.savefig(
            os.path.join(
                PLOT_DIR, f"Sensitivity_Plot4_Heatmap_{species.replace(' ', '_')}.png"
            ),
            bbox_inches="tight",
        )
        plt.close()

    print(f"\n🏆 PLOTS GENERATED IN: {PLOT_DIR}")


if __name__ == "__main__":
    generate_sensitivity_plots()
