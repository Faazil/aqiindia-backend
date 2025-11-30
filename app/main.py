from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.api.ingest import start_scheduler, ingest_job
app = FastAPI(title="AQI India API")
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    start_scheduler()
