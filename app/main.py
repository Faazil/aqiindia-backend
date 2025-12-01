# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow only your site (recommended)
origins = [
    "https://aqiindia.live",
    "https://www.aqiindia.live",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET","POST","OPTIONS","PUT","DELETE"],
    allow_headers=["*"],
)

# ... your existing routes below ...
