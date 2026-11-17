import httpx

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

async def get_weather(place: str):
    if not place.strip():
        raise ValueError("Please provide a city, town or village name.")
    async with httpx.AsyncClient(timeout=30) as client:
        geo_resp = await client.get(GEO_URL, params={"name": place, "count": 1, "language": "en", "format": "json"})
        geo_resp.raise_for_status()
        results = geo_resp.json().get("results", [])
        if not results:
            raise ValueError(f"Could not find location '{place}'. Try a nearby town or district.")
        loc = results[0]
        params = {
            "latitude": loc["latitude"], "longitude": loc["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": "auto", "forecast_days": 7,
        }
        wx_resp = await client.get(FORECAST_URL, params=params)
        wx_resp.raise_for_status()
        data = wx_resp.json()
    return {
        "location": ", ".join(x for x in [loc.get("name"), loc.get("admin1"), loc.get("country")] if x),
        "current": data.get("current", {}),
        "daily": data.get("daily", {}),
        "timezone": data.get("timezone", ""),
        "source": "Open-Meteo",
    }
