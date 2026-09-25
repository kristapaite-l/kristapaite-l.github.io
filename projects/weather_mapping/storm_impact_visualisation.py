import os
import nexradaws
import pyart
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# -------------------------------------------------------------------------
# 0. DIRECTORIES & SETUP
# -------------------------------------------------------------------------
output_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\projects\weather_mapping"
os.makedirs(output_dir, exist_ok=True)

# Sample spatial asset data (Cities/Towns near KTLX Oklahoma area)
cities_data = {
    'City': ['Oklahoma City', 'Norman', 'Moore', 'Edmond', 'Shawnee'],
    'Population': [680000, 128000, 62000, 94000, 31000],
    'Latitude': [35.4676, 35.2226, 35.3395, 35.6528, 35.3273],
    'Longitude': [-97.5164, -97.4395, -97.4867, -97.4781, -96.9253]
}

# Convert sample data to a GeoDataFrame
geometry = [Point(xy) for xy in zip(cities_data['Longitude'], cities_data['Latitude'])]
cities_gdf = gpd.GeoDataFrame(cities_data, geometry=geometry, crs="EPSG:4326")

# -------------------------------------------------------------------------
# 1. FETCH & PROCESS RADAR DATA
# -------------------------------------------------------------------------
conn = nexradaws.NexradAwsInterface()
scans = conn.get_avail_scans(2023, 5, 20, 'KTLX')
valid_scans = [s for s in scans if not s.filename.endswith('_MDM')]

# Download scan
download_result = conn.download(valid_scans[55], output_dir)
filepath = download_result.success[0].filepath

radar = pyart.io.read_nexrad_archive(filepath)
ref_field = 'reflectivity' if 'reflectivity' in radar.fields else 'equivalent_reflectivity_factor'

# Grid to Cartesian coordinates
grid = pyart.map.grid_from_radars(
    (radar,),
    grid_shape=(1, 500, 500),
    grid_limits=((1000, 1000), (-200000, 200000), (-200000, 200000)),
    fields=[ref_field]
)

# -------------------------------------------------------------------------
# 2. EXTRACT SEVERE STORM POLYGONS & BUFFER ZONES
# -------------------------------------------------------------------------
grid_data = grid.fields[ref_field]['data'][0]
lons = grid.point_longitude['data'][0]
lats = grid.point_latitude['data'][0]

# Mask severe reflectivity (>= 15 dBZ for severe convective cores)
severe_points = []
for y in range(0, grid_data.shape[0], 2):  # Step by 2 for performance
    for x in range(0, grid_data.shape[1], 2):
        if grid_data[y, x] >= 15:
            severe_points.append(Point(lons[y, x], lats[y, x]))

if severe_points:
    # Combine severe points into a multipoint geometry
    severe_gdf = gpd.GeoDataFrame(geometry=severe_points, crs="EPSG:4326")
    
    # Project to metric CRS (UTM Zone 14N for Oklahoma) to calculate buffer in meters
    severe_projected = severe_gdf.to_crs(epsg=32614)
    
    # Create 15 km risk buffer around severe core points
    buffer_15km = severe_projected.buffer(15000).unary_union
    
    # Convert buffer back to WGS84 (Lat/Lon) for mapping & spatial joins
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_15km], crs="EPSG:32614").to_crs(epsg=4326)

    # -------------------------------------------------------------------------
    # 3. SPATIAL PROXIMITY ANALYTICS (Spatial Join)
    # -------------------------------------------------------------------------
    # Find cities located inside the 15km impact buffer
    impacted_cities = gpd.sjoin(cities_gdf, buffer_gdf, predicate='within')
    
    total_pop_at_risk = impacted_cities['Population'].sum()
    print("=== RISK ANALYTICS REPORT ===")
    print(f"Cities in 15km Warning Zone: {impacted_cities['City'].tolist()}")
    print(f"Total Estimated Population at Risk: {total_pop_at_risk:,}")

# -------------------------------------------------------------------------
    # 4. ENHANCED MAP VISUALIZATION
    # -------------------------------------------------------------------------
    fig = plt.figure(figsize=(11, 9))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Plot Radar Background
    display = pyart.graph.GridMapDisplay(grid)
    display.plot_grid(ref_field, level=0, ax=ax, cmap='NWSRef', vmin=-10, vmax=75)

    # Plot 15km Risk Buffer Zone (Semi-transparent red hatching)
    buffer_gdf.plot(
        ax=ax, 
        facecolor='red', 
        alpha=0.20, 
        edgecolor='crimson', 
        linewidth=2, 
        hatch='//',
        label='15km Risk Buffer Zone'
    )

    # Separate impacted vs unimpacted city GeoDataFrames
    impacted_indices = impacted_cities.index
    unimpacted_gdf = cities_gdf[~cities_gdf.index.isin(impacted_indices)]

    # 1. Plot Unimpacted Cities (Navy Diamonds with White Outline)
    if not unimpacted_gdf.empty:
        unimpacted_gdf.plot(
            ax=ax, 
            color='#0d233a', 
            marker='D', 
            markersize=65, 
            edgecolor='white', 
            linewidth=1.5,
            label='Unimpacted City'
        )

    # 2. Plot Impacted Cities (Bright Magenta/Cyan Triangles with Thick Black Outline)
    if not impacted_cities.empty:
        impacted_cities.plot(
            ax=ax, 
            color='#ff007f', 
            marker='^', 
            markersize=120, 
            edgecolor='black', 
            linewidth=2.0,
            label='City At Risk (Impacted)'
        )
        
        # Add labels for impacted cities with high-contrast text boxes
        for _, row in impacted_cities.iterrows():
            ax.text(
                row['Longitude'] + 0.02, 
                row['Latitude'] + 0.01, 
                f"{row['City']}\n(Pop: {row['Population']:,})", 
                fontsize=9, 
                fontweight='bold', 
                color='black',
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec="#ff007f", lw=1.5)
            )

    # Map details & formatting
    ax.coastlines()
    ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5)

    plt.title(
        f"Severe Weather Proximity & Population Risk Analysis\n"
        f"Total Estimated Population at Risk: {total_pop_at_risk:,}", 
        fontsize=12, 
        fontweight='bold',
        pad=12
    )
    
    plt.legend(loc='lower right', framealpha=0.95, facecolor='white')

    save_path = os.path.join(output_dir, 'proximity_risk_analysis.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved enhanced risk map to: {save_path}")
    plt.show()
else:
    print("No severe core points (>= 15 dBZ) detected in this scan.")