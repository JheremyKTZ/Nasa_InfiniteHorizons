import React, { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import axios from 'axios'

mapboxgl.accessToken = 'pk.eyJ1IjoiZ3VpbGFkIiwiYSI6ImNtZ2Q2Z3BjeDBicWoya3BzbTNxcHZjcGkifQ.Iyeru-MS3XqalHI_yNv4Fg'

const CATEGORY_STYLES = {
  cultivo: { color: '#2ECC40', label: 'Verde - Cultivo' },
  posible_cultivo: { color: '#FFDC00', label: 'Amarillo - Posibles lugares para plantar' },
  deforestacion: { color: '#FF4136', label: 'Rojo - Zona de deforestación' },
  recuperacion: { color: '#8E6E53', label: 'Café - Nunca se planta o está en recuperación' },
  areas_verdes: { color: '#808080', label: 'Gris - Áreas verdes' },
}

const SEASONS = {
  '2024': { start: '2024-01-01', end: '2024-12-31' },
  '2025': { start: '2025-01-01', end: '2025-12-31' },
  '2023': { start: '2023-01-01', end: '2023-12-31' },
}

export default function App() {
  const mapRef = useRef(null)
  const containerRef = useRef(null)
  const [coords, setCoords] = useState({ lat: -16.5, lon: -68.15 })
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [visibleCategories, setVisibleCategories] = useState({
    cultivo: true,
    posible_cultivo: true,
    deforestacion: true,
    recuperacion: true,
    areas_verdes: true,
  })
  const [plant, setPlant] = useState('-')
  const [region, setRegion] = useState('')
  const [season, setSeason] = useState('2024')
  const [search, setSearch] = useState('')
  const [useMock, setUseMock] = useState(true)
  const popupRef = useRef(new mapboxgl.Popup({ closeButton: false, closeOnClick: false }))
  const userMarkerRef = useRef(null)

  useEffect(() => {
    if (containerRef.current && !mapRef.current) {
      mapRef.current = new mapboxgl.Map({
        container: containerRef.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [coords.lon, coords.lat],
        zoom: 7
      })

      mapRef.current.addControl(new mapboxgl.NavigationControl({ showCompass: false }))

      const geolocate = new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showUserLocation: false,
      })
      mapRef.current.addControl(geolocate)

      geolocate.on('geolocate', (e) => {
        const { latitude, longitude } = e.coords
        setCoords({ lat: latitude, lon: longitude })
        if (userMarkerRef.current) userMarkerRef.current.remove()
        userMarkerRef.current = new mapboxgl.Marker({ color: '#007aff' })
          .setLngLat([longitude, latitude])
          .addTo(mapRef.current)
      })

      mapRef.current.on('load', async () => {
        await refreshZones()
        mapRef.current.on('moveend', refreshZones)
      })

      mapRef.current.on('click', (e) => {
        setCoords({ lat: e.lngLat.lat, lon: e.lngLat.lng })
      })
    }
  }, [])

  function gridKmByZoom(z) {
    if (z >= 12) return 1
    if (z >= 10) return 2
    if (z >= 8) return 5
    if (z >= 6) return 10
    if (z >= 4) return 20
    return 40
  }

  async function refreshZones() {
    if (!mapRef.current) return
    const b = mapRef.current.getBounds()
    const z = mapRef.current.getZoom()
    const sel = SEASONS[season] || SEASONS['2024']
    const baseParams = {
      minx: b.getWest(),
      miny: b.getSouth(),
      maxx: b.getEast(),
      maxy: b.getNorth(),
      start_date: sel.start,
      end_date: sel.end,
      grid_km: gridKmByZoom(z),
      plant: plant || '-',
      irregular: true,
      cloud_pct_max: 70,
      scale: 60,
      min_area_m2: 1500,
      limit_per_cat: 2000,
      mock: useMock,
    }
    try {
      let { data } = await axios.get('http://localhost:8000/zones', { params: baseParams })
      let features = data?.features?.length || 0
      if (useMock && features === 0) {
        // Retry with Cochabamba bbox to guarantee demo data
        const cochabambaBBox = { minx: -67.5, miny: -18.6, maxx: -64.3, maxy: -16.0 }
        const params = { ...baseParams, ...cochabambaBBox }
        const resp = await axios.get('http://localhost:8000/zones', { params })
        data = resp.data
        features = data?.features?.length || 0
        if (features > 0) {
          mapRef.current.fitBounds([[cochabambaBBox.minx, cochabambaBBox.miny], [cochabambaBBox.maxx, cochabambaBBox.maxy]], { padding: 24 })
        }
      }

      if (!mapRef.current.getSource('zones')) {
        mapRef.current.addSource('zones', { type: 'geojson', data })
        addLayers()
      } else {
        const src = mapRef.current.getSource('zones')
        src.setData(data)
      }
    } catch (e) {
      console.error('Zones error', e)
    }
  }

  function addLayers() {
    Object.entries(CATEGORY_STYLES).forEach(([cat, style]) => {
      const fillId = `fill-${cat}`
      const lineId = `line-${cat}`

      if (!mapRef.current.getLayer(fillId)) {
        mapRef.current.addLayer({
          id: fillId,
          type: 'fill',
          source: 'zones',
          layout: { visibility: visibleCategories[cat] ? 'visible' : 'none' },
          paint: { 'fill-color': style.color, 'fill-opacity': 0.5 },
          filter: ['==', ['get', 'category'], cat],
        })
      }
      if (!mapRef.current.getLayer(lineId)) {
        mapRef.current.addLayer({
          id: lineId,
          type: 'line',
          source: 'zones',
          layout: { visibility: visibleCategories[cat] ? 'visible' : 'none' },
          paint: { 'line-color': style.color, 'line-width': 2 },
          filter: ['==', ['get', 'category'], cat],
        })
      }

      mapRef.current.on('mousemove', fillId, (e) => {
        const f = e.features && e.features[0]
        if (!f) return
        const { plant, start_date, end_date, t2m, rh2m } = f.properties
        const label = CATEGORY_STYLES[cat].label
        const html = `
          <div style="font-size:12px">
            <div><b>${label}</b></div>
            <div>Planta: ${plant || '—'}</div>
            <div>Inicio: ${start_date || '—'} | Fin: ${end_date || '—'}</div>
            <div>LST: ${t2m ?? '—'} °C</div>
            <div>Humedad: ${rh2m ?? '—'} %</div>
          </div>`
        popupRef.current.setLngLat(e.lngLat).setHTML(html).addTo(mapRef.current)
      })
      mapRef.current.on('mouseleave', fillId, () => popupRef.current.remove())
    })
  }

  // Apply visibility changes
  useEffect(() => {
    if (!mapRef.current) return
    Object.keys(CATEGORY_STYLES).forEach((cat) => {
      const fillId = `fill-${cat}`
      const lineId = `line-${cat}`
      if (mapRef.current.getLayer(fillId)) {
        mapRef.current.setLayoutProperty(fillId, 'visibility', visibleCategories[cat] ? 'visible' : 'none')
      }
      if (mapRef.current.getLayer(lineId)) {
        mapRef.current.setLayoutProperty(lineId, 'visibility', visibleCategories[cat] ? 'visible' : 'none')
      }
    })
  }, [visibleCategories])

  useEffect(() => { refreshZones() }, [useMock, plant, season])

  function toggleCategory(cat) {
    setVisibleCategories((prev) => ({ ...prev, [cat]: !prev[cat] }))
  }

  function recenterToUser() {
    if (!mapRef.current || !userMarkerRef.current) return
    const ll = userMarkerRef.current.getLngLat()
    mapRef.current.flyTo({ center: ll, zoom: 12 })
  }

  async function geocodeRegion(name) {
    if (!name) return
    try {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(name)}.json?access_token=${mapboxgl.accessToken}&country=bo&language=es`
      const { data } = await axios.get(url)
      const feat = data.features && data.features[0]
      if (feat && feat.bbox) {
        const [minx, miny, maxx, maxy] = feat.bbox
        mapRef.current.fitBounds([[minx, miny], [maxx, maxy]], { padding: 24 })
      } else if (feat && feat.center) {
        mapRef.current.flyTo({ center: feat.center, zoom: 9 })
      }
    } catch (e) {
      console.error('Geocode error', e)
    }
  }

  function parseCoords(input) {
    const m = input.split(',').map(s => s.trim())
    if (m.length === 2) {
      const lat = parseFloat(m[0])
      const lon = parseFloat(m[1])
      if (!Number.isNaN(lat) && !Number.isNaN(lon)) return { lat, lon }
    }
    return null
  }

  async function onSearchSubmit(e) {
    e.preventDefault()
    const parsed = parseCoords(search)
    if (parsed) {
      setCoords(parsed)
      mapRef.current.flyTo({ center: [parsed.lon, parsed.lat], zoom: 10 })
      return
    }
    await geocodeRegion(search)
  }

  function onApplyFilters() {
    if (region) geocodeRegion(region)
    refreshZones()
  }

  return (
    <div style={{ display: 'grid', gridTemplateRows: '64px 1fr', height: '100vh' }}>
      {/* Top Bar with filters */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', gap: 8, borderBottom: '1px solid #ddd', background: '#fff', zIndex: 2 }}>
        <div style={{ fontFamily: 'monospace', minWidth: 220 }}>
          Lat: {coords.lat.toFixed(5)} | Lon: {coords.lon.toFixed(5)}
        </div>
        <form onSubmit={onSearchSubmit} style={{ display: 'flex', gap: 6, flex: 1, maxWidth: 620 }}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar: 'La Paz' o '-16.5,-68.15'" style={{ flex: 1, padding: '6px 8px' }} />
          <button type="submit" style={{ padding: '6px 10px' }}>Buscar</button>
        </form>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input type='checkbox' checked={useMock} onChange={e => setUseMock(e.target.checked)} />
          Demo
        </label>
        <select value={plant} onChange={e => setPlant(e.target.value)} title="Tipo de planta" style={{ padding: '6px 8px' }}>
          <option value='-'>Todas</option>
          <option value='soya'>Soya</option>
          <option value='maiz'>Maíz</option>
          <option value='trigo'>Trigo</option>
          <option value='cafe'>Café</option>
        </select>
        <input value={region} onChange={e => setRegion(e.target.value)} placeholder="Región (Departamento/Provincia)" style={{ padding: '6px 8px', minWidth: 220 }} />
        <select value={season} onChange={e => setSeason(e.target.value)} title="Temporada" style={{ padding: '6px 8px' }}>
          {Object.keys(SEASONS).map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={onApplyFilters} title="Aplicar filtros" style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: 4, padding: '6px 10px', cursor: 'pointer' }}>Aplicar</button>
          <button onClick={recenterToUser} title="Centrar en mi ubicación" style={{ background: '#007aff', color: '#fff', border: 'none', borderRadius: 4, padding: '6px 10px', cursor: 'pointer' }}>Centrar</button>
          <button onClick={() => setSettingsOpen((s) => !s)} title="Configuración" style={{ background: 'transparent', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', padding: '4px 8px' }}>⚙️</button>
        </div>
        {settingsOpen && (
          <div style={{ position: 'absolute', top: 64, right: 12, background: '#fff', border: '1px solid #ddd', borderRadius: 6, padding: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 3 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Capas visibles</div>
            {Object.entries(CATEGORY_STYLES).map(([cat, style]) => (
              <label key={cat} style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '6px 0' }}>
                <input type="checkbox" checked={visibleCategories[cat]} onChange={() => toggleCategory(cat)} />
                <span style={{ width: 12, height: 12, background: style.color, display: 'inline-block', border: '1px solid #888' }} />
                <span>{style.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Map */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}
