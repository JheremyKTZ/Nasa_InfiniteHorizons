# Backend API (FastAPI)

## Requisitos
- Python 3.10+
- Cuenta de Google Earth Engine autenticada (earthengine-api)

## Instalación
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar
```bash
bash run.sh  # Windows PowerShell: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints
- POST /ndvi -> NDVI/EVI por punto y rango de fechas
- GET /meteo -> Temperatura y humedad diarias (NASA POWER)
- POST /classify -> Clasificación por NDVI (etiqueta + color)
- POST /observations -> Guardar observación en SQLite
- GET /observations -> Listar últimas observaciones
