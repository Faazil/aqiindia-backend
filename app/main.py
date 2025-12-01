# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router

# --- Create App ---
app = FastAPI(
    title="AQI India Backend",
    description="Backend API for AQI India project",
    version="1.0.0"
)

# --- CORS CONFIG ---
# Allow only your frontend domain (recommended)
origins = [
    "https://aqiindia.live",
    "https://www.aqiindia.live",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Only allow your domain
    allow_credentials=True,
    allow_methods=["*"],              # GET, POST, OPTIONS, PUT, DELETE
    allow_headers=["*"],              # Content-Type, Authorization, etc.
)

# --- Include API routes from app/api/endpoints.py ---
app.include_router(api_router, prefix="/api")

# --- Root health check ---
@app.get("/", tags=["Health"])
def root():
    return {"status": "OK", "message": "AQI backend running"}
