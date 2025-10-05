from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from .services.gee import compute_ndvi_evi_point
from .services.power import fetch_power_daily
from .services.zones import build_zones
from .classification import classify_ndvi
from .db import get_session, init_db
from .models import Observation

app = FastAPI(title="NASA/GEE Vegetation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NDVIRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    cloud_pct_max: Optional[int] = 30


class NDVIResponse(BaseModel):
    date: str
    ndvi: Optional[float]
    evi: Optional[float]


class MeteoResponse(BaseModel):
    date: str
    t2m: Optional[float]
    rh2m: Optional[float]


class ClassifyRequest(BaseModel):
    ndvi: float


class SaveObservationRequest(BaseModel):
    latitude: float
    longitude: float
    date: str
    ndvi: Optional[float] = None
    evi: Optional[float] = None
    t2m: Optional[float] = None
    rh2m: Optional[float] = None
    label: Optional[str] = None


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


@app.post("/ndvi", response_model=List[NDVIResponse])
async def get_ndvi(req: NDVIRequest):
    return compute_ndvi_evi_point(
        latitude=req.latitude,
        longitude=req.longitude,
        start_date=req.start_date,
        end_date=req.end_date,
        cloud_pct_max=req.cloud_pct_max,
    )


@app.get("/meteo", response_model=List[MeteoResponse])
async def get_meteo(
    latitude: float = Query(...),
    longitude: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    return fetch_power_daily(latitude, longitude, start_date, end_date)


@app.get("/zones")
async def get_zones(
    minx: float = Query(...),
    miny: float = Query(...),
    maxx: float = Query(...),
    maxy: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    grid_km: float = Query(2.0),
    plant: str = Query('-'),
    irregular: bool = Query(True),
    cloud_pct_max: int = Query(60),
    scale: int = Query(60),
    min_area_m2: int = Query(2000),
    limit_per_cat: int = Query(2000),
    mock: bool = Query(False),
):
    bbox = (minx, miny, maxx, maxy)
    return build_zones(
        bbox, start_date, end_date,
        grid_km=grid_km,
        cloud_pct_max=cloud_pct_max,
        plant=plant,
        irregular=irregular,
        scale=scale,
        min_area_m2=min_area_m2,
        limit_per_cat=limit_per_cat,
        mock=mock,
    )


@app.post("/classify")
async def classify(req: ClassifyRequest):
    label, color = classify_ndvi(req.ndvi)
    return {"label": label, "color": color}


@app.post("/observations")
async def save_observation(req: SaveObservationRequest, session=Depends(get_session)):
    obs = Observation(
        latitude=req.latitude,
        longitude=req.longitude,
        date=req.date,
        ndvi=req.ndvi,
        evi=req.evi,
        t2m=req.t2m,
        rh2m=req.rh2m,
        label=req.label,
    )
    session.add(obs)
    session.commit()
    session.refresh(obs)
    return {"id": obs.id}


@app.get("/observations")
async def list_observations(session=Depends(get_session)):
    items = session.query(Observation).order_by(Observation.date.desc()).limit(200).all()
    return [
        {
            "id": it.id,
            "latitude": it.latitude,
            "longitude": it.longitude,
            "date": it.date,
            "ndvi": it.ndvi,
            "evi": it.evi,
            "t2m": it.t2m,
            "rh2m": it.rh2m,
            "label": it.label,
        }
        for it in items
    ]
