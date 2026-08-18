# frontend/pages/papers.py
import streamlit as st

def render():
    st.markdown("## 📄 Papers Científicos")
    st.info("🚧 Próximamente: importación de papers desde PubMed y bioRxiv.")
    st.markdown("""
    **Funcionalidades planeadas:**
    - Búsqueda por DOI, título o autor
    - Extracción automática de entidades (genes, proteínas, enfermedades)
    - Integración con el grafo existente
    """)