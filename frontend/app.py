"""
Router principal de la aplicación Streamlit.
Usa st.tabs para navegación por pestañas.
"""

import streamlit as st

st.set_page_config(
    page_title="GraphRAG Medical Knowledge",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 GraphRAG: Ensayos Clínicos de Cáncer de Mama")

# ─── Sidebar con información del sistema ───
with st.sidebar:
    st.header("ℹ️ Sistema")
    st.markdown("""
    - **Modelo:** GPT-4o-mini
    - **Base de datos:** Neo4j AuraDB
    - **Fuente:** ClinicalTrials.gov
    - **Versión:** 2.0 (v2)
    """)
    st.caption("© 2026 · Jose Maria Galvez")

# ─── Navegación por pestañas ───
tab_home, tab_trials, tab_papers, tab_guides, tab_chat = st.tabs([
    "🏠 Inicio",
    "🧪 Ensayos Clínicos",
    "📄 Papers (próximamente)",
    "📚 Guías (próximamente)",
    "💬 Chat RAG",
])

with tab_home:
    from pages.home import render
    render()

with tab_trials:
    from pages.trials import render
    render()

with tab_papers:
    from pages.papers import render
    render()

with tab_guides:
    from pages.guides import render
    render()

with tab_chat:
    from pages.chat import render
    render()