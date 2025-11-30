import asyncio, os, httpx
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.db import save_measurement

OPENAQ_URL = "https://api.openaq.org/v2/latest"

async def fetch_city(session, city):
    try:
        r = await session.get(OPENAQ_URL, params={"country":"IN","city":city}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def parse_and_save(city, data):
    if not data: return
    # openaq returns results list
    results = data.get("results") or []
    if not results: return
    # take first measurement
    measurements = results[0].get("measurements", [])
    pm25 = None; pm10 = None; aqi = None
    for m in measurements:
        if m.get("parameter") == "pm25":
            pm25 = m.get("value")
        if m.get("parameter") == "pm10":
            pm10 = m.get("value")
    # aqi calculation not provided — leave aqi null for now
    ts = datetime.utcnow().isoformat()
    save_measurement(city, ts, aqi, pm25, pm10)

def ingest_job():
    cities = os.getenv("CITIES","Delhi,Mumbai,Kolkata,Bengaluru,Hyderabad").split(",")
    async def _run():
        async with httpx.AsyncClient() as session:
            tasks = [fetch_city(session, c) for c in cities]
            results = await asyncio.gather(*tasks)
            for city, data in zip(cities, results):
                parse_and_save(city, data)
    asyncio.run(_run())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ingest_job, 'interval', minutes=int(os.getenv("INGEST_MINUTES", "10")))
    scheduler.start()
