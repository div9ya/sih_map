import geopandas as gpd
from shapely.geometry import MultiPoint
from sklearn.cluster import DBSCAN
import numpy as np
import pickle

# --- Load incidents ---
print("📂 Loading incidents...")
incidents = gpd.read_file("synthetic_incidents.geojson").set_crs("EPSG:4326")

# Project to meters for DBSCAN
incidents_proj = incidents.to_crs(epsg=3857)
coords = np.array([[p.x, p.y] for p in incidents_proj.geometry])

# Run clustering
print("⚡ Running DBSCAN...")
db = DBSCAN(eps=5000, min_samples=3).fit(coords)
incidents["cluster"] = db.labels_

# Create hotspot polygons
print("📍 Creating hotspot polygons...")
hotspot_polys = []
for cluster_id in set(db.labels_):
    if cluster_id == -1:
        continue
    cluster_points = incidents[incidents["cluster"] == cluster_id].geometry
    poly = MultiPoint(cluster_points).buffer(0.05).convex_hull
    hotspot_polys.append({"cluster": cluster_id, "geometry": poly})

hotspots = gpd.GeoDataFrame(hotspot_polys, crs="EPSG:4326")

# Compute risk index
print("📊 Calculating risk scores...")
risk_scores = incidents.groupby("cluster").size().reset_index(name="INCIDENTS")
hotspots = hotspots.merge(risk_scores, on="cluster", how="left")
hotspots["RISK_INDEX"] = (hotspots["INCIDENTS"] / hotspots["INCIDENTS"].max()) * 10

# Save everything into pickle
print("💾 Saving to crime_data.pkl...")
with open("crime_data.pkl", "wb") as f:
    pickle.dump({"incidents": incidents, "hotspots": hotspots}, f)

print("✅ Done! Preprocessed data saved to crime_data.pkl")
