# frontend/graph_visualizer.py
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components


# Colores por tipo de nodo
COLOR_MAP = {
    "ClinicalTrial": "#3498db",  # Azul
    "Drug": "#2ecc71",           # Verde
    "Disease": "#e74c3c",        # Rojo
    "Biomarker": "#f39c12",      # Naranja
    "Intervention": "#9b59b6",   # Morado
}


def render_graph(graph_data: dict, height: int = 500, physics: bool = True):
    """
    Renderiza un grafo interactivo en Streamlit usando pyvis.
    
    Args:
        graph_data: dict con {"nodes": [...], "links": [...]}
        height: altura del iframe en píxeles
        physics: si True, activa la física de repulsión
    """
    if not graph_data.get("nodes"):
        st.warning("No hay datos de grafo para mostrar.")
        return
    
    # Crear red
    net = Network(height=f"{height}px", width="100%", bgcolor="#ffffff", font_color="#333333")
    
    # Añadir nodos
    for node in graph_data["nodes"]:
        node_type = node.get("type", "Unknown")
        color = COLOR_MAP.get(node_type, "#95a5a6")  # Gris por defecto
        
        net.add_node(
            node["id"],
            label=node.get("label", node["id"]),
            color=color,
            title=f"{node_type}: {node['id']}",  # Tooltip al hacer hover
            size=25 if node_type == "ClinicalTrial" else 20,  # Trials más grandes
        )
    
    # Añadir enlaces
    for link in graph_data.get("links", []):
        net.add_edge(
            link["source"],
            link["target"],
            title=link.get("rel", ""),  # Tooltip con tipo de relación
            label=link.get("rel", ""),  # Etiqueta en la línea
            color="#bdc3c7",
            width=2,
        )
    
    # Configurar física
    if physics:
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 150,
              "springConstant": 0.08
            },
            "stabilization": {
              "enabled": true,
              "iterations": 150
            }
          }
        }
        """)
    
    # Generar HTML
    html_string = net.generate_html()
    
    # Incrustar en Streamlit
    components.html(html_string, height=height, scrolling=True)


@st.cache_data(ttl=3600)  # Cache por 1 hora
def fetch_full_graph(api_url: str) -> dict:
    """
    Obtiene el grafo completo desde la API.
    Cacheado para no golpear Neo4j en cada rerun.
    """
    import requests
    
    try:
        graph_url = api_url.replace("/query", "/graph")
        response = requests.get(graph_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"nodes": [], "links": []}
    except Exception as e:
        st.error(f"Error al cargar el grafo: {e}")
        return {"nodes": [], "links": []}