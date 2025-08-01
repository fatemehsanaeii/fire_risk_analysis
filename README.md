# Fire Risk Analysis Tool Using Google Earth Engine and Python

## Overview

This project implements a fire risk analysis workflow based on satellite and terrain data using **Google Earth Engine (GEE)** and Python.  
The tool allows you to calculate fire risk indices for locations in Iran based on NDVI, land surface temperature, precipitation, slope, and aspect, and exports the results to your Google Drive.  

Additionally, a simple graphical user interface (GUI) with a map of Iran lets you select provinces interactively to run the analysis and download the results automatically.

---

## Features

- Calculate Fire Risk Index from multiple Earth observation datasets (Sentinel-2, MODIS, CHIRPS, SRTM).
- Export multiple risk-related raster layers (NDVI, LST, Precipitation, Slope, Aspect Score, Fire Risk) to Google Drive.
- GUI for province selection via clicking on an Iran map.
- Automatic download of exported layers from Google Drive.
- Modular and clear Python implementation with Earth Engine and PyDrive integration.

---

## Requirements

- Python 3.7+
- Google Earth Engine Python API (`earthengine-api`)
- `geemap` library
- `PyDrive` for Google Drive authentication and file download
- `Pillow` for image handling in the GUI
- `tkinter` for GUI (usually comes pre-installed with Python)

You can install required packages using:

```bash
pip install earthengine-api geemap PyDrive Pillow
