from typing import List, Dict, Optional
import ee
from ..ee_init import initialize_earth_engine

_initialized = False

def _ensure_init() -> None:
    global _initialized
    if _initialized:
        return
    if initialize_earth_engine():
        _initialized = True


def compute_ndvi_evi_point(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cloud_pct_max: int = 30,
) -> List[Dict[str, Optional[float]]]:
    _ensure_init()
    if not _initialized:
        return []

    point = ee.Geometry.Point([longitude, latitude])

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR")
        .filterDate(start_date, end_date)
        .filterBounds(point)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_pct_max))
    )

    def with_indices(image: ee.Image) -> ee.Image:
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = image.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {
                "NIR": image.select("B8"),
                "RED": image.select("B4"),
                "BLUE": image.select("B2"),
            },
        ).rename("EVI")
        return image.addBands([ndvi, evi])

    with_idx = s2.map(with_indices)

    def extract(img: ee.Image):
        stats = img.select(["NDVI", "EVI"]).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=10
        )
        return ee.Feature(None, {
            "date": ee.Date(img.get("system:time_start")).format("YYYY-MM-dd"),
            "NDVI": stats.get("NDVI"),
            "EVI": stats.get("EVI"),
        })

    feats = with_idx.map(extract).getInfo()
    results: List[Dict[str, Optional[float]]] = []
    for f in feats.get("features", []):
        p = f.get("properties", {})
        results.append({
            "date": p.get("date"),
            "ndvi": p.get("NDVI"),
            "evi": p.get("EVI"),
        })
    results.sort(key=lambda r: r.get("date") or "")
    return results
