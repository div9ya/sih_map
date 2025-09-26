# from flask import Flask, request
# import geopandas as gpd
# from shapely.geometry import Point, MultiPoint
# from sklearn.cluster import DBSCAN
# import numpy as np
# import folium
# import io

# app = Flask(__name__)

# # --- Load incidents ---
# incidents = gpd.read_file("synthetic_incidents.geojson").set_crs("EPSG:4326")
# incidents_proj = incidents.to_crs(epsg=3857)
# coords = np.array([[p.x, p.y] for p in incidents_proj.geometry])
# db = DBSCAN(eps=5000, min_samples=3).fit(coords)
# incidents["cluster"] = db.labels_

# hotspot_polys = []
# for cluster_id in set(db.labels_):
#     if cluster_id == -1:
#         continue
#     cluster_points = incidents[incidents["cluster"] == cluster_id].geometry
#     poly = MultiPoint(cluster_points).buffer(0.05).convex_hull
#     hotspot_polys.append({"cluster": cluster_id, "geometry": poly})

# hotspots = gpd.GeoDataFrame(hotspot_polys, crs="EPSG:4326")
# risk_scores = incidents.groupby("cluster").size().reset_index(name="INCIDENTS")
# hotspots = hotspots.merge(risk_scores, on="cluster", how="left")
# hotspots["RISK_INDEX"] = (hotspots["INCIDENTS"] / hotspots["INCIDENTS"].max()) * 10


# def check_user_location(lat, lon):
#     user_point = Point(lon, lat)
#     for _, row in hotspots.iterrows():
#         if row.geometry.contains(user_point):
#             return row["cluster"], row["RISK_INDEX"]

#     incidents_proj = incidents.to_crs(epsg=3857)
#     user_point_proj = gpd.GeoSeries([user_point], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
#     incidents_proj['distance_to_user'] = incidents_proj.geometry.distance(user_point_proj)
#     min_dist_meters = incidents_proj['distance_to_user'].min()

#     C, k = 10000, 1000
#     risk = C / (min_dist_meters + k)
#     risk = min(round(risk, 2), 10)

#     return -1, risk


# @app.route("/get_risk", methods=["GET"])
# def get_risk():
#     lat = request.args.get("lat", type=float)
#     lon = request.args.get("lon", type=float)

#     if lat is None or lon is None:
#         return "<h3>Please provide ?lat=..&lon=..</h3>"

#     cluster, risk = check_user_location(lat, lon)

#     m = folium.Map(location=[lat, lon], zoom_start=8)

#     # Hotspots
#     for _, row in hotspots.iterrows():
#         folium.GeoJson(
#             row.geometry,
#             style_function=lambda x, col="red" if row["RISK_INDEX"] >= 7 else "orange" if row["RISK_INDEX"] >= 4 else "green": {
#                 "fillColor": col,
#                 "color": "black",
#                 "weight": 1,
#                 "fillOpacity": 0.4
#             },
#             tooltip=f"Cluster {row['cluster']} - Risk: {row['RISK_INDEX']:.2f}"
#         ).add_to(m)

#     # Incidents
#     for _, row in incidents.iterrows():
#         folium.CircleMarker(
#             location=[row.geometry.y, row.geometry.x],
#             radius=2,
#             color="blue",
#             fill=True,
#             fill_opacity=0.6
#         ).add_to(m)

#     # User marker
#     folium.Marker(
#         location=[lat, lon],
#         popup=f"📍 User Risk: {risk:.2f} (Cluster {cluster})",
#         icon=folium.Icon(color="red" if risk > 7 else "green")
#     ).add_to(m)

#     # Render map as HTML response
#     return m._repr_html_()


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)


from flask import Flask, request
import geopandas as gpd
from shapely.geometry import Point
import folium
import pickle

app = Flask(__name__)

# --- Load preprocessed data ---
print("📂 Loading preprocessed data...")
with open("crime_data.pkl", "rb") as f:
    data = pickle.load(f)

incidents = data["incidents"]
hotspots = data["hotspots"]
print("✅ Data loaded successfully!")


def check_user_location(lat, lon):
    user_point = Point(lon, lat)

    # Case 1: User inside hotspot
    for _, row in hotspots.iterrows():
        if row.geometry.contains(user_point):
            return row["cluster"], row["RISK_INDEX"]

    # Case 2: Calculate risk based on nearest incident
    incidents_proj = incidents.to_crs(epsg=3857)
    user_point_proj = gpd.GeoSeries([user_point], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
    incidents_proj['distance_to_user'] = incidents_proj.geometry.distance(user_point_proj)
    min_dist_meters = incidents_proj['distance_to_user'].min()

    C, k = 10000, 1000
    risk = C / (min_dist_meters + k)
    risk = min(round(risk, 2), 10)

    return -1, risk


@app.route("/get_risk", methods=["GET"])
def get_risk():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if lat is None or lon is None:
        return "<h3>❌ Please provide ?lat=..&lon=..</h3>"

    cluster, risk = check_user_location(lat, lon)

    # Create Folium map
    m = folium.Map(location=[lat, lon], zoom_start=8)

    # Hotspots
    for _, row in hotspots.iterrows():
        folium.GeoJson(
            row.geometry,
            style_function=lambda x, col="red" if row["RISK_INDEX"] >= 7 else "orange" if row["RISK_INDEX"] >= 4 else "green": {
                "fillColor": col,
                "color": "black",
                "weight": 1,
                "fillOpacity": 0.4
            },
            tooltip=f"Cluster {row['cluster']} - Risk: {row['RISK_INDEX']:.2f}"
        ).add_to(m)

    # Incidents
    for _, row in incidents.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=2,
            color="blue",
            fill=True,
            fill_opacity=0.6
        ).add_to(m)

    # User marker
    folium.Marker(
        location=[lat, lon],
        popup=f"📍 User Risk: {risk:.2f} (Cluster {cluster})",
        icon=folium.Icon(color="red" if risk > 7 else "green")
    ).add_to(m)

    return m._repr_html_()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
