"""
Visualizador de grafo usando Streamlit nativo
"""

import streamlit as st
import pandas as pd
import requests


def fetch_full_graph(api_base: str, limit: int = 200) -> dict:
    """
    Obtiene el grafo completo desde la API.
    """
    try:
        response = requests.get(f"{api_base}/graph", params={"limit": limit}, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error obteniendo el grafo: {e}")
        return {"nodes": [], "links": []}


def render_graph(graph_data: dict, height: int = 600, physics: bool = True):
    """
    Renderiza el grafo usando tablas de Streamlit (compatible con CPUs antiguas).
    
    Args:
        graph_data: Dict con 'nodes' y 'links'
        height: Altura de la visualización (no usado, mantenido por compatibilidad)
        physics: Si usar física (no usado, mantenido por compatibilidad)
    """
    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    
    if not nodes:
        st.info("No hay datos en el grafo.")
        return
    
    st.markdown(f"**{len(nodes)} nodos · {len(links)} relaciones**")
    
    # ─── Tabla de nodos ───
    st.subheader("🔵 Nodos")
    
    if nodes:
        df_nodes = pd.DataFrame([
            {
                "ID": node.get("id", ""),
                "Tipo": node.get("label", node.get("type", "")),
                "Fuente": node.get("source", "N/A"),
            }
            for node in nodes
        ])
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)
    
    # ─── Tabla de relaciones ───
    if links:
        st.subheader("🔗 Relaciones")
        df_links = pd.DataFrame([
            {
                "Origen": link.get("source", ""),
                "Tipo": link.get("rel", ""),
                "Destino": link.get("target", ""),
            }
            for link in links
        ])
        st.dataframe(df_links, use_container_width=True, hide_index=True)
    
    # ─── Estadísticas del grafo ───
    st.subheader("📊 Estadísticas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Contar tipos de nodos
        node_types = {}
        for node in nodes:
            label = node.get("label", node.get("type", "Unknown"))
            node_types[label] = node_types.get(label, 0) + 1
        st.write("**Tipos de nodos:**")
        for tipo, count in sorted(node_types.items()):
            st.write(f"- {tipo}: {count}")
    
    with col2:
        # Contar tipos de relaciones
        rel_types = {}
        for link in links:
            rel = link.get("rel", "Unknown")
            rel_types[rel] = rel_types.get(rel, 0) + 1
        st.write("**Tipos de relaciones:**")
        for tipo, count in sorted(rel_types.items()):
            st.write(f"- {tipo}: {count}")
    
    with col3:
        # Contar por fuente
        sources = {}
        for node in nodes:
            source = node.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        st.write("**Por fuente:**")
        for fuente, count in sorted(sources.items()):
            icon = "🔵" if fuente == "demo" else "🟢"
            st.write(f"- {icon} {fuente}: {count}")