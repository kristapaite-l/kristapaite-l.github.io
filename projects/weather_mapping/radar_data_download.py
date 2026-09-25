import os
import nexradaws
import pyart
import numpy as np
from scipy.ndimage import center_of_mass
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# -------------------------------------------------------------------------
# 0. DEFINE DIRECTORIES & ENSURE THEY EXIST
# -------------------------------------------------------------------------
data_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\data\weather_mapping"
output_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\projects\weather_mapping"

os.makedirs(data_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# -------------------------------------------------------------------------
# 1. DOWNLOAD RADAR FILE (nexradaws)
# -------------------------------------------------------------------------
conn = nexradaws.NexradAwsInterface()

# Query available scans for KTLX on May 20, 2023
scans = conn.get_avail_scans(2023, 5, 20, 'KTLX')
print(f"Found {len(scans)} scans for KTLX.")

# Download the first scan directly into data_dir
download_result = conn.download(scans[0], data_dir)
filepath = download_result.success[0].filepath
print(f"Successfully downloaded: {filepath}")

# -------------------------------------------------------------------------
# 2. PARSE RADIAL COORDINATES (Py-ART)
# -------------------------------------------------------------------------
radar = pyart.io.read_nexrad_archive(filepath)
print(f"Loaded radar site: {radar.metadata['instrument_name']}")

# Determine reflectivity field name (varies slightly between NEXRAD formats)
ref_field = 'reflectivity' if 'reflectivity' in radar.fields else 'equivalent_reflectivity_factor'

# -------------------------------------------------------------------------
# 3. GRID & PROJECT TO CARTESIAN COORDINATES
# -------------------------------------------------------------------------
# Convert polar sweeps to a 500x500 grid spanning 200 km around the radar
grid = pyart.map.grid_from_radars(
    (radar,),
    grid_shape=(1, 500, 500),
    grid_limits=((1000, 1000), (-200000, 200000), (-200000, 200000)),
    fields=[ref_field]
)

# -------------------------------------------------------------------------
# 4. ISOLATE STORM CORES & CALCULATE CENTROID
# -------------------------------------------------------------------------
grid_data = grid.fields[ref_field]['data'][0]

# Threshold reflectivity at >= 40 dBZ (thunderstorm cores)
storm_mask = np.where(grid_data >= 40, grid_data, 0)

# Calculate spatial centroid index (Y, X) within grid array
cy_idx, cx_idx = center_of_mass(storm_mask)

# Map grid indices back to geographic coordinates (latitude, longitude)
grid_lons = grid.point_longitude['data'][0]
grid_lats = grid.point_latitude['data'][0]

centroid_lon = grid_lons[int(cy_idx), int(cx_idx)]
centroid_lat = grid_lats[int(cy_idx), int(cx_idx)]

print(f"Storm Core Centroid: {centroid_lat:.4f}° N, {centroid_lon:.4f}° W")

# -------------------------------------------------------------------------
# 5. GEOSPATIAL MAP VISUALIZATION & SAVE
# -------------------------------------------------------------------------
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# Render the radar reflectivity grid
display = pyart.graph.GridMapDisplay(grid)
display.plot_grid(
    ref_field, 
    level=0, 
    ax=ax, 
    cmap='NWSRef', 
    vmin=-10, 
    vmax=75,
    colorbar_label='Reflectivity (dBZ)'
)

# Add map features
ax.coastlines()
ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5)

# Plot calculated storm center centroid marker
ax.plot(
    centroid_lon, 
    centroid_lat, 
    marker='X', 
    color='red', 
    markersize=12, 
    markeredgecolor='black',
    transform=ccrs.PlateCarree(),
    label='Storm Core Centroid'
)

plt.legend(loc='upper right')
filename_only = os.path.basename(filepath)
plt.title(f"NEXRAD Radar Scan with Storm Tracking\nFile: {filename_only}")

# Save image to project folder
image_save_path = os.path.join(output_dir, 'storm_visualization.png')
plt.savefig(image_save_path, dpi=300, bbox_inches='tight')
print(f"Saved visualization to: {image_save_path}")

plt.show()