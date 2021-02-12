# New-Graph-Analysis

This repository contains the various scripts utilized in our paper
"A Brave new World." In the following sections, we document how
to utilize each of them, starting with the Size Analysis script.

## 0. Requirements for All Analyses
- Python3 and pip3
- Jupyter Notebook
- Python Packages you may need to install: NetworkX, adblockparser

## 1. Size Analysis

__TODO: need to modify this readme for branch-analysis updates.__

#### Setup
1. Clone the repository.
2. Ensure you have modified the filepaths in get_paths.py and ran the get_paths.py on your graph folder.
3. Modify config file: nodal_size_analysis_config.py.
4. Modify config file: branch_size_analysis_config.py.

#### Usage

1. Run nodal_size_analysis.py on all the graphml data
2. Run branch_size_analysis.py on all the graphml data.
3. Modify filepaths for paper-ready python notebook for the data from 
    nodal_size_analysis.py and branch_size_analysis.py
4. Run the size_analysis_paper_ready python notebook to generate data.

## 2. Tracker and Ad Bytes Analysis
In this script, we create a simple chart that depicts the median sizes
of the ad and tracker bytes. We also add a line depicting the standard deviation.

#### Requirements
In order to utilize this script, we need to make sure we have the generated JSON
data from Size Analysis (1).


__TODO: Need to modify notebook to include others column and explain a few things in python script__

#### Setup
1. Enter the "tracker_and_ad_bytes" directory.
2. Open up the notebook file.
3. Modify the "data_dir" variable to point to your directory containing the various json files from
the size analysis script.
4. Simply run the notebook from top down after configuring this directory.


## 3. Popularity Analysis
In this script, we utilize the graphml data and filter lists to obtain data on trackers and ads
per website. From the gathered, we can calculate the amount of trackers, ads, and how the popularity of a 
website (based on its position on the Alexa Top 1M) will affect such amounts. 

#### Requirements
In order to utilize this script, you must run the tracker_ads_popularity_analysis.py to grab data on all
of the websites. Once doing so, you can use the ipynb to run analysis on "urls_?.txt" files to generate the
graphs.

#### Usage

1. Run tracker_ads_popularity_analysis.py on all the graphml data (using the output from get_paths.py).
2. Open the jupyter notebooks.
3. Edit the constants: 
    - URL_DATA_FOLDER to wherever the urls folder is from Step 1.
    - ALEXA_TOP_1M_FILEPATH to wherever the alexa top1m list is
    - any constant ending in _FILE or _PATH is simply where the graphs will be saved to (.pdf files).
4. Run the jupyter notebooks until the end.


