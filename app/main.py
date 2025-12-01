# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import router from endpoints (must exist at app/api/endpoints.py)
from app.api.endpoints import router as api_router

app = FastAPI(
    title="AQI India Backend",
    description="Backend API for AQI India project",
    version="1.0.0"
)

# Only allow your production frontend origin
origins = [
    "https://aqiindia.live",
    "https://www.aqiindia.live",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount the API router at /api
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Health"])
def root():
    return {"status": "OK", "message": "AQI backend running"}
