# Great Lakes Native Fish Refugia Modeling: Supplementary Data & Code

### Overview
This repository contains the supplementary datasets, spatial outputs, and custom Python (`arcpy`) geoprocessing scripts associated with the study on identifying minimally invaded ecological refugia for native sport fishes in the Laurentian Great Lakes. The research quantifies the "habitat squeeze" caused by Aquatic Invasive Species (AIS) on three ecologically and economically vital native fishes: **Walleye (*Sander vitreus*)**, **Yellow Perch (*Perca flavescens*)**, and **Lake Whitefish (*Coregonus clupeaformis*)**. 

By synthesizing physical limnology, reproductive biology, and invasion ecology, this project provides a basin-wide geostatistical framework to assist fisheries managers in prioritizing urgent AIS mitigation and optimizing strategic stocking efforts.

---

### Repository Structure
This repository is organized into the following directories to ensure full methodological transparency and reproducibility:

#### 1. `Data_and_Impact_Dictionaries/`
Contains the raw statistical and biological threshold data utilized to evaluate invasive threats and quantify habitat:
* **`Scored_Impact_Data_[Species].csv`**: Comprehensive impact dictionaries isolating the specific direct and indirect ecological impacts of over 180 nonindigenous species on the focal native fishes, complete with quantitative impact scores.
* **`Final_Thesis_MultiScenario_Stats.csv`**: The master statistical database containing the zonal statistics (potential habitat, actual refugia area, and percentage protected) extracted across varying sensitivity thresholds.
* **`Supplementary_Bibliography.pdf`**: The comprehensive list of over 160 references utilized to calculate the AIS impact scores.

#### 2. `Geoprocessing_Scripts/`
Contains the custom Python (`arcpy`) pipelines developed to execute the spatial modeling:
* **Data Harmonization:** Scripts that parse, standardize, and QA/QC fragmented binational water quality data from the WQP, ECCC, and EPA GLENDA databases.
* **Environmental Baselines:** Scripts executing Empirical Bayesian Kriging (EBK) and Euclidean distance models for physical constraints (e.g., bathymetry, fetch, substrate, tributary proximity).
* **Suitability & Threat Modeling:** Scripts automating the Weighted Sum Habitat Suitability Index (HSI) overlays, alongside observational bias correction (spatial thinning), Kernel Density Estimation (KDE), and Threat Inversion Algebra for high-impact AIS.
* **Map Algebra:** Boolean map algebra scripts used to calculate the intersection of optimal native habitat and low invasive pressure across Liberal, Moderate, and Strict sensitivity scenarios.

#### 3. `Spatial_Outputs/`
* **`[Species]_Comparison_Grid.shp`**: Finalized vector shapefiles containing the absolute area (in square kilometers) of surviving refugia per standardized spatial grid cell.

#### 4. `Figures_and_Visualizations/`
* **`Workflow_Diagram_Academic.png`**: A high-resolution flowchart detailing the complete transition from raw data preparation to final refugia intersection.
* **`Sensitivity_Plot_Decay.png`**: Bar charts and line plots visualizing the absolute footprint of refugia and the rate of habitat decay across different management scenarios. 
* **`Habitat_Squeeze_Plots.png`**: Visual representations contrasting Potential Baseline Habitat against Actual Surviving Refugia.

---

### Data Sources
The models generated in this repository were built upon harmonized data sourced from:
* **GLANSIS** (Great Lakes Aquatic Nonindigenous Species Information System)
* **GLAHF** (Great Lakes Aquatic Habitat Framework)
* **WQP** (Water Quality Portal)
* **ECCC** (Environment and Climate Change Canada)
* **GLENDA** (EPA Great Lakes Environmental Database)

---

### Requirements & Dependencies
To run the geoprocessing scripts, the following environments and packages are required:
* **Python 3.x**
* **Esri ArcGIS Pro (Advanced License)** with the **Spatial Analyst** extension enabled (required for all `arcpy` execution). 
* `pandas`, `matplotlib`, and `seaborn` (for data visualization and statistical plotting). 

---

### Acknowledgments and Funding
This research was supported by the **U.S. Coastal Research Program (USCRP)** under Contract #W912HZ24C0054. 
* **Principal Investigator:** Dr. Silvia Newell (University of Michigan, Michigan Sea Grant)
* **GLANSIS Program Manager:** Dr. Rochelle Sturtevant (Michigan State University)
* **Researchers/Authors:** Connor Shelly (University of Michigan School for Environment and Sustainability)
