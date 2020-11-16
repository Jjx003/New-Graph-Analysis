# New-Graph-Analysis

This repository contains the various scripts utilized in our paper
"A Brave new World." In the following sections, we document how
to utilize each of them, starting with the Size Analysis script.

## 1. Size Analysis

__TODO: need to modify this readme for branch-analysis updates.__

#### Setup
1. Clone the repository.
2. Modify config file: nodal_size_analysis_config.py
3. Modify filepaths for branch-analysis.py

#### Usage

1. Run size-nodal_size_analysis.py on all the graphml data
2. Run branch-analysis.py on all the graphml data.
3. Modify filepaths for paper-ready python notebook for the data from 
    size-analysis.py and branch-analysis.py
4. Run the paper-ready python notebook to generate data.

## 2. Tracker and Ad Bytes Analysis
In this script, we create a simple chart that depicts the median sizes
of the ad and tracker bytes. We also add a line depicting the standard deviation.

## Requirements
In order to utilize this script, we need to make sure we have the generated JSON
data from Size Analysis (1).

### Setup
1. Enter the "tracker_and_ad_bytes" directory.
2. Open up the notebook file.
3. Modify the "data_dir" variable to point to your directory containing the various json files from
the size analysis script.
4. Simply run the notebook from top down after configuring this directory.

