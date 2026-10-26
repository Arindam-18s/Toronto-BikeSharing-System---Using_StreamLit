import streamlit as st
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic

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

# ---------- Page config (must be the first Streamlit call) ----------
st.set_page_config(
    page_title="Toronto Bike-Sharing System",
    page_icon="🚲",
    layout="wide",
)
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Constants ----------
TORONTO_CENTER = [43.65306613746548, -79.38815311015]
STATION_URL = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status"
LATLON_URL = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"
DEFAULT_ZOOM_CITY = 13
DEFAULT_ZOOM_STREET = 16
MAP_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">Arindam</a> '
    'S <a href="https://carto.com/attributions">@Sept-2026</a>'
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


# ---------- Map builder (single source of truth) ----------
def build_map(
    center,
    zoom,
    data,
    user_location=None,
    station_location=None,
    station_popup="",
    route_coords=None,
    route_tooltip="",
):
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=TILES_URL,
        attr=MAP_ATTR,
        max_zoom=20,
    )

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
        folium.PolyLine(
            locations=route_coords,
            color="blue",
            weight=5,
            tooltip=route_tooltip,
        ).add_to(m)
    return m

# ---------- Nearest stations helper ----------
def nearest_stations_table(df, origin, n=5):
    """Return the n nearest stations to `origin` as a display-ready DataFrame."""
    work = df.copy()
    work["distance_km"] = work.apply(
        lambda row: geodesic(origin, (row["lat"], row["lon"])).km, axis=1
    )
    work = work.sort_values("distance_km").head(n)

    cols = ["station_id", "name", "distance_km",
            "num_bikes_available", "ebike", "mechanical",
            "num_docks_available"]
    # Guard: drop 'name' if it doesn't exist in the data
    cols = [c for c in cols if c in work.columns]

    rename_map = {
        "station_id": "Station ID",
        "name": "Station Name",
        "distance_km": "Distance (km)",
        "num_bikes_available": "Bikes",
        "ebike": "E-Bikes",
        "mechanical": "Mechanical",
        "num_docks_available": "Empty Docks",
    }
    result = work[cols].rename(columns=rename_map).reset_index(drop=True)

    if "Distance (km)" in result.columns:
        result["Distance (km)"] = result["Distance (km)"].round(2)
    return result

# ---------- Footer ----------
def render_footer():
    st.markdown(
        """
        <style>
        .footer-links a {
            color: #2563eb; text-decoration: none;
            font-weight: 600; margin: 0 4px;
        }
        .footer-links a:hover { text-decoration: underline; }
        </style>
        ---
        <div style='text-align:right; color:#888; font-size:13px; line-height:1.6;'>
            Designed &amp; developed by <strong><b>Arindam S</b></strong><br>
            <span class='footer-links'>
                <a href='https://github.com/YOUR_USERNAME' target='_blank'>GitHub</a> ·
                <a href='https://www.linkedin.com/in/YOUR_HANDLE' target='_blank'>LinkedIn</a> ·
                <a href='mailto:you@example.com'>Email</a>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Header ----------
st.title("🚲 Toronto Bike-Sharing System - Dashboard")
st.caption("Live data · Toronto Bike Share GBFS · Refreshes every 60 seconds")

# ---------- Data ----------
data = load_data()
if data is None or data.empty:
    st.stop()

# ---------- Top metrics ----------
# col1, col2, col3 = st.columns(3)
# with col1:
#     st.metric("Bikes Available Now", int(data["num_bikes_available"].sum()))
#     st.metric("E-Bikes Available Now", int(data["ebike"].sum()))
# with col2:
#     st.metric("Stations with Bikes", int((data["num_bikes_available"] > 0).sum()))
#     st.metric("Stations with E-Bikes", int((data["ebike"] > 0).sum()))
# with col3:
#     st.metric("Stations with Empty Docks",
#               int((data["num_docks_available"] > 0).sum()))

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

        find_col, reset_col = st.columns([2, 1])
        with find_col:
            find_clicked = st.button(
                "Find me a Bike", type="primary", use_container_width=True
            )
        with reset_col:
            reset_clicked = st.button(
                "🔄 Reset", use_container_width=True
            )

        if find_clicked:
            if not input_street.strip():
                st.error("Please enter a street address.")
            else:
                with st.spinner("Locating address…"):
                    loc = geocode(
                        f"{input_street} {input_city} {input_country}"
                    )
                if not loc:
                    st.error("Address not found. Please check your input.")
                else:
                    st.session_state.iamhere = loc

        if reset_clicked:
            st.session_state.iamhere = None
            st.session_state.iamhere_to_return = None
            st.rerun()

    elif bike_method == "Return":
        st.header("Where are you located?")
        input_street_return = st.text_input("Street", "")
        input_city = st.text_input("City", "Toronto")
        input_country = st.text_input("Country", "Canada")

        find_col, reset_col = st.columns([2, 1])
        with find_col:
            find_clicked = st.button(
                "Find me a Dock", type="primary", use_container_width=True
            )
        with reset_col:
            reset_clicked = st.button(
                "🔄 Reset", use_container_width=True
            )

        if find_clicked:
            if not input_street_return.strip():
                st.error("Please enter a street address.")
            else:
                with st.spinner("Locating address…"):
                    loc = geocode(
                        f"{input_street_return} {input_city} {input_country}"
                    )
                if not loc:
                    st.error("Address not found. Please check your input.")
                else:
                    st.session_state.iamhere_to_return = loc

        if reset_clicked:
            st.session_state.iamhere = None
            st.session_state.iamhere_to_return = None
            st.rerun()

# # ---------- Map rendering ----------
# iamhere = st.session_state.iamhere
# iamhere_to_return = st.session_state.iamhere_to_return

# # Default Toronto view (no address entered yet)
# if not iamhere and not iamhere_to_return:
#     m = build_map(TORONTO_CENTER, DEFAULT_ZOOM_CITY, data)
#     folium_static(m, width=1400)

#     if bike_method is None:
#         st.info(
#             "👈 Select **Rent** or **Return** in the sidebar, then enter "
#             "your street address to find the nearest station.",
#             icon="🚲",
#         )

# # Rent flow
# elif bike_method == "Rent" and iamhere:
#     try:
#         with st.spinner("Finding the best bike for you…"):
#             chosen_station = get_bike_availability(iamhere, data, input_bike_modes)
#             coords, duration = run_osrm(chosen_station, iamhere)
#     except Exception as e:
#         st.error(f"Could not compute route: {e}")
#         st.stop()

#     m = build_map(
#         center=iamhere,
#         zoom=DEFAULT_ZOOM_STREET,
#         data=data,
#         user_location=iamhere,
#         station_location=(chosen_station[1], chosen_station[2]),
#         station_popup="Rent your bike here.",
#         route_coords=coords,
#         route_tooltip=f"It'll take you {duration} min to get here.",
#     )
#     folium_static(m, width=1400)
#     with col3:
#         st.metric(":green[Travel Time]", f"{duration} min")

#     st.subheader("📍 5 Nearest Stations")
#     st.dataframe(
#         nearest_stations_table(data, iamhere),
#         use_container_width=True,
#         hide_index=True,
#     )

# # Return flow
# elif bike_method == "Return" and iamhere_to_return:
#     try:
#         with st.spinner("Finding the best dock for you…"):
#             chosen_station = get_dock_availability(iamhere_to_return, data)
#             coords, duration = run_osrm(chosen_station, iamhere_to_return)
#     except Exception as e:
#         st.error(f"Could not compute route: {e}")
#         st.stop()

#     m = build_map(
#         center=iamhere_to_return,
#         zoom=DEFAULT_ZOOM_STREET,
#         data=data,
#         user_location=iamhere_to_return,
#         station_location=(chosen_station[1], chosen_station[2]),
#         station_popup="Return your bike here.",
#         route_coords=coords,
#         route_tooltip=f"It'll take you {duration} min to get here.",
#     )
#     folium_static(m, width=1400)
#     with col3:
#         st.metric(":green[Travel Time]", f"{duration} min")

#     st.subheader("📍 5 Nearest Stations")
#     st.dataframe(
#         nearest_stations_table(data, iamhere_to_return),
#         use_container_width=True,
#         hide_index=True,
#     )

# # ---------- Footer ----------
# render_footer()








# ---------- Top Metrics + Map Layout ----------
# Create two columns: Left for metrics (smaller), Right for map (larger)

# iamhere = st.session_state.iamhere
# iamhere_to_return = st.session_state.iamhere_to_return
# metric_col, map_col = st.columns([1, 3], gap="large")

# with metric_col:
#     st.subheader("Network Status")
    
#     # Group Rent metrics
#     st.metric("Bikes Available", f"{int(data['num_bikes_available'].sum()):,}")
#     st.metric("E-Bikes Available", f"{int(data['ebike'].sum()):,}")
    
#     st.divider()
    
#     # Group Station metrics
#     st.metric("Stations with Bikes", f"{int((data['num_bikes_available'] > 0).sum()):,}")
#     st.metric("Stations with E-Bikes", f"{int((data['ebike'] > 0).sum()):,}")
#     st.metric("Stations with Empty Docks", f"{int((data['num_docks_available'] > 0).sum()):,}")

# with map_col:
#     st.subheader("Live Map")
    
#     # Default Toronto view
#     if not iamhere and not iamhere_to_return:
#         m = build_map(TORONTO_CENTER, DEFAULT_ZOOM_CITY, data)
#         # use_container_width dynamically fills the wide column
#         folium_static(m, height=400) 

#         if bike_method is None:
#             st.info(
#                 "👈 Select **Rent** or **Return** in the sidebar, then enter "
#                 "your street address to find the nearest station.",
#                 icon="🚲",
#             )

#     # Rent flow
#     elif bike_method == "Rent" and iamhere:
#         try:
#             with st.spinner("Finding the best bike for you…"):
#                 chosen_station = get_bike_availability(iamhere, data, input_bike_modes)
#                 coords, duration = run_osrm(chosen_station, iamhere)
#         except Exception as e:
#             st.error(f"Could not compute route: {e}")
#             st.stop()

#         m = build_map(
#             center=iamhere,
#             zoom=DEFAULT_ZOOM_STREET,
#             data=data,
#             user_location=iamhere,
#             station_location=(chosen_station[1], chosen_station[2]),
#             station_popup="Rent your bike here.",
#             route_coords=coords,
#             route_tooltip=f"It'll take you {duration} min to get here.",
#         )
#         folium_static(m, height=400)
        
#         st.success(f"**Travel Time:** {duration} min to the nearest station.")
        
#         st.subheader("📍 5 Nearest Stations")
#         st.dataframe(
#             nearest_stations_table(data, iamhere),
#             use_container_width=True,
#             hide_index=True,
#         )

#     # Return flow
#     elif bike_method == "Return" and iamhere_to_return:
#         try:
#             with st.spinner("Finding the best dock for you…"):
#                 chosen_station = get_dock_availability(iamhere_to_return, data)
#                 coords, duration = run_osrm(chosen_station, iamhere_to_return)
#         except Exception as e:
#             st.error(f"Could not compute route: {e}")
#             st.stop()

#         m = build_map(
#             center=iamhere_to_return,
#             zoom=DEFAULT_ZOOM_STREET,
#             data=data,
#             user_location=iamhere_to_return,
#             station_location=(chosen_station[1], chosen_station[2]),
#             station_popup="Return your bike here.",
#             route_coords=coords,
#             route_tooltip=f"It'll take you {duration} min to get here.",
#         )
#         folium_static(m, height=400)
        
#         st.success(f"**Travel Time:** {duration} min to the nearest dock.")
        
#         st.subheader("📍 5 Nearest Stations")
#         st.dataframe(
#             nearest_stations_table(data, iamhere_to_return),
#             use_container_width=True,
#             hide_index=True,
#         )












# with map_col:
#     # Create tabs so the user immediately sees both options
#     tab1, tab2 = st.tabs(["🗺️ Live Map", "📋 Station Data"])
    
#     with tab1:
#         # Default Toronto view
#         if not iamhere and not iamhere_to_return:
#             m = build_map(TORONTO_CENTER, DEFAULT_ZOOM_CITY, data)
#             folium_static(m, height=450) 

#             if bike_method is None:
#                 st.info(
#                     "👈 Select **Rent** or **Return** in the sidebar, then enter "
#                     "your street address to find the nearest station.",
#                     icon="🚲",
#                 )

#         # Rent flow
#         elif bike_method == "Rent" and iamhere:
#             try:
#                 with st.spinner("Finding the best bike for you…"):
#                     chosen_station = get_bike_availability(iamhere, data, input_bike_modes)
#                     coords, duration = run_osrm(chosen_station, iamhere)
#             except Exception as e:
#                 st.error(f"Could not compute route: {e}")
#                 st.stop()

#             m = build_map(
#                 center=iamhere,
#                 zoom=DEFAULT_ZOOM_STREET,
#                 data=data,
#                 user_location=iamhere,
#                 station_location=(chosen_station[1], chosen_station[2]),
#                 station_popup="Rent your bike here.",
#                 route_coords=coords,
#                 route_tooltip=f"It'll take you {duration} min to get here.",
#             )
#             folium_static(m, height=450)
#             st.success(f"**Travel Time:** {duration} min to the nearest station.")

#         # Return flow
#         elif bike_method == "Return" and iamhere_to_return:
#             try:
#                 with st.spinner("Finding the best dock for you…"):
#                     chosen_station = get_dock_availability(iamhere_to_return, data)
#                     coords, duration = run_osrm(chosen_station, iamhere_to_return)
#             except Exception as e:
#                 st.error(f"Could not compute route: {e}")
#                 st.stop()

#             m = build_map(
#                 center=iamhere_to_return,
#                 zoom=DEFAULT_ZOOM_STREET,
#                 data=data,
#                 user_location=iamhere_to_return,
#                 station_location=(chosen_station[1], chosen_station[2]),
#                 station_popup="Return your bike here.",
#                 route_coords=coords,
#                 route_tooltip=f"It'll take you {duration} min to get here.",
#             )
#             folium_static(m, height=450)
#             st.success(f"**Travel Time:** {duration} min to the nearest dock.")

#     with tab2:
#         st.subheader("📍 Nearest Stations")
#         # Show nearest stations if a location is set, otherwise show a prompt
#         if bike_method == "Rent" and iamhere:
#             st.dataframe(
#                 nearest_stations_table(data, iamhere),
#                 use_container_width=True,
#                 hide_index=True,
#             )
#         elif bike_method == "Return" and iamhere_to_return:
#             st.dataframe(
#                 nearest_stations_table(data, iamhere_to_return),
#                 use_container_width=True,
#                 hide_index=True,
#             )
#         else:
#             st.info("Enter a location in the sidebar to see the nearest stations.")

# ---------- Footer ----------
# render_footer()








# ---------- Main Layout: Metrics Left, View Toggle Right ----------
iamhere = st.session_state.iamhere
iamhere_to_return = st.session_state.iamhere_to_return

# Create two columns: Left for metrics (narrow), Right for the view (wide)
metric_col, view_col = st.columns([1, 3], gap="large")

with metric_col:
    st.subheader("Network Status")
    
    # Group Rent metrics
    st.metric("Bikes Available", f"{int(data['num_bikes_available'].sum()):,}")
    st.metric("E-Bikes Available", f"{int(data['ebike'].sum()):,}")
    
    st.divider()
    
    # Group Station metrics
    st.metric("Stations with Bikes", f"{int((data['num_bikes_available'] > 0).sum()):,}")
    st.metric("Stations with E-Bikes", f"{int((data['ebike'] > 0).sum()):,}")
    st.metric("Stations with Empty Docks", f"{int((data['num_docks_available'] > 0).sum()):,}")

with view_col:
    # The Apple-style centered toggle
    view_toggle = st.segmented_control(
        "View Mode",
        options=["🗺️ Visualize Through Map", "📋 Nearest Stations Data"],
        default="🗺️ Visualize Through Map",
        label_visibility="collapsed", # Hides the label so it just looks like a clean toggle
    )

    # If Map is selected
    if view_toggle == "🗺️ Visualize Through Map":
        # Default Toronto view
        if not iamhere and not iamhere_to_return:
            m = build_map(TORONTO_CENTER, DEFAULT_ZOOM_CITY, data)
            folium_static(m, height=500) 

            if bike_method is None:
                st.info(
                    "👈 Select **Rent** or **Return** in the sidebar, then enter "
                    "your street address to find the nearest station.",
                    icon="🚲",
                )

        # Rent flow
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
            folium_static(m, height=500)
            st.success(f"**Travel Time:** {duration} min to the nearest station.")

        # Return flow
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
            folium_static(m, height=500)
            st.success(f"**Travel Time:** {duration} min to the nearest dock.")

    # If Data is selected
    elif view_toggle == "📋 Nearest Stations Data":
        st.subheader("📍 Nearest Stations")
        
        if bike_method == "Rent" and iamhere:
            st.dataframe(
                nearest_stations_table(data, iamhere),
                use_container_width=True,
                hide_index=True,
            )
        elif bike_method == "Return" and iamhere_to_return:
            st.dataframe(
                nearest_stations_table(data, iamhere_to_return),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Enter a location in the sidebar to see the nearest stations.")

# ---------- Footer ----------
render_footer()

