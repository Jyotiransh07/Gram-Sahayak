import httpx
from app.config import settings

BASE = "https://api.data.gov.in/resource/"

async def get_mandi_prices(commodity: str = "", state: str = "", district: str = "", market: str = "", limit: int = 30):
    if not settings.data_gov_api_key or "PASTE_YOUR" in settings.data_gov_api_key:
        raise RuntimeError("Add your data.gov.in API key to the DATA_GOV_API_KEY value in .env.")
    params = {
        "api-key": settings.data_gov_api_key,
        "format": "json",
        "limit": max(1, min(limit, 100)),
    }
    # The API accepts filters using the dataset's field names.
    for key, value in (("commodity", commodity), ("state", state), ("district", district), ("market", market)):
        if value.strip():
            params[f"filters[{key}]"] = value.strip()
    url = f"{BASE}{settings.mandi_resource_id}"
    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    records = payload.get("records", [])
    if not records:
        return {"records": [], "total": payload.get("total", 0), "message": "No matching mandi records were returned. Try a broader commodity, district or market."}
    cleaned = []
    for r in records:
        cleaned.append({
            "state": r.get("state", ""),
            "district": r.get("district", ""),
            "market": r.get("market", ""),
            "commodity": r.get("commodity", ""),
            "variety": r.get("variety", ""),
            "arrival_date": r.get("arrival_date", r.get("date", "")),
            "min_price": r.get("min_price", ""),
            "max_price": r.get("max_price", ""),
            "modal_price": r.get("modal_price", ""),
        })
    return {"records": cleaned, "total": payload.get("total", len(cleaned))}
