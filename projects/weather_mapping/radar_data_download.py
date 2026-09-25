import os
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np
from scipy.ndimage import center_of_mass
import nexradaws
import pyart

# -------------------------------------------------------------------------
# 0. DIRECTORIES & SETUP
# -------------------------------------------------------------------------
data_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\data\weather_mapping"
output_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\projects\weather_mapping"
frames_dir = os.path.join(output_dir, "temp_frames")

os.makedirs(data_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(frames_dir, exist_ok=True)

# -------------------------------------------------------------------------
# 1. FETCH MULTIPLE SCANS
# -------------------------------------------------------------------------
conn = nexradaws.NexradAwsInterface()

# Query available scans for May 20, 2023 for station KTLX
scans = conn.get_avail_scans(2023, 5, 20, 'KTLX')

# Take a slice of 10 sequential scans (e.g., ~1 hour of radar activity)
selected_scans = scans[50:60]
print(f"Processing {len(selected_scans)} sequential scans for animation...")

frame_paths = []

# -------------------------------------------------------------------------
# 2. LOOP & GENERATE INDIVIDUAL FRAMES
# -------------------------------------------------------------------------
for idx, scan in enumerate(selected_scans):
    print(f"\n[Frame {idx + 1}/{len(selected_scans)}] Downloading {scan.filename}...")
    
    # Download scan
    download_result = conn.download(scan, data_dir)
    filepath = download_result.success[0].filepath

    # Read radar data
    radar = pyart.io.read_nexrad_archive(filepath)
    ref_field = 'reflectivity' if 'reflectivity' in radar.fields else 'equivalent_reflectivity_factor'

    # Grid data to 500x500 spatial coordinates
    grid = pyart.map.grid_from_radars(
        (radar,),
        grid_shape=(1, 500, 500),
        grid_limits=((1000, 1000), (-200000, 200000), (-200000, 200000)),
        fields=[ref_field]
    )

    # Isolate core reflectivity (>= 40 dBZ)
    grid_data = grid.fields[ref_field]['data'][0]
    storm_mask = np.where(grid_data >= 40, grid_data, 0)

    # Calculate centroid coordinates
    cy_idx, cx_idx = center_of_mass(storm_mask)
    
    if not np.isnan(cy_idx) and not np.isnan(cx_idx):
        grid_lons = grid.point_longitude['data'][0]
        grid_lats = grid.point_latitude['data'][0]
        centroid_lon = grid_lons[int(cy_idx), int(cx_idx)]
        centroid_lat = grid_lats[int(cy_idx), int(cx_idx)]
        has_centroid = True
    else:
        has_centroid = False

    # Plot map frame
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())

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

    ax.coastlines()
    ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5)

    if has_centroid:
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

    time_str = scan.filename.split('_')[1]  # Extract HHMMSS timestamp
    plt.title(f"NEXRAD Radar Motion Tracking\nScan Time: {time_str} UTC")

    # Save individual frame image
    frame_path = os.path.join(frames_dir, f"frame_{idx:03d}.png")
    plt.savefig(frame_path, dpi=150, bbox_inches='tight')
    plt.close(fig)  # Free memory
    
    frame_paths.append(frame_path)

# -------------------------------------------------------------------------
# 3. COMPILE FRAMES INTO ANIMATED GIF
# -------------------------------------------------------------------------
gif_output_path = os.path.join(output_dir, 'storm_tracking_movement.gif')
print(f"\nBuilding animated GIF from {len(frame_paths)} frames...")

images = [imageio.imread(f) for f in frame_paths]
imageio.mimsave(gif_output_path, images, fps=2, loop=0)

print(f"Animation saved successfully to: {gif_output_path}")