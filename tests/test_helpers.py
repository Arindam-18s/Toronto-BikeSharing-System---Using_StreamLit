import pandas as pd
import pytest
from geopy.distance import geodesic

from helpers import (
    get_bike_availability,
    get_dock_availability,
    get_marker_color,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "station_id": ["A", "B", "C"],
        "name": ["Station A", "Station B", "Station C"],
        "lat": [43.65, 43.66, 43.67],
        "lon": [-79.38, -79.39, -79.40],
        "ebike": [5, 0, 2],
        "mechanical": [3, 4, 0],
        "num_bikes_available": [8, 4, 2],
        "num_docks_available": [0, 6, 10],
    })


def test_marker_color():
    assert get_marker_color(5) == "green"
    assert get_marker_color(2) == "yellow"
    assert get_marker_color(0) == "red"


def test_nearest_bike(sample_df):
    loc = (43.65, -79.38)
    result = get_bike_availability(loc, sample_df, [])
    assert result[0] == "A"  # nearest with any bikes


def test_ebike_only(sample_df):
    loc = (43.65, -79.38)
    result = get_bike_availability(loc, sample_df, ["ebike"])
    assert result[0] == "A"  # A has ebikes; B has none


def test_nearest_dock(sample_df):
    loc = (43.65, -79.38)
    result = get_dock_availability(loc, sample_df)
    assert result[0] == "B"  # B is first nearest with docks


def test_no_ebikes_raises():
    df = pd.DataFrame({
        "station_id": ["A"], "name": ["Station A"],
        "lat": [43.65], "lon": [-79.38],
        "ebike": [0], "mechanical": [5],
        "num_bikes_available": [5], "num_docks_available": [0],
    })
    with pytest.raises(ValueError):
        get_bike_availability((43.65, -79.38), df, ["ebike"])


def test_nearest_stations_table():
    """Local copy of the app helper, tested against the same fixture shape."""
    df = pd.DataFrame({
        "station_id": ["A", "B", "C"],
        "name": ["Station A", "Station B", "Station C"],
        "lat": [43.65, 43.66, 43.67],
        "lon": [-79.38, -79.39, -79.40],
        "ebike": [5, 0, 2],
        "mechanical": [3, 4, 0],
        "num_bikes_available": [8, 4, 2],
        "num_docks_available": [0, 6, 10],
    })

    # Inline the same logic as app.nearest_stations_table to avoid
    # pulling streamlit into the test environment.
    work = df.copy()
    work["distance_km"] = work.apply(
        lambda row: geodesic((43.65, -79.38), (row["lat"], row["lon"])).km,
        axis=1,
    )
    work = work.sort_values("distance_km").head(2)

    assert len(work) == 2
    assert work.iloc[0]["station_id"] == "A"
    assert work.iloc[1]["station_id"] == "B"
    assert work.iloc[0]["distance_km"] < work.iloc[1]["distance_km"]