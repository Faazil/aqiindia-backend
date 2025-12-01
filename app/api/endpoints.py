# app/api/endpoints.py
from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

router = APIRouter()

OPENAQ_BASE = "https://api.openaq.org/v3"

PM25_BREAKPOINTS = [
    (0.0, 30.0, 0, 50),
    (30.0, 60.0, 51, 100),
    (60.0, 90.0, 101, 200),
    (90.0, 120.0, 201, 300),
    (120.0, 250.0, 301, 400),
    (250.0, 350.0, 401, 500),
    (350.0, 500.0, 501, 999),
]
PM10_BREAKPOINTS = [
    (0.0, 50.0, 0, 50),
    (50.0, 100.0, 51, 100),
    (100.0, 250.0, 101, 200),
    (250.0, 350.0, 201, 300),
    (350.0, 430.0, 301, 400),
    (430.0, 500.0, 401, 500),
    (500.0, 1000.0, 501, 999),
]


def linear_interpolate(C: float, bp: Tuple[float, float, int, int]) -> Optional[float]:
    C_low, C_high, I_low, I_high = bp
    if C is None:
        return None
    if C_low <= C <= C_high:
        span_C = (C_high - C_low)
        if span_C == 0:
            return float(I_low)
        slope = (I_high - I_low) / span_C
        I = slope * (C - C_low) + I_low
        return I
    return None


def get_subindex(conc: Optional[float], breakpoints: List[Tuple[float, float, int, int]]) -> Optional[int]:
    if conc is None:
        return None
    for bp in breakpoints:
        val = linear_interpolate(conc, bp)
        if val is not None:
            return int(round(val))
    # if above highest defined breakpoint, extrapolate using last interval
    if conc > breakpoints[-1][1]:
        Clow, Chigh, Ilow, Ihigh = breakpoints[-1]
        span_C = (Chigh - Clow) if (Chigh - Clow) != 0 else 1
        slope = (Ihigh - Ilow) / span_C
        I = slope * (conc - Clow) + Ilow
        return int(round(I))
    return None


async def fetch_openaq(client: httpx.AsyncClient, endpoint: str, params: dict) -> Optional[Dict[str, Any]]:
    try:
        resp = await client.get(f"{OPENAQ_BASE}/{endpoint}", params=params, timeout=20.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def extract_from_latest(payload: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if not payload:
        return None, None, None
    results = payload.get("results") or []
    if not results:
        return None, None, None
    pm25 = None
    pm10 = None
    updated = None
    # search through results and measurements to pick pm25 and pm10
    for res in results:
        measurements = res.get("measurements") or []
        for m in measurements:
            param = (m.get("parameter") or "").lower()
            val = m.get("value")
            ts = m.get("lastUpdated") or m.get("last_updated") or m.get("lastUpdatedAt") or None
            try:
                v = float(val)
            except Exception:
                v = None
            if param in ("pm25", "pm2.5") and pm25 is None and v is not None:
                pm25 = v
                if not updated and ts:
                    updated = ts
            if param == "pm10" and pm10 is None and v is not None:
                pm10 = v
                if not updated and ts:
                    updated = ts
        if pm25 is not None and pm10 is not None:
            break
    return pm25, pm10, updated


async def try_measurements_for_city(client: httpx.AsyncClient, city: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    # Try to fetch recent measurements (separate endpoint) for PM2.5 and PM10
    pm25 = None
    pm10 = None
    updated = None
    params = {"country": "IN", "city": city, "limit": 100, "sort": "desc", "parameter": "pm25,pm10"}
    resp = await fetch_openaq(client, "measurements", params)
    if resp:
        results = resp.get("results") or []
        for m in results:
            p = (m.get("parameter") or "").lower()
            try:
                v = float(m.get("value"))
            except Exception:
                continue
            ts = m.get("date", {}).get("utc") or m.get("date", {}).get("local") or m.get("date") or None
            if p in ("pm25", "pm2.5") and pm25 is None:
                pm25 = v
                updated = updated or ts
            if p == "pm10" and pm10 is None:
                pm10 = v
                updated = updated or ts
            if pm25 is not None and pm10 is not None:
                break
    return pm25, pm10, updated


async def find_locations_and_try(client: httpx.AsyncClient, city: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    # search locations with city in name (keyword)
    params = {"country": "IN", "limit": 50, "sort": "desc", "city": city}
    resp = await fetch_openaq(client, "locations", params)
    if not resp:
        return None, None, None
    locations = resp.get("results") or []
    for loc in locations:
        location_name = loc.get("id") or loc.get("location")
        # fetch measurements for this location
        params2 = {"location_id": loc.get("id"), "limit": 20}
        data = await fetch_openaq(client, "measurements", params2)
        if data:
            results = data.get("results") or []
            pm25 = None
            pm10 = None
            updated = None
            for m in results:
                p = (m.get("parameter") or "").lower()
                try:
                    v = float(m.get("value"))
                except Exception:
                    continue
                ts = m.get("date", {}).get("utc") or m.get("date", {}).get("local") or None
                if p in ("pm25", "pm2.5") and pm25 is None:
                    pm25 = v; updated = updated or ts
                if p == "pm10" and pm10 is None:
                    pm10 = v; updated = updated or ts
                if pm25 is not None and pm10 is not None:
                    return pm25, pm10, updated
    return None, None, None


@router.get("/top-cities")
async def top_cities():
    return {"cities": ["Delhi", "Mumbai", "Kolkata", "Chennai", "Hyderabad"]}


@router.get("/city/{city}")
async def city_endpoint(city: str):
    city_q = city
    async with httpx.AsyncClient() as client:
        # 1) try latest endpoint
        payload = await fetch_openaq(client, "latest", {"country": "IN", "city": city_q, "limit": 20})
        pm25, pm10, updated = extract_from_latest(payload)
        # 2) if empty, try measurements endpoint
        if pm25 is None and pm10 is None:
            pm25, pm10, updated = await try_measurements_for_city(client, city_q)
        # 3) if still empty, search locations and try
        if pm25 is None and pm10 is None:
            pm25, pm10, updated = await find_locations_and_try(client, city_q)

    # nothing found
    if pm25 is None and pm10 is None:
        # return 200 with message (frontend expects JSON)
        return {"city": city, "message": "No measurements found for PM2.5 or PM10"}

    sub_pm25 = get_subindex(pm25, PM25_BREAKPOINTS) if pm25 is not None else None
    sub_pm10 = get_subindex(pm10, PM10_BREAKPOINTS) if pm10 is not None else None
    candidates = [x for x in (sub_pm25, sub_pm10) if x is not None]
    overall_aqi = max(candidates) if candidates else None

    ts_iso = None
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            ts_iso = dt.astimezone(timezone.utc).isoformat()
        except Exception:
            ts_iso = updated

    return {
        "city": city,
        "pm25": None if pm25 is None else round(pm25, 2),
        "pm10": None if pm10 is None else round(pm10, 2),
        "aqi": overall_aqi,
        "subindex": {"pm25": sub_pm25, "pm10": sub_pm10},
        "updated": ts_iso,
        "source": "openaq"
    }
