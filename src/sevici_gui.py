import requests
from pathlib import Path
from collections import namedtuple
import folium
from folium.plugins import MarkerCluster
import webview  
from sevici_utiles import *

SEVILLE_CENTER = (37.3891, -5.9845)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
HTML_PATH = TMP_DIR / "sevici_mapa.html"

API_KEY = "1fc3a06635799dc2c36dc69818ba8d4606251a92"
def obtener_estaciones_sevici():
    """
    Consulta la API de JCDecaux para obtener todas las estaciones de Sevici 
    y devuelve una lista de objetos EstacionSevici.
    """
    url = f"https://api.jcdecaux.com/vls/v1/stations?contract=Seville&apiKey={API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    estaciones = []
    for e in data:
        try:
            nombre = e.get("name", "").strip()
            direccion = e.get("address", "").strip()
            latitud = float(e.get("position", {}).get("lat", 0.0))
            longitud = float(e.get("position", {}).get("lng", 0.0))
            capacidad = int(e.get("bike_stands", 0))
            puestos_libres = int(e.get("available_bike_stands", 0))
            bicicletas_disponibles = int(e.get("available_bikes", 0))
            
            estaciones.append(
                EstacionSevici(
                    nombre, direccion, latitud, longitud, 
                    capacidad, puestos_libres, bicicletas_disponibles
                )
            )
        except Exception as ex:
            print(f"[Aviso] No se pudo procesar una estación: {ex}")

    return estaciones


def build_map_html(
    estaciones, 
    out_html_path: Path, 
    stats=None, 
    current_filter_value=0, 
    current_search_query="", 
    current_zoom=None, 
    current_center=None,
    ruta: dict = None
):
    """Construye el mapa Folium y lo guarda como HTML, preservando la vista y mostrando estadísticas y la ruta."""

    if current_zoom and current_center:
        m = folium.Map(location=current_center, zoom_start=current_zoom, control_scale=True, tiles="OpenStreetMap")
    else:
        m = folium.Map(location=SEVILLE_CENTER, zoom_start=12, control_scale=True, tiles="OpenStreetMap")

    if ruta and ruta.get('inicio') and ruta.get('fin'):
        est_inicio = ruta['inicio']
        est_fin = ruta['fin']
        
        folium.Marker(
            location=(float(est_inicio.latitud), float(est_inicio.longitud)),
            popup=f"<b>✅ Inicio Recomendado:</b><br>{est_inicio.nombre}<br>Bicis: {est_inicio.bicicletas_disponibles}",
            tooltip="Coge tu bici aquí",
            icon=folium.Icon(color='green', icon='play', prefix='fa', icon_color='white')
        ).add_to(m)

        folium.Marker(
            location=(float(est_fin.latitud), float(est_fin.longitud)),
            popup=f"<b>🏁 Fin Recomendado:</b><br>{est_fin.nombre}<br>Sitios libres: {est_fin.puestos_libres}",
            tooltip="Deja tu bici aquí",
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa', icon_color='white')
        ).add_to(m)
        
        folium.PolyLine(
            locations=[
                (float(est_inicio.latitud), float(est_inicio.longitud)),
                (float(est_fin.latitud), float(est_fin.longitud))
            ],
            color='#3498db', weight=5, opacity=0.9,
            tooltip="Ruta en bicicleta recomendada"
        ).add_to(m)

        if ruta.get('puntos_usuario'):
            p_inicio_usr, p_fin_usr = ruta['puntos_usuario']
            folium.PolyLine(
                locations=[p_inicio_usr, (float(est_inicio.latitud), float(est_inicio.longitud))],
                color='gray', weight=3, opacity=0.8, dash_array='5, 10', tooltip="Camino a la estación de origen"
            ).add_to(m)
            folium.PolyLine(
                locations=[(float(est_fin.latitud), float(est_fin.longitud)), p_fin_usr],
                color='gray', weight=3, opacity=0.8, dash_array='5, 10', tooltip="Camino desde la estación de destino"
            ).add_to(m)


    mc = MarkerCluster(name="Estaciones").add_to(m)
    bounds = []
    for est in estaciones:
        popup_html = (
            f"<b>{est.nombre}</b><br>"
            f"Dirección: {est.direccion}<br>"
            f"Capacidad: {int(est.capacidad)}<br>"
            f"Bicicletas disponibles: {int(est.bicicletas_disponibles)}<br>"
            f"Puestos libres: {int(est.puestos_libres)}<br>"
            f"Lat/Lon: {float(est.latitud):.6f}, {float(est.longitud):.6f}"
        )
        folium.Marker(
            location=(float(est.latitud), float(est.longitud)),
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=est.nombre,
            icon=folium.Icon(color=selecciona_color(est), icon="bicycle", prefix="fa"),
        ).add_to(mc)
        bounds.append((float(est.latitud), float(est.longitud)))

    if bounds and not current_zoom:
        m.fit_bounds(bounds, padding=(20, 20))

    folium.LayerControl().add_to(m)
    map_js_name = m.get_name()
    
    # --- JavaScript ---
    map_js = f"""
        let routeMode = false;
        let originPoint = null;
        let map = null;

        function reloadMap(htmlContent) {{
            document.open();
            document.write(htmlContent);
            document.close();
            setTimeout(initializeMapInteraction, 200);
        }}

        function initializeMapInteraction() {{
            map = window.{map_js_name};
            if (map) {{
                map.on('click', function(e) {{
                    if (!routeMode) return;
                    
                    if (!originPoint) {{
                        originPoint = e.latlng;
                        document.getElementById('route-status').innerText = 'Origen seleccionado. Haz clic para el destino.';
                    }} else {{
                        const destinationPoint = e.latlng;
                        document.getElementById('route-status').innerText = 'Calculando ruta...';
                        seviciPlanRoute([originPoint.lat, originPoint.lng], [destinationPoint.lat, destinationPoint.lng]);
                        toggleRouteMode(false);
                    }}
                }});
            }} else {{
                setTimeout(initializeMapInteraction, 100);
            }}
        }}

        setTimeout(initializeMapInteraction, 200);

        function seviciRefresh(){{
            if (window.pywebview && window.pywebview.api){{
                window.pywebview.api.refresh().then(function(result){{
                    if(result.ok){{ reloadMap(result.html); }} 
                    else {{ alert('Error: ' + result.error); }}
                }}).catch(function(err){{ alert('Error en llamada: ' + err); }});
            }} else {{ alert('Interfaz pywebview no disponible.'); }}
        }}

        function updateSliderValue(value) {{
            document.getElementById('slider-value').textContent = value;
        }}
        
        function seviciApplyFilters() {{
            if (!window.pywebview || !window.pywebview.api || !map) {{
                alert('Interfaz pywebview o mapa no disponible.'); return;
            }}
            const zoom = map.getZoom();
            const center = map.getCenter();
            const searchValue = document.getElementById('address-search-input').value;
            const sliderValue = document.getElementById('availability-slider').value;

            window.pywebview.api.apply_filters(searchValue, sliderValue, zoom, [center.lat, center.lng]).then(function(result){{
                if(result.ok){{ reloadMap(result.html); }} 
                else {{ alert('Error: ' + result.error); }}
            }}).catch(function(err){{ alert('Error en llamada: ' + err); }});
        }}

        function handleSearchKey(event) {{
            if (event.key === 'Enter') {{ seviciApplyFilters(); }}
        }}

        function toggleRouteMode(forceState) {{
            routeMode = (forceState !== undefined) ? forceState : !routeMode;
            const routeBtn = document.getElementById('route-btn');
            const routeStatus = document.getElementById('route-status');
            const mapContainer = map ? map.getContainer() : null;

            if (routeMode) {{
                originPoint = null;
                routeBtn.style.backgroundColor = '#28a745';
                routeBtn.style.color = 'white';
                routeStatus.innerText = 'Haz clic en el mapa para seleccionar el origen.';
                if(mapContainer) mapContainer.style.cursor = 'crosshair';
            }} else {{
                routeBtn.style.backgroundColor = '';
                routeBtn.style.color = '';
                routeStatus.innerText = '';
                if(mapContainer) mapContainer.style.cursor = '';
            }}
        }}

        function seviciPlanRoute(origin, destination) {{
             if (!window.pywebview || !window.pywebview.api || !map) {{
                alert('Interfaz pywebview o mapa no disponible.'); return;
            }}
            const zoom = map.getZoom();
            const center = map.getCenter();
            const searchValue = document.getElementById('address-search-input').value;
            const sliderValue = document.getElementById('availability-slider').value;

            window.pywebview.api.plan_route(origin, destination, searchValue, sliderValue, zoom, [center.lat, center.lng]).then(function(result){{
                if(result.ok){{ reloadMap(result.html); }} 
                else {{ alert('Error al calcular la ruta: ' + result.error); }}
            }}).catch(function(err){{ alert('Error en llamada: ' + err); }});
        }}

        function seviciClearRoute() {{
             if (!window.pywebview || !window.pywebview.api || !map) {{
                alert('Interfaz pywebview o mapa no disponible.'); return;
            }}
            const zoom = map.getZoom();
            const center = map.getCenter();
            const searchValue = document.getElementById('address-search-input').value;
            const sliderValue = document.getElementById('availability-slider').value;
            
            window.pywebview.api.clear_route(searchValue, sliderValue, zoom, [center.lat, center.lng]).then(function(result){{
                if(result.ok){{ reloadMap(result.html); }}
                else {{ alert('Error al limpiar la ruta: ' + result.error); }}
            }}).catch(function(err){{ alert('Error en llamada: ' + err); }});
        }}
    """
    map_css = """
        .sevici-refresh-btn {
            position: absolute; bottom: 12px; right: 12px; z-index: 9999;
            background: white; border: 1px solid #ccc; border-radius: 6px;
            padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            cursor: pointer; font-family: system-ui, sans-serif; font-size: 14px;
        }
        .sevici-refresh-btn:hover { background: #f5f5f5; }
        .sevici-controls-container {
            position: absolute; bottom: 12px; left: 12px; z-index: 9999;
            background: white; border: 1px solid #ccc; border-radius: 6px;
            padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: system-ui, sans-serif; font-size: 14px;
            display: flex; align-items: center; gap: 10px;
        }
        .sevici-controls-container label { white-space: nowrap; }
        .sevici-controls-container input[type=range] { width: 150px; }
        .sevici-stats-panel {
            position: absolute; top: 100px; left: 12px; z-index: 9999;
            background: white; border: 1px solid #ccc; border-radius: 6px;
            padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: system-ui, sans-serif; font-size: 14px;
        }
        .sevici-stats-panel h4 { margin: 0 0 5px 0; padding: 0; }
        .sevici-stats-panel p { margin: 3px 0; padding: 0; }
        .sevici-search-container {
            position: absolute; top: 12px; right: 100px; z-index: 9999;
            background: white; border: 1px solid #ccc; border-radius: 6px;
            padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: system-ui, sans-serif; font-size: 14px;
            display: flex; align-items: center; gap: 8px;
        }
        .sevici-search-container input {
            border: 1px solid #ccc; padding: 4px; border-radius: 4px;
        }
        .sevici-search-container button {
            padding: 4px 10px; cursor: pointer;
        }
        .sevici-route-container {
            position: absolute; top: 12px; left: 12px; z-index: 9999;
            background: white; border: 1px solid #ccc; border-radius: 6px;
            padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: system-ui, sans-serif; font-size: 14px;
            display: flex; align-items: center; gap: 8px;
        }
        .sevici-route-container button { padding: 4px 10px; cursor: pointer; }
        #route-status { font-style: italic; color: #555; }
        #clear-route-btn { display: none; } /* Oculto por defecto */
    """
    
    refresh_html = '<div class="sevici-refresh-btn" onclick="seviciRefresh()">⟳ Refrescar</div>'

    slider_html = f"""
    <div class="sevici-controls-container">
        <label for="availability-slider">Disponibilidad Mínima: <span id="slider-value">{current_filter_value}</span>%</label>
        <input type="range" min="0" max="100" value="{current_filter_value}" id="availability-slider" 
               oninput="updateSliderValue(this.value)" onchange="seviciApplyFilters()">
    </div>
    """
    
    search_html = f"""
    <div class="sevici-search-container">
        <label for="address-search-input">Buscar Dirección:</label>
        <input type="search" id="address-search-input" value="{current_search_query}" onkeydown="handleSearchKey(event)" placeholder="Ej: Av. Constitución">
        <button onclick="seviciApplyFilters()">🔍</button>
    </div>
    """

    clear_btn_style = "display: inline-block;" if ruta else "display: none;"
    route_html = f"""
    <div class="sevici-route-container">
        <button id="route-btn" onclick="toggleRouteMode()">🗺️ Planificar Ruta</button>
        <button id="clear-route-btn" onclick="seviciClearRoute()" style="{clear_btn_style}">❌ Limpiar Ruta</button>
        <span id="route-status"></span>
    </div>
    """

    stats_html = ""
    if stats:
        bicis, capacidad, ocupacion, total_est = stats
        stats_html = f"""
        <div class="sevici-stats-panel">
            <h4>Estadísticas (Vista Actual)</h4>
            <p><b>Estaciones mostradas:</b> {total_est}</p>
            <p><b>Bicicletas disponibles:</b> {bicis}</p>
            <p><b>Capacidad total:</b> {capacidad}</p>
            <p><b>Ocupación:</b> {ocupacion:.1f}%</p>
        </div>
        """
        
    from branca.element import Element
    m.get_root().header.add_child(Element(f"<style>{map_css}</style>"))
    m.get_root().header.add_child(Element(f"<script>{map_js}</script>"))
    m.get_root().html.add_child(Element(refresh_html))
    m.get_root().html.add_child(Element(slider_html))
    m.get_root().html.add_child(Element(stats_html))
    m.get_root().html.add_child(Element(search_html))
    m.get_root().html.add_child(Element(route_html))

    m.save(str(out_html_path))
    return out_html_path

class ApiBridge:
    """Puente Python <-> JS para pywebview."""
    def __init__(self, html_path: Path):
        self.html_path = html_path
        self.window = None
        self.all_stations = []
        self.current_route = None 

    def set_window(self, window):
        self.window = window

    def refresh(self):
        """Llamado desde JS: vuelve a consultar la API y recarga el mapa completo."""
        try:
            self.all_stations = obtener_estaciones_sevici()
            self.current_route = None 
            stats = calcula_estadisticas(self.all_stations)
            build_map_html(self.all_stations, self.html_path, stats=stats)
            html_str = self.html_path.read_text(encoding='utf-8')
            if self.window:
                self.window.set_title(f"Sevici - {len(self.all_stations)} estaciones")
                self.window.load_html(html_str) # Soluciona el problema con Planificar Ruta, pero provoca en error
            return {"ok": True, "count": len(self.all_stations), "html": html_str}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apply_filters(self, search_query: str, min_percentage_str: str, zoom: int, center: list):
        """Llamado desde JS: filtra las estaciones, manteniendo la ruta si existe."""
        if not self.all_stations:
            return {"ok": False, "error": "No hay datos de estaciones. Refresca primero."}

        try:
            stations_to_filter = self.all_stations
            if search_query:
                stations_to_filter = busca_estaciones_direccion(stations_to_filter, search_query)

            min_percentage = int(min_percentage_str)
            min_disponibilidad = min_percentage / 100.0
            filtered_list = busca_estaciones_con_disponibilidad(stations_to_filter, min_disponibilidad)
            
            stats = calcula_estadisticas(filtered_list)
            
            build_map_html(
                filtered_list, self.html_path,
                stats=stats,
                current_filter_value=min_percentage,
                current_search_query=search_query,
                current_zoom=zoom, current_center=center,
                ruta=self.current_route 
            )
            html_str = self.html_path.read_text(encoding='utf-8')
            if self.window:
                self.window.set_title(f"Sevici - Mostrando {len(filtered_list)}/{len(self.all_stations)} estaciones")
                self.window.load_html(html_str) # Soluciona el problema con Planificar Ruta, pero provoca en error
            return {"ok": True, "count": len(filtered_list), "html": html_str}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def plan_route(self, origin: list, destination: list, search_query: str, min_percentage_str: str, zoom: int, center: list):
        """Calcula la ruta óptima y la muestra en el mapa."""
        if not self.all_stations:
            return {"ok": False, "error": "No hay datos de estaciones. Refresca primero."}
        try:
            est_inicio, est_fin = calcula_ruta(self.all_stations, tuple(origin), tuple(destination))
            
            if not est_inicio or not est_fin:
                return {"ok": False, "error": "No se encontraron estaciones disponibles para la ruta solicitada."}

            self.current_route = {
                'inicio': est_inicio,
                'fin': est_fin,
                'puntos_usuario': [tuple(origin), tuple(destination)]
            }
            
            return self.apply_filters(search_query, min_percentage_str, zoom, center)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": f"Error interno al calcular la ruta: {e}"}

    def clear_route(self, search_query: str, min_percentage_str: str, zoom: int, center: list):
        """Limpia la ruta actual y redibuja el mapa."""
        self.current_route = None
        return self.apply_filters(search_query, min_percentage_str, zoom, center)


def main():
    api = ApiBridge(HTML_PATH)
    window = webview.create_window(
        title="Sevici - Cargando estaciones...",
        html="<h1>Cargando mapa, por favor espere...</h1>",
        width=1100, height=750, resizable=True, confirm_close=False,
    )
    api.set_window(window)
    window.expose(api.refresh)
    window.expose(api.apply_filters)
    window.expose(api.plan_route)
    window.expose(api.clear_route)
    
    def initial_load():
        result = api.refresh()
        if result['ok']:
            window.load_html(result['html'])

    webview.start(initial_load, gui='tk', http_server=False, debug=False)


if __name__ == "__main__":
    main()