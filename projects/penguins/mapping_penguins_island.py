import os
import pandas as pd
import folium

# 1. Load your CSV dataset
data_path = os.path.join("data", "penguins", "Penguin Species Prediction Dataset.csv")
df = pd.read_csv(data_path)

# Drop missing values if present
df = df.dropna(subset=['island', 'species'])

# 2. Known coordinates for Palmer Archipelago Islands
ISLAND_COORDS = {
    'Torgersen': (-64.773, -64.074),
    'Biscoe': (-64.800, -63.783),
    'Dream': (-64.733, -64.233)
}

# 3. Initialize map centered around the Palmer Archipelago
m = folium.Map(location=[-64.77, -64.05], zoom_start=9, tiles="OpenStreetMap")

# 4. Group data by island and calculate summary statistics
for island_name, coords in ISLAND_COORDS.items():
    island_data = df[df['island'].str.contains(island_name, case=False, na=False)]
    
    if not island_data.empty:
        total_count = len(island_data)
        species_counts = island_data['species'].value_counts().to_dict()
        avg_mass = island_data['body_mass_g'].mean()
        avg_flipper = island_data['flipper_length_mm'].mean()
        
        # Build HTML popup text
        species_str = "<br>".join([f"• <b>{s}:</b> {c}" for s, c in species_counts.items()])
        popup_html = f"""
        <div style="font-family: sans-serif; width: 200px;">
            <h4 style="margin-bottom: 5px;">{island_name} Island</h4>
            <b>Total Penguins:</b> {total_count}<br><br>
            <b>Species Breakdown:</b><br>{species_str}<br><br>
            <b>Avg Mass:</b> {avg_mass:.0f}g<br>
            <b>Avg Flipper:</b> {avg_flipper:.1f}mm
        </div>
        """
        
        # Add marker to the map
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{island_name} Island ({total_count} penguins)",
            icon=folium.Icon(color="cadetblue", icon="info-sign")
        ).add_to(m)

# 5. Define output directory & save interactive HTML map
output_dir = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\projects\penguins"
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "penguin_island_map.html")
m.save(output_file)

print(f"Saved map to '{output_file}'. Open this file in your browser!")