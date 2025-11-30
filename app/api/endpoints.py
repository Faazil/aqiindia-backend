from fastapi import APIRouter, HTTPException
from app.db import get_top_cities
from typing import List
router = APIRouter()

@router.get("/top-cities")
def top_cities(limit: int = 10):
    return get_top_cities(limit=limit)
