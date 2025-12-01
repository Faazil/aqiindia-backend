# app/api/endpoints.py
from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

router = APIRouter()

OPENAQ_BASE = "https://api.openaq.org/v2/latest"
# We will request country=IN and city=<city>

# CPCB/typical breakpoints for PM2.5 and PM10 (conc ranges -> AQI ranges)
# Each entry: (C_low, C_high, I_low, I_high)
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
    """
    Linear interpolation from concentration (C) into sub-index range using a breakpoint tuple.
    Returns sub-index (float) or None if not applicable.
    """
    C_low, C_high, I_low, I_high = bp
    if C is None:
        return None
    if C_low <= C <= C_high:
        # careful arithmetic
        # I = ((Ihigh - Ilow)/(Chigh - Clow)) * (C - Clow) + Ilow
        numerator = (I_high := I_high if False else I_high)  # dummy to keep style below
        # compute step by step to avoid accidental float mistakes
        span_C = (C_high - C_low)
        if span_C == 0:
            return float(I_low)
        slope = (I_high - I_low) / span_C
        I = slope * (C - C_low) + I_low
        return I
    return None


def get_subindex(conc: Optional[float], breakpoints: list) -> Optional[int]:
    """
    Given a concentration and breakpoint table, return the rounded sub-index (integer).
    Returns None if conc is None or doesn't fit any breakpoint.
    """
    if conc is None:
        return None
    for bp in breakpoints:
        val = linear_interpolate(conc, bp)
        if val is not None:
            # round to nearest integer
            return int(round(val))
    # if above highest defined breakpoint, extrapolate using last interval
    if conc > breakpoints[-1][1]:
        Clow, Chigh, Ilow, Ihigh = breakpoints[-1]
        span_C = (Chigh - Clow) if (Chigh - Clow) != 0 else 1
        slope = (Ihigh - Ilow) / span_C
        I = slope * (conc - Clow) + Ilow
        return int(round(I))
    return None


async def fetch_city_latest(client: httpx.AsyncClient, city: str) -> Optional[Dict[str, Any]]:
    """
    Query OpenAQ latest endpoint for the city (country=IN).
    Returns parsed JSON dict or None on error.
    """
    params = {"country": "IN", "city": city, "limit": 20}
    try:
        resp = await client.get(OPENAQ_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def extract_pm_values_from_openaq_payload(payload: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Given the OpenAQ 'latest' JSON, attempt to find PM2.5 and PM10 concentrations and a timestamp.
    Returns (pm25, pm10, last_updated_iso)
    - pm25/pm10 are floats or None
    - last_updated_iso is ISO timestamp string or None
    """
    if not payload:
        return None, None, None

    results = payload.get("results") or []
    if not results:
        return None, None, None

    # We'll examine the first few locations for pm25/pm10 measurements and take the
    # first available measurement for each pollutant (this is simple and deterministic).
    pm25 = None
    pm10 = None
    updated = None

    for res in results:
        # 'measurements' is usually a list
        measurements = res.get("measurements") or []
        for m in measurements:
            param = (m.get("parameter") or "").lower()
            # OpenAQ returns ISO timestamps in 'lastUpdated' or 'lastUpdated' key
            t = m.get("lastUpdated") or m.get("last_updated") or m.get("lastUpdatedAt") or None
            if param in ("pm25", "pm2.5") and pm25 is None:
                # try float conversion
                try:
                    pm25 = float(m.get("value"))
                    if not updated and t:
                        updated = t
                except Exception:
                    pm25 = None
            if param == "pm10" and pm10 is None:
                try:
                    pm10 = float(m.get("value"))
                    if not updated and t:
                        updated = t
                except Exception:
                    pm10 = None
        # if we found both, break
        if pm25 is not None and pm10 is not None:
            break

    return pm25, pm10, updated


@router.get("/top-cities")
async def get_top_cities():
    """
    Basic placeholder: can be extended to compute top polluted cities from DB or OpenAQ.
    For now, return a static list or instruct frontend to use /api/city/<city>.
    """
    sample = [
        "Delhi", "Mumbai", "Kolkata", "Chennai", "Hyderabad"
    ]
    return {"cities": sample}


@router.get("/city/{city}")
async def get_city(city: str):
    """
    Returns the latest PM2.5, PM10 and computed AQI for a given city (India).
    Response:
      {
        "city": "Delhi",
        "pm25": 85.2,
        "pm10": 132.1,
        "aqi": 167,
        "subindex": {"pm25": 167, "pm10": 134},
        "updated": "2025-12-01T14:20:00Z"
      }
    If no data available, returns 204 with a descriptive body.
    """
    city_query = city
    async with httpx.AsyncClient() as client:
        payload = await fetch_city_latest(client, city_query)
