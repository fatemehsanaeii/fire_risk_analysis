
import ee
import geemap
import sys
import time
import os
import math
import tkinter as tk
from PIL import Image, ImageTk
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# ----------------------- Earth Engine Setup and Fire Risk Analysis -----------------------

def run_fire_risk_analysis(longitude, latitude):
    """
    Run Fire Risk Analysis using Google Earth Engine for a given longitude and latitude.
    Exports various layers (NDVI, LST, Precipitation, Slope, Aspect Score, Fire Risk) to Google Drive.
    """
    ee.Initialize(project="project-ee-458713")

    # Define the study area as a 30 km buffer around the input point
    point = ee.Geometry.Point([longitude, latitude])
    area = point.buffer(30000)

    # Date range for data filtering
    start = '2023-07-01'
    end = '2023-08-31'

    # Sentinel-2 NDVI
    s2 = ee.ImageCollection("COPERNICUS/S2_SR") \
        .filterBounds(area) \
        .filterDate(start, end) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
    s2_median = s2.median()
    ndvi = ee.Image(
        ee.Algorithms.If(
            s2_median.bandNames().size().gt(0),
            s2_median.normalizedDifference(['B8', 'B4']).rename('NDVI'),
            ee.Image(0).rename('NDVI')
        )
    )

    # MODIS Land Surface Temperature (LST)
    lstCol = ee.ImageCollection("MODIS/006/MOD11A2") \
        .filterBounds(area) \
        .filterDate(start, end) \
        .select('LST_Day_1km')
    lstImage = lstCol.mean()
    lst = ee.Image(
        ee.Algorithms.If(
            lstImage.bandNames().size().gt(0),
            lstImage.multiply(0.02).subtract(273.15).rename('LST'),
            ee.Image(25).rename('LST')
        )
    )

    # CHIRPS Rainfall
    chirpsCol = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterBounds(area) \
        .filterDate('2023-06-01', end)
    precipImage = chirpsCol.sum()
    precip = ee.Image(
        ee.Algorithms.If(
            precipImage.bandNames().size().gt(0),
            precipImage.rename('Precip'),
            ee.Image(10).rename('Precip')
        )
    )

    # DEM - Slope and Aspect
    dem = ee.Image("USGS/SRTMGL1_003").clip(area)
    terrain = ee.Algorithms.Terrain(dem)
    slope = terrain.select('slope').rename('Slope')
    aspect = terrain.select('aspect').rename('Aspect')

    # Normalize layers for fire risk index calculation
    ndvi_norm = ndvi.unitScale(0, 1).clamp(0, 1)
    lst_norm = lst.unitScale(20, 45).clamp(0, 1)
    slope_norm = slope.unitScale(0, 60).clamp(0, 1)
    aspect_south = aspect.expression(
        "cos((aspect - 180) * 3.1416 / 180)", {'aspect': aspect}
    ).rename('Aspect_Score')
    precip_norm = precip.unitScale(0, 150).clamp(0, 1)

    # Fire Risk Index computation
    fireRisk = lst_norm.multiply(0.3) \
        .add(ndvi_norm.multiply(-0.3)) \
        .add(slope_norm.multiply(0.15)) \
        .add(aspect_south.multiply(0.15)) \
        .add(precip_norm.multiply(-0.1)) \
        .rename('Fire_Risk')

    # Function to export a layer to Google Drive
    def export_layer(image, name):
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=name,
            folder='EarthEnginefatemeh',
            fileNamePrefix=name,
            region=area.bounds(),
            scale=30,
            maxPixels=1e13
        )
        task.start()
        print(f"Export started: {name}")

    # Export all layers
    export_layer(ndvi, f'NDVI_{latitude}_{longitude}')
    export_layer(lst, f'LST_{latitude}_{longitude}')
    export_layer(precip, f'Precip_{latitude}_{longitude}')
    export_layer(slope, f'Slope_{latitude}_{longitude}')
    export_layer(aspect_south, f'Aspect_Score_{latitude}_{longitude}')
    export_layer(fireRisk, f'Fire_Risk_{latitude}_{longitude}')

    # Return export started message
    print("All export tasks started. Please wait for completion before downloading.")


# ----------------------- Download exported files from Google Drive -----------------------

def download_exports_from_drive():
    """
    Authenticates with Google Drive and downloads all files from the specified folder.
    """
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Opens browser to authenticate
    drive = GoogleDrive(gauth)

    folder_name = 'EarthEnginefatemeh'

    # Find the folder ID
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if not file_list:
        raise Exception(f"Folder '{folder_name}' not found in Drive")

    folder_id = file_list[0]['id']

    # List files inside the folder
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

    download_path = "downloads"
    os.makedirs(download_path, exist_ok=True)

    for file in file_list:
        print(f"Downloading {file['title']}...")
        file.GetContentFile(os.path.join(download_path, file['title']))

    print("✅ All files downloaded.")


# ----------------------- GUI for province selection and running analysis -----------------------

# Provinces with coordinates
PROVINCES = [
    ("Tehran", 35.6892, 51.3890),
    ("Isfahan", 32.6519, 51.6680),
    ("Fars", 29.5893, 52.5311),
    ("Razavi Khorasan", 36.3000, 59.6000),
    ("Mazandaran", 36.5525, 53.0762),
    ("Kurdistan", 34.7800, 46.5300),
    ("Khuzestan", 31.9391, 48.6692),
    ("East Azerbaijan", 38.0700, 46.2960),
    ("West Azerbaijan", 37.5300, 45.0000),
    ("Ardabil", 38.2500, 48.3000),
    ("Zanjan", 36.6764, 48.4963),
    ("Qazvin", 36.2700, 50.0000),
    ("Gilan", 37.2800, 49.5832),
    ("Golestan", 36.8400, 54.4300),
    ("Semnan", 35.5700, 53.4000),
    ("Alborz", 35.8400, 50.9400),
    ("Qom", 34.6400, 50.8800),
    ("Markazi", 34.1000, 49.7000),
    ("Hamedan", 34.8000, 48.5000),
    ("Ilam", 33.6300, 46.4200),
    ("Lorestan", 33.5800, 48.3500),
    ("Chaharmahal and Bakhtiari", 32.3200, 50.8600),
    ("Kohgiluyeh and Boyer-Ahmad", 30.6500, 51.6000),
    ("Bushehr", 28.9200, 50.8300),
    ("Hormozgan", 27.2000, 56.3700),
    ("Sistan and Baluchestan", 29.4900, 60.8500),
    ("Kerman", 30.2839, 57.0834),
    ("Yazd", 31.8974, 54.3569),
    ("South Khorasan", 32.8700, 59.2200),
    ("North Khorasan", 37.4700, 57.3300),
]

# Map boundaries for coordinate to pixel conversion
MIN_LAT, MAX_LAT = 25, 39
MIN_LON, MAX_LON = 44, 63
WIDTH, HEIGHT = 800, 1000  # GUI canvas size


def geo_to_pixel(lat, lon):
    """Convert geographic coordinates to pixel position on the GUI map."""
    x = (lon - MIN_LON) / (MAX_LON - MIN_LON) * WIDTH
    y = (MAX_LAT - lat) / (MAX_LAT - MIN_LAT) * HEIGHT
    return int(x), int(y)


def pixel_to_geo(x, y):
    """Convert pixel position to geographic coordinates."""
    lon = x / WIDTH * (MAX_LON - MIN_LON) + MIN_LON
    lat = MAX_LAT - y / HEIGHT * (MAX_LAT - MIN_LAT)
    return lat, lon


def on_map_click(event):
    """Handle click event on the map to select nearest province and run analysis."""
    lat, lon = pixel_to_geo(event.x, event.y)

    # Find nearest province by Euclidean distance
    nearest = None
    min_dist = float("inf")
    for name, plat, plon in PROVINCES:
        dist = math.hypot(lat - plat, lon - plon)
        if dist < min_dist:
            min_dist = dist
            nearest = (name, plat, plon)

    if nearest:
        name, plat, plon = nearest
        print(f"You clicked near: {name} (lat: {plat}, lon: {plon})")

        # Run Fire Risk Analysis for the selected province coordinates
        run_fire_risk_analysis(plon, plat)

        # Wait a bit, then start downloading exported files
        print("Waiting for exports to complete before downloading...")
        # Wait 1 minute here for demo; increase if needed
        for remaining in range(60, 0, -1):
            print(f"\rTime remaining: {remaining} seconds", end="")
            time.sleep(1)
        print("\nStarting download...")
        download_exports_from_drive()


def create_gui():
    """Create the GUI window for map and province selection."""
    root = tk.Tk()
    root.title("Iran Map Fire Risk Analysis")

    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
    canvas.pack()

    # Load map image (make sure 'iran_map.png' is in your folder)
    map_image = Image.open("iran_map.png").resize((WIDTH, HEIGHT))
    map_photo = ImageTk.PhotoImage(map_image)
    canvas.create_image(0, 0, anchor=tk.NW, image=map_photo)

    # Draw province names on map
    for name, lat, lon in PROVINCES:
        x, y = geo_to_pixel(lat, lon)
        canvas.create_text(x, y, text=name, fill="red", font=("Arial", 10, "bold"))

    # Bind click event
    canvas.bind("<Button-1>", on_map_click)

    root.mainloop()


# ----------------------- Main -----------------------

if __name__ == "__main__":
    # If longitude and latitude are given as command-line arguments, run analysis directly
    if len(sys.argv) == 3:
        try:
            lon = float(sys.argv[1])
            lat = float(sys.argv[2])
            run_fire_risk_analysis(lon, lat)
            print("Waiting for exports to complete before downloading...")
            for remaining in range(60, 0, -1):