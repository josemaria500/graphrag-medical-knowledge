"""
Página de Chat RAG: preguntas en lenguaje natural al grafo.
"""

import streamlit as st
from api_client import query_rag
from graph_visualizer import render_graph


def render():
    st.markdown("""
    Haz preguntas en lenguaje natural sobre los ensayos clínicos del grafo.
    """)
    
    # Pregunta
    question = st.text_input(
        "¿Qué deseas consultar?",
        placeholder="Ej: ¿Qué fármacos se están probando para cáncer de mama?",
        key="chat_question"
    )
    
    if st.button("🚀 Consultar", type="primary"):
        if not question:
            st.warning("Escribe una pregunta primero.")
            return
        
        with st.spinner("Analizando pregunta y consultando Neo4j..."):
            try:
                result = query_rag(question)
                st.success("Respuesta:")
                st.info(result["answer"])
                
                if result.get("graph", {}).get("nodes"):
                    st.session_state.last_graph = result["graph"]
                else:
                    st.warning("No se encontraron relaciones gráficas.")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Mostrar grafo de la última consulta
    if "last_graph" in st.session_state and st.session_state.last_graph.get("nodes"):
        st.divider()
        st.subheader("🔗 Subgrafo de la consulta")
        render_graph(st.session_state.last_graph, height=500, physics=True)
    
    # Ejemplos rápidos
    st.divider()
    st.markdown("### 💡 Prueba con estos ejemplos:")
    
    examples = [
        "¿Qué fármacos se están probando para cáncer de mama?",
        "¿Qué ensayos clínicos prueban Abemaciclib?",
        "Dame detalles del ensayo NCT02689427",
    ]
    cols = st.columns(len(examples))
    for col, ex in zip(cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state.chat_question = ex
            st.rerun()