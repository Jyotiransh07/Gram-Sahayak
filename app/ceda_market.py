"""CEDA Agri Market Data adapter for Gram Sahayak.

API: https://api.ceda.ashoka.edu.in/v1
Key: Bearer token from CEDA_API_KEY (.env)
Only source-reported data; never fills missing prices with guesses.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import median
import time
import re

import requests
from . import config, db

BASE_URL = "https://api.ceda.ashoka.edu.in/v1"
SOURCE_URL = "https://ceda.ashoka.edu.in/agmarknet/"


class CedaError(RuntimeError):
    """Safe human-readable error for a CEDA lookup."""


def _normalize(s):
    return re.sub(r"\s+", " ", str(s or "").casefold()).strip()


ALIASES = {
    "प्याज": "onion", "प्याज़": "onion", "टमाटर": "tomato",
    "आलू": "potato", "गेहूं": "wheat", "गेहूँ": "wheat",
    "सोयाबीन": "soyabean", "soybean": "soyabean", "मक्का": "maize",
    "कपास": "cotton", "सरसों": "mustard", "धान": "paddy",
}


def _resolve(items, query, field, label):
    needle = ALIASES.get(_normalize(query), _normalize(query)) if label == "commodity" else _normalize(query)
    if not needle:
        raise CedaError(f"Please enter a {label} name.")
    # Exactly matching names are preferred; a unique partial match is allowed.
    exact = [item for item in items if _normalize(item.get(field)) == needle]
    if exact:
        return exact[0]
    partial = [item for item in items if needle in _normalize(item.get(field))]
    if len(partial) == 1:
        return partial[0]
    if partial:
        sample = ", ".join(str(i.get(field)) for i in partial[:6])
        raise CedaError(f"Ambiguous {label} '{query}'. Try one of: {sample}.")
    sample = ", ".join(str(i.get(field)) for i in items[:6])
    raise CedaError(f"No matching {label} for '{query}' in CEDA. Check the spelling. Examples: {sample}.")


class CedaClient:
    def __init__(self, api_key=None, session=None, base_url=BASE_URL):
        self.api_key = (api_key if api_key is not None else config.env("CEDA_API_KEY")).strip()
        if not self.api_key:
            raise CedaError("CEDA API key missing. Add CEDA_API_KEY=... to your project's .env file and restart FastAPI.")
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def call(self, method, endpoint, body=None):
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json",
                   "User-Agent": "GramSahayak/1.0 (non-commercial educational project)"}
        for attempt in range(2):
            try:
                response = self.session.request(method, self.base_url + endpoint,
                                                json=body if method == "POST" else None,
                                                headers=headers, timeout=(7, 22))
            except requests.Timeout as exc:
                if attempt == 0:
                    time.sleep(0.4)
                    continue
                raise CedaError("CEDA did not respond in time. Please try again shortly.") from exc
            except requests.RequestException as exc:
                raise CedaError("Unable to reach CEDA. Check internet access and the service's availability.") from exc
            status = response.status_code
            if status in (401, 403):
                raise CedaError(f"CEDA rejected this API key (HTTP {status}). Verify or renew CEDA_API_KEY.")
            if status == 429:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise CedaError("CEDA rate limit reached (HTTP 429). Please try again later.")
            if status in (500, 502, 503, 504):
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise CedaError(f"CEDA service is temporarily unavailable (HTTP {status}).")
            if status >= 400:
                raise CedaError(f"CEDA request failed (HTTP {status}). Check the selected dates and location.")
            try:
                result = response.json()
            except ValueError as exc:
                raise CedaError("CEDA returned a non-JSON response.") from exc
            if not isinstance(result, dict) or not isinstance(result.get("output"), dict):
                raise CedaError("Unexpected CEDA API response format (missing output envelope).")
            wrapper = result["output"]
            if wrapper.get("type") != "success":
                # Do not surface arbitrary upstream content or secret-bearing URLs.
                raise CedaError("CEDA did not return a successful result. Check the requested commodity and dates.")
            rows = wrapper.get("data", [])
            if not isinstance(rows, list):
                raise CedaError("CEDA returned an unexpected data format.")
            return rows
        raise CedaError("CEDA could not complete the request.")

    def commodities(self):
        cached = db.get_cache("ceda:reference:commodities", 7 * 86400)
        if cached is not None:
            return cached
        data = self.call("GET", "/agmarknet/commodities")
        if data:
            db.put_cache("ceda:reference:commodities", data)
        return data

    def geographies(self):
        cached = db.get_cache("ceda:reference:geographies", 7 * 86400)
        if cached is not None:
            return cached
        data = self.call("GET", "/agmarknet/geographies")
        if data:
            db.put_cache("ceda:reference:geographies", data)
        return data

    def markets(self, commodity_id, state_id, district_id):
        key = f"ceda:reference:markets:{commodity_id}:{state_id}:{district_id}"
        cached = db.get_cache(key, 7 * 86400)
        if cached is not None:
            return cached
        data = self.call("POST", "/agmarknet/markets", {
            "commodity_id": commodity_id, "state_id": state_id,
            "district_id": district_id, "indicator": "price"})
        db.put_cache(key, data)
        return data

    def prices(self, commodity, state, district="", from_date=None, to_date=None):
        today = date.today()
        to_date = to_date or today.isoformat()
        from_date = from_date or (today - timedelta(days=365)).isoformat()
        try:
            start = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date)
        except (TypeError, ValueError) as exc:
            raise CedaError("Use dates in YYYY-MM-DD format.") from exc
        if start > end:
            raise CedaError("From date must be before or equal to To date.")
        if end > today:
            raise CedaError("To date cannot be in the future.")
        if (end - start).days > 1095:
            raise CedaError("Select at most 3 years per search to keep requests manageable.")
        commodities = self.commodities()
        geos = self.geographies()
        commodity_item = _resolve(commodities, commodity, "commodity_name", "commodity")
        state_item = _resolve(geos, state, "census_state_name", "state")
        state_id = int(state_item["census_state_id"])
        commodity_id = int(commodity_item["commodity_id"])
        district_id = None
        district_name = None
        if district and district.strip():
            all_in_state = [g for g in geos if int(g.get("census_state_id", -1)) == state_id]
            found = _resolve(all_in_state, district, "census_district_name", "district")
            district_id = int(found["census_district_id"])
            district_name = str(found["census_district_name"])
        body = {"commodity_id": commodity_id, "state_id": state_id,
                "from_date": start.isoformat(), "to_date": end.isoformat()}
        if district_id is not None:
            body["district_id"] = [district_id]
        raw = self.call("POST", "/agmarknet/prices", body)
        geography_lookup = {(int(g.get("census_state_id", -1)), int(g.get("census_district_id", -1))):
                             str(g.get("census_district_name", "")) for g in geos}
        market_lookup = {}
        # Market metadata requires extra requests; only look it up for a specific district.
        if district_id is not None and raw:
            try:
                market_lookup = {int(m["market_id"]): str(m["market_name"])
                                 for m in self.markets(commodity_id, state_id, district_id)
                                 if m.get("market_id") is not None}
            except CedaError:
                # Price data is still useful without the optional name lookup.
                market_lookup = {}
        records = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            when = str(row.get("date", ""))[:10]
            try:
                date.fromisoformat(when)
                modal = float(row["modal_price"])
                low = float(row["min_price"])
                high = float(row["max_price"])
            except (ValueError, TypeError, KeyError):
                continue
            if modal <= 0 or low < 0 or high < 0:
                continue
            d_id, m_id = row.get("census_district_id"), row.get("market_id")
            try:
                d_id = int(d_id) if d_id is not None else None
                m_id = int(m_id) if m_id is not None else None
            except (ValueError, TypeError):
                d_id, m_id = None, None
            rec_district = geography_lookup.get((state_id, d_id), district_name or "All districts") if d_id is not None else "All districts"
            level = "market" if m_id is not None else ("district aggregate" if d_id is not None else "state aggregate")
            market_name = market_lookup.get(m_id, f"Market ID {m_id}") if m_id is not None else level.title()
            records.append({"date": when, "commodity": str(commodity_item["commodity_name"]),
                            "state": str(state_item["census_state_name"]), "district": rec_district,
                            "market": market_name, "min_price": low, "max_price": high,
                            "modal_price": modal, "level": level})
        records.sort(key=lambda r: (r["date"], r["district"], r["market"]), reverse=True)
        if not records:
            raise CedaError(f"CEDA reported no usable prices for {commodity} in {district or state} between {start} and {end}. Try a wider date range.")
        most_recent = records[0]["date"]
        latest_records = [r for r in records if r["date"] == most_recent]
        latest_median = median([r["modal_price"] for r in latest_records])
        return {"provider": "CEDA Agri Market Data (CEDA-AMD)", "source": SOURCE_URL,
                "attribution": "Centre for Economic Data & Analysis, Ashoka University; underlying AGMARKNET/DMI data",
                "source_as_of": most_recent, "latest_reported_date": most_recent,
                "price_unit": "INR per quintal", "commodity": str(commodity_item["commodity_name"]),
                "state": str(state_item["census_state_name"]), "district": district_name or "All districts",
                "from_date": start.isoformat(), "to_date": end.isoformat(),
                "record_count": len(records), "latest_day_record_count": len(latest_records),
                "latest_day_median_modal": latest_median,
                "records": records[:250], "cached": False,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "note": "Latest reported CEDA/AGMARKNET historical prices, not necessarily today's live mandi rates. "
                        "State/district aggregates are not individual mandi quotes."}
