# 🚲 Toronto Bike-Share Finder

A live, interactive Streamlit app that helps you find the nearest available
bike — or the nearest empty dock — in Toronto's Bike Share network, with
travel-time routing straight to your destination.

**🔗 Live demo:** https://your-app-name.streamlit.app

![Screenshot](docs/screenshot.png)

---

## Features

- **Live data** from Toronto's GBFS feed (bike availability, e-bike counts,
  dock capacity)
- **Geocoded address search** — type any street address in Toronto
- **Smart station selection** — nearest station matching your bike preference
  (mechanical, e-bike, or either)
- **Routing with travel time** — powered by OSRM
- **Interactive map** — color-coded station markers (green = plenty of bikes,
  yellow = few, red = none) with popups showing live counts
- **Live KPI dashboard** — total bikes, e-bikes, and available docks across
  the city

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

---

## Architecture

```
app.py       →  Streamlit UI: layout, sidebar, map builder, session state
helpers.py   →  API clients, data joins, geocoding, routing, station selection
```

- All external API calls are wrapped with error handling so the app degrades
  gracefully instead of crashing on network or rate-limit failures.
- Station data is cached for 60 seconds — fresh enough to be useful, but
  gentle on the public GBFS endpoint.

---

## Run Locally

```bash
git clone https://github.com/your-user/bike-share-app.git
cd bike-share-app

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

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (make sure `.streamlit/secrets.toml` is
   gitignored — **never commit API keys**).
2. Go to <https://share.streamlit.io> → **New app** → point it at your repo,
   branch `main`, main file `app.py`.
3. Under **Settings → Secrets**, paste:

   ```toml
   CARTO_API_KEY = "your_key_here"
   ```

4. Deploy. Test both **Rent** and **Return** flows end-to-end on the live URL
   before sharing it.

---

## Notes on Production

- The GBFS and OSRM public endpoints are fine for demos but are **not
  SLA-backed**. Expect occasional slowdowns or rate limits.
- For a real production deployment, host your own OSRM instance and add a
  server-side cache/queue in front of the GBFS feed.

---

## License

MIT @2026