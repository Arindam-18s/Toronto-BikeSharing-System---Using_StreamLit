import streamlit as st
import folium
from streamlit_folium import folium_static
from helpers import (
    query_station_status,
    get_station_latlon,
    join_latlon,
    geocode,
    get_bike_availability,
    get_dock_availability,
    run_osrm,
    get_marker_color,
)

# ---------- Page config ----------
st.set_page_config(
    page_title="Toronto Bike-Share Finder",
    page_icon="🚲",
    layout="wide",
)

# ---------- Constants ----------
TORONTO_CENTER = [43.65306613746548, -79.38815311015]
STATION_URL = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status"
LATLON_URL = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"
DEFAULT_ZOOM_CITY = 13
DEFAULT_ZOOM_STREET = 16
MAP_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)

CARTO_API_KEY = st.secrets.get("CARTO_API_KEY", "")
if not CARTO_API_KEY:
    st.warning("CARTO_API_KEY not configured — map tiles may not load.", icon="⚠️")

TILES_URL = (
    f"https://basemaps.cartocdn.com/rastertiles/light_all/{{z}}/{{x}}/{{y}}.png"
    f"?key={CARTO_API_KEY}"
)


# ---------- Cached data fetch ----------
@st.cache_data(ttl=60, show_spinner="Fetching live bike-share data…")
def load_data():
    try:
        df1 = query_station_status(STATION_URL)
        df2 = get_station_latlon(LATLON_URL)
        return join_latlon(df1, df2)
    except Exception as e:
        st.error(f"Could not load bike-share data: {e}")
        return None


# ---------- Map builder ----------
def build_map(center, zoom, data, user_location=None, station_location=None,
              station_popup="", route_coords=None, route_tooltip=""):
    m = folium.Map(location=center, zoom_start=zoom, tiles=TILES_URL,
                   attr=MAP_ATTR, max_zoom=20)

    for _, row in data.iterrows():
        color = get_marker_color(row["num_bikes_available"])
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=2,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"Station ID: {row['station_id']}<br>"
                f"Total Bikes Available: {row['num_bikes_available']}<br>"
                f"Mechanical Bikes Available: {row['mechanical']}<br>"
                f"eBikes Available: {row['ebike']}",
                max_width=300,
            ),
        ).add_to(m)

    if user_location:
        folium.Marker(
            location=user_location,
            popup="You are here.",
            icon=folium.Icon(color="blue", icon="person", prefix="fa"),
        ).add_to(m)

    if station_location:
        folium.Marker(
            location=station_location,
            popup=station_popup,
            icon=folium.Icon(color="red", icon="bicycle", prefix="fa"),
        ).add_to(m)

    if route_coords:
        folium.PolyLine(locations=route_coords, color="blue", weight=5,
                        tooltip=route_tooltip).add_to(m)

    return m


# ---------- Header ----------
st.title("🚲 Toronto Bike-Share Finder")
st.markdown("Find the nearest available bike or dock in Toronto — live.")

# ---------- Data ----------
data = load_data()
if data is None or data.empty:
    st.stop()

# ---------- Metrics ----------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Bikes Available Now", int(data["num_bikes_available"].sum()))
    st.metric("E-Bikes Available Now", int(data["ebike"].sum()))
with col2:
    st.metric("Stations with Bikes", int((data["num_bikes_available"] > 0).sum()))
    st.metric("Stations with E-Bikes", int((data["ebike"] > 0).sum()))
with col3:
    st.metric("Stations with Empty Docks", int((data["num_docks_available"] > 0).sum()))

# ---------- Session state ----------
st.session_state.setdefault("iamhere", None)
st.session_state.setdefault("iamhere_to_return", None)

# ---------- Sidebar ----------
with st.sidebar:
    st.title("Your Dashboard")
    bike_method = st.selectbox(
        "Are you looking to Rent or Return a bike?",
        ("Rent", "Return"),
        index=None,
        placeholder="Select an option",
    )

    input_bike_modes = []
    input_street = ""
    input_street_return = ""

    if bike_method == "Rent":
        input_bike_modes = st.multiselect(
            "What kind of bike are you looking to rent?",
            ["ebike", "mechanical"],
        )
        st.header("Where are you located?")
        input_street = st.text_input("Street", "")
        input_city = st.text_input("City", "Toronto")
        input_country = st.text_input("Country", "Canada")

        if st.button("Find me a Bike", type="primary"):
            if not input_street.strip():
                st.error("Please enter a street address.")
            else:
                with st.spinner("Locating address…"):
                    loc = geocode(f"{input_street} {input_city} {input_country}")
                if not loc:
                    st.error("Address not found. Please check your input.")
                else:
                    st.session_state.iamhere = loc

    elif bike_method == "Return":
        st.header("Where are you located?")
        input_street_return = st.text_input("Street", "")
        input_city = st.text_input("City", "Toronto")
        input_country = st.text_input("Country", "Canada")

        if st.button("Find me a Dock", type="primary"):
            if not input_street_return.strip():
                st.error("Please enter a street address.")
            else:
                with st.spinner("Locating address…"):
                    loc = geocode(f"{input_street_return} {input_city} {input_country}")
                if not loc:
                    st.error("Address not found. Please check your input.")
                else:
                    st.session_state.iamhere_to_return = loc

# ---------- Map rendering ----------
iamhere = st.session_state.iamhere
iamhere_to_return = st.session_state.iamhere_to_return

if bike_method in ("Rent", "Return") and not iamhere and not iamhere_to_return:
    m = build_map(TORONTO_CENTER, DEFAULT_ZOOM_CITY, data)
    folium_static(m, width=1400)

elif bike_method == "Rent" and iamhere:
    try:
        with st.spinner("Finding the best bike for you…"):
            chosen_station = get_bike_availability(iamhere, data, input_bike_modes)
            coords, duration = run_osrm(chosen_station, iamhere)
    except Exception as e:
        st.error(f"Could not compute route: {e}")
        st.stop()

    m = build_map(
        center=iamhere,
        zoom=DEFAULT_ZOOM_STREET,
        data=data,
        user_location=iamhere,
        station_location=(chosen_station[1], chosen_station[2]),
        station_popup="Rent your bike here.",
        route_coords=coords,
        route_tooltip=f"It'll take you {duration} min to get here.",
    )
    folium_static(m, width=1400)
    with col3:
        st.metric(":green[Travel Time]", f"{duration} min")

elif bike_method == "Return" and iamhere_to_return:
    try:
        with st.spinner("Finding the best dock for you…"):
            chosen_station = get_dock_availability(iamhere_to_return, data)
            coords, duration = run_osrm(chosen_station, iamhere_to_return)
    except Exception as e:
        st.error(f"Could not compute route: {e}")
        st.stop()

    m = build_map(
        center=iamhere_to_return,
        zoom=DEFAULT_ZOOM_STREET,
        data=data,
        user_location=iamhere_to_return,
        station_location=(chosen_station[1], chosen_station[2]),
        station_popup="Return your bike here.",
        route_coords=coords,
        route_tooltip=f"It'll take you {duration} min to get here.",
    )
    folium_static(m, width=1400)
    with col3:
        st.metric(":green[Travel Time]", f"{duration} min")

# ---------- Bottom-right footer ----------
st.markdown(
    """
    <style>
    .footer-links a {
        color: #2563eb;
        text-decoration: none;
        font-weight: 600;
        margin: 0 4px;
    }
    .footer-links a:hover { text-decoration: underline; }
    </style>
    ---
    <div style='text-align:right; color:#888; font-size:13px; line-height:1.6;'>
        Designed &amp; developed by <strong><b>Arindam S</b></strong><br>
        <span class='footer-links'>
            <a href='https://github.com/Arindam-18s' target='_blank'>GitHub</a> ·
            <a href='https://www.linkedin.com/in/arindam-samadder' target='_blank'>LinkedIn</a> ·
            <a href='arindam.samadder18@gmail.com'>Email</a>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)