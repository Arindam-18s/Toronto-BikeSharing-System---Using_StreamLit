import pandas as pd
import pytest
from helpers import get_bike_availability, get_dock_availability, get_marker_color


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "station_id": ["A", "B", "C"],
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
    assert result[0] == "A"   # nearest with bikes


def test_ebike_only(sample_df):
    loc = (43.65, -79.38)
    result = get_bike_availability(loc, sample_df, ["ebike"])
    assert result[0] == "A"   # A has ebikes; B has none


def test_nearest_dock(sample_df):
    loc = (43.65, -79.38)
    result = get_dock_availability(loc, sample_df)
    assert result[0] == "B"   # B is first nearest with docks


def test_no_ebikes_raises():
    df = pd.DataFrame({
        "station_id": ["A"], "lat": [43.65], "lon": [-79.38],
        "ebike": [0], "mechanical": [5],
        "num_bikes_available": [5], "num_docks_available": [0],
    })
    with pytest.raises(ValueError):
        get_bike_availability((43.65, -79.38), df, ["ebike"])