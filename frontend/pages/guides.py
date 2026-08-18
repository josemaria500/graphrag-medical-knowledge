# frontend/pages/guides.py
import streamlit as st

def render():
    st.markdown("## 📚 Guías Clínicas")
    st.info("🚧 Próximamente: importación de guías clínicas (NCCN, ESMO, WHO...).")
    st.markdown("""
    **Funcionalidades planeadas:**
    - Subida de PDFs
    - Extracción de recomendaciones clínicas
    - Relación con ensayos clínicos existentes
    """)