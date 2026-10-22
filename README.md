# 🚲 Toronto Bike-Share Finder

![Python](https://img.shields.io/badge/python-3.11-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.39-red)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-live-success)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-name.streamlit.app)

A live, interactive Streamlit app that helps you find the nearest available
bike — or the nearest empty dock — in Toronto's Bike Share network, with
travel-time routing straight to your destination.

**🔗 Live demo:** https://your-app-name.streamlit.app

![Screenshot](docs/screenshot.png)

---

## Features

- **Live data** from Toronto's GBFS feed (bike availability, e-bike counts,
  dock capacity), refreshed every 60 seconds
- **Geocoded address search** — type any street address in Toronto
- **Smart station selection** — nearest station matching your bike preference
  (mechanical, e-bike, or either)
- **Routing with travel time** — powered by OSRM
- **Interactive map** — color-coded station markers (green = plenty of bikes,
  yellow = few, red = none) with popups showing live counts
- **5 nearest stations table** — distance-sorted table of the closest
  stations below the route map, with live bike / dock counts
- **Live KPI dashboard** — total bikes, e-bikes, and available docks across
  the city
- **Reset search** — one click to clear the current address and return to the
  default city view

---

## Tech Stack

| Layer      | Tool                                          |
|------------|-----------------------------------------------|
| Frontend   | Streamlit                                     |
| Maps       | Folium + CARTO basemaps                       |
| Data       | Toronto GBFS API (Bike Share Toronto)         |
| Geocoding  | geopy + Nominatim (OpenStreetMap)             |
| Routing    | OSRM public demo server                       |
| Caching    | `st.cache_data(ttl=60)`                       |
| Testing    | pytest                                        |

---

## Architecture

```
app.py             →  Streamlit UI: layout, sidebar, map builder, session state
helpers.py         →  API clients, data joins, geocoding, routing, station selection
streamlit_app.py   →  Shim entrypoint (delegates to app.py) for Streamlit Cloud
tests/             →  pytest suite for helpers
conftest.py        →  Adds project root to sys.path so tests can import helpers
```

- All external API calls are wrapped with error handling so the app degrades
  gracefully instead of crashing on network or rate-limit failures.
- Station data is cached for 60 seconds — fresh enough to be useful, but
  gentle on the public GBFS endpoint.
- A caption under the title surfaces the data source and refresh cadence:
  *"Live data · Toronto Bike Share GBFS · Refreshes every 60 seconds"*.

---

## Run Locally

```bash
git clone https://github.com/Arindam-18s/Toronto-BikeSharing-System---Using_StreamLit
cd Toronto-BikeSharing-System---Using_StreamLit

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

You'll need a free **CARTO API key** for the basemap tiles.

1. Sign up at <https://carto.com/developers/auth-api/>
2. Create `.streamlit/secrets.toml` in the project root:

```toml
CARTO_API_KEY = "your_key_here"
```

Then reload the app. If the key is missing, the app still runs but will warn
you and the map tiles may not render.

---

## Running Tests

```bash
pip install -r requirements.txt pytest
pytest tests/ -v
```

The suite covers station selection (bike + dock), marker color logic, and the
nearest-stations table sort. `conftest.py` at the project root adds the repo
to `sys.path` so `from helpers import ...` resolves correctly under pytest on
any OS.

Expected output:

```
tests/test_helpers.py::test_marker_color PASSED
tests/test_helpers.py::test_nearest_bike PASSED
tests/test_helpers.py::test_ebike_only PASSED
tests/test_helpers.py::test_nearest_dock PASSED
tests/test_helpers.py::test_no_ebikes_raises PASSED
tests/test_helpers.py::test_nearest_stations_table PASSED
========== 6 passed ==========
```

---

## Notes on Production

- The GBFS and OSRM public endpoints are fine for demos but are **not
  SLA-backed**. Expect occasional slowdowns or rate limits.
- For a real production deployment, host your own OSRM instance and add a
  server-side cache/queue in front of the GBFS feed.
- Nominatim's public geocoder has a strict rate limit (1 req/sec). For higher
  traffic, swap in a commercial geocoder or cache results.

---

## License

MIT © 2026 Arindam S