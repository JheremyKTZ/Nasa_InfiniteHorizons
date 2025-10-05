from typing import Dict, Any, List, Tuple
from datetime import datetime
from shapely.geometry import Polygon, mapping, shape
import random
import math

from .gee import compute_ndvi_evi_point
from .power import fetch_power_daily
from ..classification import classify_ndvi
from ..ee_init import initialize_earth_engine

# Try to import ee lazily
try:
    import ee  # type: ignore
    _HAS_EE = True
except Exception:
    _HAS_EE = False

# Color map consistent with frontend
COLOR_MAP = {
    'cultivo': '#2ECC40',
    'posible_cultivo': '#FFDC00',
    'deforestacion': '#FF4136',
    'recuperacion': '#8E6E53',
    'areas_verdes': '#808080',
}


def _generate_grid(bbox: Tuple[float, float, float, float], step_deg: float) -> List[Tuple[Polygon, Tuple[float, float]]]:
    minx, miny, maxx, maxy = bbox
    cells: List[Tuple[Polygon, Tuple[float, float]]] = []
    y = miny
    while y < maxy:
        x = minx
        y2 = min(y + step_deg, maxy)
        while x < maxx:
            x2 = min(x + step_deg, maxx)
            poly = Polygon([(x, y), (x2, y), (x2, y2), (x, y2), (x, y)])
            cx = (x + x2) / 2.0
            cy = (y + y2) / 2.0
            cells.append((poly, (cy, cx)))
            x = x2
        y = y2
    return cells


def _enrich_props(lat: float, lon: float, start_date: str, end_date: str, props: Dict[str, Any]) -> Dict[str, Any]:
    meteo = fetch_power_daily(lat, lon, start_date, end_date)
    t2m = None
    rh2m = None
    if meteo:
        try:
            t2m = meteo[-1].get("t2m")
            rh2m = meteo[-1].get("rh2m")
        except Exception:
            pass
    props.update({"t2m": t2m, "rh2m": rh2m})
    return props


def _random_irregular_polygon(cx: float, cy: float, min_r: float, max_r: float, num_vertices: int = 12) -> Polygon:
    # Build an irregular polygon around center using random radial distances
    angles = sorted([random.random() * 2 * math.pi for _ in range(num_vertices)])
    pts = []
    for a in angles:
        r = random.uniform(min_r, max_r)
        # small jitter to make it more irregular
        r *= random.uniform(0.85, 1.15)
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        pts.append((x, y))
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def build_zones_mock(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    plant: str = '—',
    count: int = 320,
) -> Dict[str, Any]:
    # Focus mock on Cochabamba department bbox (approx), clipped to requested bbox
    # Cochabamba approx: lon [-67.5, -64.3], lat [-18.6, -16.0]
    co_minx, co_maxx = -67.5, -64.3
    co_miny, co_maxy = -18.6, -16.0
    minx = max(bbox[0], co_minx)
    miny = max(bbox[1], co_miny)
    maxx = min(bbox[2], co_maxx)
    maxy = min(bbox[3], co_maxy)
    if minx >= maxx or miny >= maxy:
        # If outside Cochabamba, just return empty to avoid confusing results
        return {"type": "FeatureCollection", "features": []}

    random.seed(42)
    cols = int(math.sqrt(count) * 1.2)
    rows = int(math.sqrt(count) * 1.2)
    dx = (maxx - minx) / max(cols, 1)
    dy = (maxy - miny) / max(rows, 1)

    features: List[Dict[str, Any]] = []

    # Weighted categories to ensure plenty of polygons in each class
    cats = [
        ('cultivo', 0.28),
        ('posible_cultivo', 0.27),
        ('recuperacion', 0.18),
        ('deforestacion', 0.17),
        ('areas_verdes', 0.10),
    ]
    weights = [c[1] for c in cats]
    names = [c[0] for c in cats]

    for i in range(cols):
        for j in range(rows):
            if len(features) >= count:
                break
            cx = minx + (i + 0.5) * dx + random.uniform(-0.2 * dx, 0.2 * dx)
            cy = miny + (j + 0.5) * dy + random.uniform(-0.2 * dy, 0.2 * dy)
            # Size of polygon scales with cell size
            min_r = 0.15 * min(dx, dy)
            max_r = 0.45 * min(dx, dy)
            poly = _random_irregular_polygon(cx, cy, min_r, max_r, num_vertices=random.randint(8, 16))
            # Clip to bbox to avoid spillover
            if not poly.is_valid or poly.is_empty:
                continue
            if not (minx <= cx <= maxx and miny <= cy <= maxy):
                continue

            category = random.choices(names, weights=weights, k=1)[0]
            ndvi_val = {
                'cultivo': random.uniform(0.55, 0.85),
                'posible_cultivo': random.uniform(0.35, 0.50),
                'recuperacion': random.uniform(0.18, 0.32),
                'deforestacion': random.uniform(0.02, 0.14),
                'areas_verdes': random.uniform(-0.05, 0.05),
            }[category]
            evi_val = max(0.0, ndvi_val - random.uniform(0.05, 0.12))
            t2m = round(random.uniform(15.0, 30.0), 1)
            rh2m = int(random.uniform(35, 85))

            props = {
                'category': category,
                'plant': plant if plant != '-' else random.choice(['soya', 'maiz', 'trigo', 'cafe', '—']),
                'start_date': start_date,
                'end_date': end_date,
                'ndvi': round(ndvi_val, 3),
                'evi': round(evi_val, 3),
                'estimate_date': end_date,
                't2m': t2m,
                'rh2m': rh2m,
                'color': COLOR_MAP.get(category, '#000000'),
            }

            features.append({
                'type': 'Feature',
                'properties': props,
                'geometry': mapping(poly),
            })
        if len(features) >= count:
            break

    return { 'type': 'FeatureCollection', 'features': features }


def build_zones_grid(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    grid_km: float = 2.0,
    cloud_pct_max: int = 70,
    plant: str = "—",
) -> Dict[str, Any]:
    # Approx deg per km at equator ~ 0.009 degrees.
    step_deg = 0.009 * grid_km
    grid = _generate_grid(bbox, step_deg)

    features: List[Dict[str, Any]] = []

    for poly, (lat, lon) in grid:
        ndvi_series = compute_ndvi_evi_point(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            cloud_pct_max=cloud_pct_max,
        )
        ndvi_val = None
        evi_val = None
        date_val = None
        if ndvi_series:
            last = ndvi_series[-1]
            ndvi_val = last.get("ndvi")
            evi_val = last.get("evi")
            date_val = last.get("date")

        # classify and enrich
        label, color = classify_ndvi(ndvi_val if ndvi_val is not None else -1.0)
        label_map = {
            "cultivo": "cultivo",
            "posible_cultivo": "posible_cultivo",
            "deforestacion": "deforestacion",
            "recuperacion": "recuperacion",
            "sin_datos": "areas_verdes",
            "no_plantado_area_verde": "areas_verdes",
        }
        category = label_map.get(label, label)

        props = {
            "category": category,
            "plant": plant,
            "start_date": start_date,
            "end_date": end_date,
            "ndvi": ndvi_val,
            "evi": evi_val,
            "estimate_date": date_val,
            "color": color,
        }
        props = _enrich_props(lat, lon, start_date, end_date, props)

        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(poly),
        })

    return {"type": "FeatureCollection", "features": features}


def build_zones_irregular(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    cloud_pct_max: int = 60,
    plant: str = "—",
    scale: int = 60,
    min_area_m2: int = 2_000,
    limit_per_cat: int = 2000,
) -> Dict[str, Any]:
    if not _HAS_EE:
        return {"type": "FeatureCollection", "features": []}
    if not initialize_earth_engine():
        return {"type": "FeatureCollection", "features": []}

    # Build region geometry from bbox
    minx, miny, maxx, maxy = bbox
    region = ee.Geometry.Rectangle([minx, miny, maxx, maxy])

    # Sentinel-2 SR collection with cloud filter
    s2 = (
        ee.ImageCollection('COPERNICUS/S2_SR')
        .filterDate(start_date, end_date)
        .filterBounds(region)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', cloud_pct_max))
    )
    try:
        if s2.size().getInfo() == 0:
            return {"type": "FeatureCollection", "features": []}
    except Exception:
        return {"type": "FeatureCollection", "features": []}

    # Compute NDVI per image and build a quality mosaic by max NDVI
    def add_ndvi(img):
        return img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI'))
    s2_ndvi = s2.map(add_ndvi)
    mosaic = s2_ndvi.qualityMosaic('NDVI')
    ndvi = mosaic.select('NDVI')

    # Also compute EVI on the mosaic for enrichment
    evi_img = mosaic.expression(
        '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
        { 'NIR': mosaic.select('B8'), 'RED': mosaic.select('B4'), 'BLUE': mosaic.select('B2') }
    ).rename('EVI')

    # Lower thresholds to increase coverage
    cultivo_m = ndvi.gte(0.5)
    posible_m = ndvi.gte(0.3).And(ndvi.lt(0.5))
    recuperacion_m = ndvi.gte(0.15).And(ndvi.lt(0.3))
    deforestacion_m = ndvi.gte(0.00).And(ndvi.lt(0.15))
    areas_verdes_m = ndvi.lt(0.00)

    class_defs = [
        ("cultivo", cultivo_m),
        ("posible_cultivo", posible_m),
        ("recuperacion", recuperacion_m),
        ("deforestacion", deforestacion_m),
        ("areas_verdes", areas_verdes_m),
    ]

    features: List[Dict[str, Any]] = []

    for category, mask in class_defs:
        try:
            vector_fc = mask.selfMask().reduceToVectors(
                geometry=region,
                scale=scale,
                geometryType='polygon',
                eightConnected=True,
                bestEffort=True,
                labelProperty='label',
                maxPixels=1e13,
                tileScale=4,
            )
            vec = vector_fc.limit(limit_per_cat).getInfo()
        except Exception:
            vec = { 'features': [] }

        for f in vec.get('features', []):
            geom = f.get('geometry')
            if not geom:
                continue
            try:
                c = shape(geom).centroid
                lat = c.y
                lon = c.x
            except Exception:
                lat = (bbox[1] + bbox[3]) / 2.0
                lon = (bbox[0] + bbox[2]) / 2.0

            ndvi_val = None
            evi_val = None
            try:
                pt = ee.Geometry.Point([lon, lat])
                ndvi_val = ndvi.reduceRegion(ee.Reducer.mean(), pt, scale).get('NDVI').getInfo()
                evi_val = evi_img.reduceRegion(ee.Reducer.mean(), pt, scale).get('EVI').getInfo()
            except Exception:
                pass

            props = {
                'category': category,
                'plant': plant,
                'start_date': start_date,
                'end_date': end_date,
                'ndvi': ndvi_val,
                'evi': evi_val,
                'estimate_date': end_date,
                't2m': None,
                'rh2m': None,
                'color': COLOR_MAP.get(category, '#000000'),
            }
            props = _enrich_props(lat, lon, start_date, end_date, props)

            try:
                if shape(geom).area < (min_area_m2 / (111_320 ** 2)):
                    continue
            except Exception:
                pass

            features.append({
                'type': 'Feature',
                'properties': props,
                'geometry': geom,
            })

    return {"type": "FeatureCollection", "features": features}


def build_zones(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    grid_km: float = 2.0,
    cloud_pct_max: int = 70,
    plant: str = "—",
    irregular: bool = True,
    scale: int = 60,
    min_area_m2: int = 2000,
    limit_per_cat: int = 2000,
    mock: bool = False,
) -> Dict[str, Any]:
    if mock:
        return build_zones_mock(bbox, start_date, end_date, plant=plant, count=320)
    if irregular:
        try:
            irregular_fc = build_zones_irregular(
                bbox, start_date, end_date,
                cloud_pct_max=cloud_pct_max,
                plant=plant,
                scale=scale,
                min_area_m2=min_area_m2,
                limit_per_cat=limit_per_cat,
            )
            if irregular_fc.get('features'):
                return irregular_fc
        except Exception:
            pass
    # Fallback to grid; adapt grid size to bbox width to get enough cells
    minx, miny, maxx, maxy = bbox
    width_deg = maxx - minx
    step_deg = max(width_deg / 30.0, 0.005)
    grid_km_adapted = step_deg / 0.009
    return build_zones_grid(bbox, start_date, end_date, grid_km=grid_km_adapted, cloud_pct_max=cloud_pct_max, plant=plant)
