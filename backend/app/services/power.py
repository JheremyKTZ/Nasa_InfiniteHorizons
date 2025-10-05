from typing import List, Dict, Optional
import requests

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def fetch_power_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Optional[float]]]:
    params = {
        "parameters": "T2M,RH2M",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "format": "JSON",
    }
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    t2m = data.get("properties", {}).get("parameter", {}).get("T2M", {})
    rh2m = data.get("properties", {}).get("parameter", {}).get("RH2M", {})

    # Dates are keys like YYYYMMDD
    dates = sorted(set(list(t2m.keys()) + list(rh2m.keys())))
    result: List[Dict[str, Optional[float]]] = []
    for d in dates:
        iso = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
        result.append({
            "date": iso,
            "t2m": t2m.get(d),
            "rh2m": rh2m.get(d),
        })
    return result
