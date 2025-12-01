# app/api/endpoints.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/top-cities")
def get_top_cities():
    # your logic here
    return {"result": "ok"}

@router.get("/city/{city}")
def get_city(city: str):
    # your logic here
    return {"city": city}
