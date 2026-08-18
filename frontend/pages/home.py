"""
Página de Inicio: visualización del grafo y estadísticas.
"""

import streamlit as st
from graph_visualizer import render_graph
from api_client import fetch_full_graph, get_graph_stats


def render():
    st.markdown("""
    Bienvenido al sistema de conocimiento médico.
    Explora el grafo de ensayos clínicos o haz preguntas en la pestaña **💬 Chat RAG**.
    """)
    
    # ─── Indicador de capacidad del grafo ───
    try:
        stats = get_graph_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nodos en el grafo", f"{stats['node_count']:,}")
            st.progress(min(stats['node_percentage'] / 100, 1.0))
            st.caption(f"{stats['node_percentage']}% del límite")
        with col2:
            st.metric("Relaciones", f"{stats['rel_count']:,}")
            st.progress(min(stats['rel_percentage'] / 100, 1.0))
            st.caption(f"{stats['rel_percentage']}% del límite")
        with col3:
            if stats['is_at_limit']:
                st.error("🚫 Grafo al límite")
            elif stats['is_near_limit']:
                st.warning(f"⚠️ {stats['overall_percentage']}% usado")
            else:
                st.success("✅ Capacidad OK")
            st.caption("Estado del free tier")
    except Exception as e:
        st.warning(f"No se pudo obtener estadísticas: {e}")
    
    st.divider()
    
    # ─── Grafo interactivo ───
    st.subheader("🔗 Grafo de Conocimiento")
    
    if "current_graph" not in st.session_state:
        try:
            st.session_state.current_graph = fetch_full_graph()
            st.session_state.graph_source = "full"
        except Exception as e:
            st.error(f"Error cargando el grafo: {e}")
            return
    
    graph_data = st.session_state.current_graph
    
    if graph_data.get("nodes"):
        render_graph(graph_data, height=600, physics=True)
        
        if st.session_state.graph_source == "query":
            st.info("💡 Mostrando subgrafo de una consulta. Importa más ensayos en la pestaña **🧪 Ensayos Clínicos**.")
            if st.button("🔄 Ver grafo completo"):
                st.session_state.current_graph = fetch_full_graph()
                st.session_state.graph_source = "full"
                st.rerun()
    else:
        st.info("No hay datos en el grafo. Importa ensayos en la pestaña **🧪 Ensayos Clínicos**.")