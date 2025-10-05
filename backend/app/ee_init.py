import os
from typing import Optional

try:
    import ee  # type: ignore
except Exception:  # pragma: no cover
    ee = None  # type: ignore

_initialized = False
_last_error: Optional[str] = None


def initialize_earth_engine() -> bool:
    global _initialized, _last_error
    if _initialized:
        return True
    if ee is None:
        _last_error = 'earthengine-api not installed'
        return False
    try:
        # Prefer service account if provided
        svc_email = os.getenv('EE_SERVICE_ACCOUNT')
        key_path = os.getenv('EE_PRIVATE_KEY')
        if svc_email and key_path and os.path.exists(key_path):
            credentials = ee.ServiceAccountCredentials(svc_email, key_path)
            ee.Initialize(credentials)
            _initialized = True
            return True
        # Fallback to default credentials (interactive auth previously stored)
        ee.Initialize()
        _initialized = True
        return True
    except Exception as e:
        _last_error = str(e)
        return False


def get_last_error() -> Optional[str]:
    return _last_error
