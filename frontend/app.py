# frontend/app.py
import streamlit as st
import requests
import os
from graph_visualizer import render_graph, fetch_full_graph

# Configuración de la página
st.set_page_config(
    page_title="GraphRAG Medical Knowledge",
    page_icon="🩺",
    layout="wide"
)

# URL de la API (nombre del servicio dentro de la red Docker)
API_URL = os.getenv("API_URL", "http://api:8000/query")

st.title("🩺 GraphRAG: Ensayos Clínicos de Cáncer de Mama")
st.markdown("""
Bienvenido al sistema de conocimiento médico.
Haz preguntas sobre fármacos, ensayos clínicos y biomarcadores.
""")

# Sidebar con información del sistema
with st.sidebar:
    st.header("ℹ️ Sobre el Sistema")
    st.markdown("""
    - **Modelo:** GPT-4o-mini
    - **Base de datos:** Neo4j AuraDB
    - **Fuente:** ClinicalTrials.gov
    """)

    if st.button("🔍 Verificar conexión API"):
        try:
            health_url = API_URL.replace("/query", "/health")
            res = requests.get(health_url)
            if res.status_code == 200:
                st.success("✅ API conectada correctamente")
            else:
                st.error("❌ La API respondió con error")
        except Exception as e:
            st.error(f"❌ No se pudo conectar: {e}")

st.divider()

# --- Gestión del estado del grafo ---
if "current_graph" not in st.session_state:
    # Cargar grafo completo al iniciar
    st.session_state.current_graph = fetch_full_graph(API_URL)
    st.session_state.graph_source = "full"

# --- Pregunta principal ---
question = st.text_input(
    "¿Qué deseas consultar hoy?",
    key="question_input",
    placeholder="Ej: ¿Qué fármacos se están probando para cáncer de mama?"
)

# Disparador: botón principal O clic en un ejemplo
run_query = st.button("🚀 Consultar Grafo", type="primary") or st.session_state.pop("auto_ask", False)

if run_query:
    if question:
        with st.spinner("Analizando pregunta y consultando Neo4j..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"question": question},
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    st.success("Respuesta generada:")
                    st.info(data["answer"])
                    
                    # Actualizar grafo con el subgrafo de la consulta
                    if data.get("graph", {}).get("nodes"):
                        st.session_state.current_graph = data["graph"]
                        st.session_state.graph_source = "query"
                    else:
                        st.warning("No se encontraron relaciones gráficas para esta pregunta.")
                        
                else:
                    st.error(f"Error de la API (Código {response.status_code}): {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("No se pudo conectar con la API. ¿Está el contenedor 'api' corriendo?")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
    else:
        st.warning("Por favor, escribe una pregunta antes de consultar.")

# --- Botón para volver al grafo completo ---
if st.session_state.graph_source == "query":
    st.divider()
    if st.button("🔄 Ver grafo completo"):
        st.session_state.current_graph = fetch_full_graph(API_URL)
        st.session_state.graph_source = "full"
        st.rerun()

# --- Visualización del grafo ---
st.divider()
st.subheader(f"🔗 Grafo de Conocimiento ({st.session_state.graph_source})")

if st.session_state.current_graph.get("nodes"):
    render_graph(st.session_state.current_graph, height=600, physics=True)
else:
    st.info("No hay datos en el grafo. Ejecuta el pipeline de ingesta primero.")

# --- Ejemplos rápidos ---
st.divider()
st.subheader("💡 Prueba con estos ejemplos:")
col1, col2, col3 = st.columns(3)

EXAMPLES = [
    ("Fármacos para cáncer de mama", "¿Qué fármacos se están probando para cáncer de mama?"),
    ("Ensayos de Abemaciclib", "¿Qué ensayos clínicos prueban Abemaciclib?"),
    ("Detalles NCT02689427", "Dame detalles del ensayo NCT02689427"),
]


def load_example(q: str):
    """Callback de los botones de ejemplo."""
    st.session_state["question_input"] = q
    st.session_state["auto_ask"] = True


for col, (label, q) in zip([col1, col2, col3], EXAMPLES):
    with col:
        st.button(label, on_click=load_example, args=(q,))