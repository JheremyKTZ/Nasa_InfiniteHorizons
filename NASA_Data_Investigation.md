# NASA Data Investigation: Obtención de Datos Satelitales para Análisis de Vegetación

## Introducción

### ¿Qué son NDVI, EVI, temperatura y humedad?

**NDVI (Normalized Difference Vegetation Index)**: Es un índice que mide la "verdor" de la vegetación comparando la reflectancia en las bandas del infrarrojo cercano y rojo. Valores entre 0.1-0.3 indican vegetación escasa, 0.3-0.6 vegetación moderada, y 0.6-1.0 vegetación densa.

**EVI (Enhanced Vegetation Index)**: Similar al NDVI pero con mejor sensibilidad en áreas de alta biomasa y menor influencia atmosférica. Es especialmente útil para monitorear cambios sutiles en la vegetación.

**Temperatura**: Datos de temperatura superficial terrestre (LST) obtenidos por sensores satelitales, cruciales para entender el estrés hídrico de las plantas y patrones climáticos.

**Humedad**: Incluye humedad del suelo y vapor de agua atmosférico, fundamentales para predecir floración y crecimiento vegetal.

### Aplicaciones
- **Detección de floración**: Los índices de vegetación muestran cambios en la actividad fotosintética
- **Monitoreo agrícola**: Seguimiento del estado de cultivos y predicción de rendimientos
- **Estudios climáticos**: Análisis de patrones de temperatura y humedad
- **Conservación**: Evaluación de ecosistemas y biodiversidad

## Datasets Recomendados

| Dataset | Variables | Resolución | Fuente | Período | Acceso |
|---------|-----------|------------|--------|---------|--------|
| MODIS Terra/Aqua | NDVI, EVI, LST | 250m-1km | NASA LP DAAC | 2000-presente | EarthData |
| Landsat 8/9 | NDVI, EVI, LST | 30m | USGS | 2013-presente | EarthData |
| NASA POWER | Temperatura, Humedad | 0.5° | NASA | 1981-presente | API REST |
| ERA5 | Temperatura, Humedad | 0.25° | ECMWF | 1940-presente | GEE |
| Sentinel-2 | NDVI, EVI | 10-20m | ESA | 2015-presente | GEE |
| CHIRPS | Precipitación | 0.05° | UCSB | 1981-presente | GEE |

## Autenticación y Configuración

### 1. NASA EarthData

```bash
# Registro en https://urs.earthdata.nasa.gov/
# Crear aplicación para obtener credenciales
```

```python
import requests
from requests.auth import HTTPBasicAuth

# Configurar credenciales
username = "tu_usuario"
password = "tu_password"
auth = HTTPBasicAuth(username, password)
```

### 2. NASA POWER API

```python
# No requiere autenticación para datos públicos
base_url = "https://power.larc.nasa.gov/api/temporal/daily"
```

### 3. Google Earth Engine

```python
# Instalación
# pip install earthengine-api

import ee

# Autenticación (primera vez)
# ee.Authenticate()

# Inicialización
ee.Initialize()
```

## Ejemplos de Obtención de Datos

### 1. NDVI y EVI con NASA EarthData (MODIS)

```python
import requests
import json
from datetime import datetime, timedelta

def get_modis_data(lat, lon, start_date, end_date):
    """
    Obtiene datos MODIS NDVI/EVI para coordenadas específicas
    """
    base_url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    
    params = {
        'lat': lat,
        'lon': lon,
        'start': start_date,
        'end': end_date,
        'kmAboveBelow': 1,
        'kmLeftRight': 1
    }
    
    response = requests.get(base_url, params=params, auth=auth)
    return response.json()

# Ejemplo de uso
lat, lon = -16.5, -68.1  # Coordenadas de La Paz, Bolivia
start_date = "2023-01-01"
end_date = "2023-12-31"

data = get_modis_data(lat, lon, start_date, end_date)
print(f"NDVI promedio: {data['data'][0]['ndvi']}")
```

### 2. Temperatura y Humedad con NASA POWER

```python
def get_nasa_power_data(lat, lon, start_date, end_date):
    """
    Obtiene datos de temperatura y humedad de NASA POWER
    """
    base_url = "https://power.larc.nasa.gov/api/temporal/daily"
    
    params = {
        'parameters': 'T2M,RH2M',
        'community': 'AG',
        'longitude': lon,
        'latitude': lat,
        'start': start_date,
        'end': end_date,
        'format': 'JSON'
    }
    
    response = requests.get(base_url, params=params)
    return response.json()

# Ejemplo de uso
power_data = get_nasa_power_data(lat, lon, start_date, end_date)
print(f"Temperatura promedio: {power_data['properties']['parameter']['T2M']['mean']}°C")
```

### 3. Datos con Google Earth Engine

```python
import ee
import pandas as pd

def get_gee_ndvi_data(lat, lon, start_date, end_date):
    """
    Obtiene datos NDVI de Sentinel-2 usando GEE
    """
    # Definir punto de interés
    point = ee.Geometry.Point([lon, lat])
    
    # Cargar colección Sentinel-2
    collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                  .filterDate(start_date, end_date)
                  .filterBounds(point)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
    
    def calculate_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    # Calcular NDVI
    ndvi_collection = collection.map(calculate_ndvi)
    
    # Obtener valores en el punto
    def extract_values(image):
        value = image.select('NDVI').reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=10
        ).get('NDVI')
        return ee.Feature(None, {'NDVI': value, 'date': image.date()})
    
    values = ndvi_collection.map(extract_values).getInfo()
    
    # Convertir a DataFrame
    data = []
    for feature in values['features']:
        data.append({
            'date': feature['properties']['date'],
            'NDVI': feature['properties']['NDVI']
        })
    
    return pd.DataFrame(data)

# Ejemplo de uso
gee_data = get_gee_ndvi_data(lat, lon, start_date, end_date)
print(gee_data.head())
```

### 4. Ejemplo con cURL

```bash
# NASA POWER API
curl "https://power.larc.nasa.gov/api/temporal/daily?parameters=T2M,RH2M&community=AG&longitude=-68.1&latitude=-16.5&start=20230101&end=20231231&format=JSON"

# MODIS API (requiere autenticación)
curl -u "usuario:password" "https://modis.ornl.gov/rst/api/v1/MOD13Q1?lat=-16.5&lon=-68.1&start=2023-01-01&end=2023-12-31&kmAboveBelow=1&kmLeftRight=1"
```

## Visualización de Datos

### 1. Gráficos con Matplotlib

```python
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

def plot_vegetation_indices(data):
    """
    Crea gráficos de series temporales de índices de vegetación
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # NDVI
    ax1.plot(data['date'], data['NDVI'], 'g-', linewidth=2, label='NDVI')
    ax1.set_ylabel('NDVI')
    ax1.set_title('Índice de Vegetación Normalizado (NDVI)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # EVI
    ax2.plot(data['date'], data['EVI'], 'b-', linewidth=2, label='EVI')
    ax2.set_ylabel('EVI')
    ax2.set_xlabel('Fecha')
    ax2.set_title('Índice de Vegetación Mejorado (EVI)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.show()

# Ejemplo de uso
plot_vegetation_indices(gee_data)
```

### 2. Mapas Interactivos con Folium

```python
import folium
import numpy as np

def create_ndvi_map(lat, lon, ndvi_data):
    """
    Crea un mapa interactivo con datos NDVI
    """
    # Crear mapa base
    m = folium.Map(location=[lat, lon], zoom_start=10)
    
    # Agregar marcador con información
    popup_text = f"""
    <b>Coordenadas:</b> {lat}, {lon}<br>
    <b>NDVI Promedio:</b> {np.mean(ndvi_data):.3f}<br>
    <b>NDVI Máximo:</b> {np.max(ndvi_data):.3f}<br>
    <b>NDVI Mínimo:</b> {np.min(ndvi_data):.3f}
    """
    
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color='green', icon='leaf')
    ).add_to(m)
    
    # Agregar capa de satélite
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Imagen Satelital',
        overlay=False,
        control=True
    ).add_to(m)
    
    return m

# Ejemplo de uso
ndvi_values = [0.2, 0.4, 0.6, 0.8, 0.5, 0.3]  # Datos de ejemplo
mapa = create_ndvi_map(lat, lon, ndvi_values)
mapa.save('ndvi_map.html')
```

## Comparación: APIs REST de NASA vs Google Earth Engine

| Aspecto | NASA APIs | Google Earth Engine |
|---------|-----------|-------------------|
| **Facilidad de uso** | Media (requiere manejo de APIs) | Alta (SDK integrado) |
| **Procesamiento** | Limitado | Potente (cloud computing) |
| **Resolución** | 250m-1km (MODIS) | 10-30m (Sentinel-2, Landsat) |
| **Cobertura temporal** | 2000-presente | 1972-presente |
| **Costo** | Gratuito | Gratuito (con límites) |
| **Escalabilidad** | Limitada | Excelente |
| **Tiempo de desarrollo** | Mayor | Menor |
| **Dependencias** | Múltiples APIs | Una plataforma |

### Ventajas de NASA APIs:
- Acceso directo a datos oficiales
- Control granular sobre descargas
- Ideal para análisis puntuales

### Ventajas de Google Earth Engine:
- Procesamiento en la nube
- Múltiples fuentes de datos integradas
- Herramientas de análisis avanzadas
- Mejor para análisis espaciales extensos

## Conclusión para MVP de Detección de Floración en Bolivia

### Recomendación: **Google Earth Engine**

Para un MVP de detección de floración en Bolivia, recomiendo usar **Google Earth Engine** por las siguientes razones:

1. **Resolución espacial**: Sentinel-2 (10-20m) es ideal para detectar cambios sutiles en vegetación
2. **Cobertura temporal**: Datos desde 2015 con frecuencia semanal
3. **Procesamiento eficiente**: Análisis de grandes áreas sin descargar datos
4. **Integración**: Múltiples sensores (Sentinel-2, Landsat, MODIS) en una plataforma
5. **Rapidez de desarrollo**: SDK maduro con ejemplos abundantes

### Estrategia recomendada:
1. **Datos principales**: Sentinel-2 NDVI/EVI (GEE)
2. **Datos meteorológicos**: NASA POWER para temperatura y humedad
3. **Validación**: Comparar con datos in situ de estaciones meteorológicas
4. **Frecuencia**: Análisis semanal durante temporadas de floración

### Próximos pasos:
1. Configurar cuenta GEE y autenticación
2. Desarrollar pipeline de procesamiento NDVI/EVI
3. Integrar datos meteorológicos de NASA POWER
4. Implementar algoritmo de detección de floración
5. Validar con datos históricos de Bolivia

## Enlaces a Documentación Oficial

### NASA EarthData
- [Portal principal](https://earthdata.nasa.gov/)
- [Guía de APIs](https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python)
- [MODIS API](https://modis.ornl.gov/data/modis_webservice.html)

### NASA POWER
- [Documentación API](https://power.larc.nasa.gov/docs/services/api/)
- [Parámetros disponibles](https://power.larc.nasa.gov/docs/services/api/v1/parameters/)
- [Ejemplos de uso](https://power.larc.nasa.gov/docs/services/api/v1/temporal/)

### Google Earth Engine
- [Documentación oficial](https://developers.google.com/earth-engine)
- [Guía de Python](https://developers.google.com/earth-engine/guides/python_install)
- [Colecciones de datos](https://developers.google.com/earth-engine/datasets)
- [Ejemplos de código](https://github.com/google/earthengine-api/tree/master/examples)

### Datasets Específicos
- [MODIS Vegetation Indices](https://lpdaac.usgs.gov/products/mod13q1v061/)
- [Sentinel-2](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
- [Landsat 8/9](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2)

---

*Documento creado para investigación de datos satelitales aplicados a detección de floración en Bolivia*
