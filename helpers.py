import urllib.request
import json
import datetime as dt
import requests
import pandas as pd
import streamlit as st
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

@st.cache_data(ttl=60)
def query_station_status(url):
    with urllib.request.urlopen(url, timeout=10) as data_url:
        data = json.loads(data_url.read().decode())

    df = pd.DataFrame(data["data"]["stations"])
    df = df[df.is_renting == 1]
    df = df[df.is_returning == 1]
    df = df.drop_duplicates(["station_id", "last_reported"])

    df["last_reported"] = df["last_reported"].map(
        lambda x: dt.datetime.fromtimestamp(x, tz=dt.timezone.utc)
    )
    df["time"] = data["last_updated"]
    df["time"] = df["time"].map(
        lambda x: dt.datetime.fromtimestamp(x, tz=dt.timezone.utc)
    )
    df = df.set_index("time")

    df = pd.concat([df, df["num_bikes_available_types"].apply(pd.Series)], axis=1)
    return df


def get_station_latlon(url):
    with urllib.request.urlopen(url, timeout=10) as data_url:
        latlon = json.loads(data_url.read().decode())
    return pd.DataFrame(latlon["data"]["stations"])


def join_latlon(df1, df2):
    df1 = df1.copy()
    df2 = df2.copy()
    df1["station_id"] = df1["station_id"].astype(str)
    df2["station_id"] = df2["station_id"].astype(str)

    df = df1.merge(df2[["station_id", "lat", "lon"]], how="left", on="station_id")
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    return df


def get_marker_color(num_bikes_available):
    if num_bikes_available > 3:
        return "green"
    elif 0 < num_bikes_available <= 3:
        return "yellow"
    return "red"


def geocode(address):
    geolocator = Nominatim(user_agent="toronto_bikeshare_arindam-18s_v1.1")
    try:
        location = geolocator.geocode(address, timeout=10)
    except Exception:
        return None
    if location is None:
        return None
    return (location.latitude, location.longitude)


def _closest_station(df):
    """Return [station_id, lat, lon] for the closest row (assumes 'distance' col exists)."""
    idx = df["distance"].idxmin()
    row = df.loc[idx]
    return [row["station_id"], row["lat"], row["lon"]]


def get_bike_availability(latlon, df, input_bike_modes):
    """
    latlon: (lat, lon)
    input_bike_modes: [] (both) | ["ebike"] | ["mechanical"] | both
    returns [station_id, lat, lon] of nearest matching station
    """
    df = df.copy()
    df["distance"] = df.apply(
        lambda row: geodesic(latlon, (row["lat"], row["lon"])).km, axis=1
    )

    # No preference or both selected -> any bike
    if len(input_bike_modes) == 0 or len(input_bike_modes) == 2:
        df = df.loc[(df["ebike"] > 0) | (df["mechanical"] > 0)]
    else:
        mode = input_bike_modes[0]  # "ebike" or "mechanical"
        df = df.loc[df[mode] > 0]

    if df.empty:
        raise ValueError("No stations matching your bike preference were found.")

    return _closest_station(df)


def get_dock_availability(latlon, df):
    df = df.copy()
    df["distance"] = df.apply(
        lambda row: geodesic(latlon, (row["lat"], row["lon"])).km, axis=1
    )
    df = df.loc[df["num_docks_available"] > 0]

    if df.empty:
        raise ValueError("No stations with available docks were found.")

    return _closest_station(df)


def run_osrm(chosen_station, iamhere):
    """chosen_station: [station_id, lat, lon]; iamhere: (lat, lon). Returns (coords, duration_min)."""
    start = f"{iamhere[1]},{iamhere[0]}"
    end = f"{chosen_station[2]},{chosen_station[1]}"
    url = (
        f"https://router.project-osrm.org/route/v1/driving/{start};{end}"
        f"?geometries=geojson"
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    routejson = r.json()

    if not routejson.get("routes"):
        raise ValueError("No route could be computed by OSRM.")

    coordinates = [
        [coord[1], coord[0]]  # flip [lon, lat] -> [lat, lon]
        for coord in routejson["routes"][0]["geometry"]["coordinates"]
    ]
    duration = round(routejson["routes"][0]["duration"] / 60, 1)
    return coordinates, duration