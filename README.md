#  GraphRAG: Ensayos Clínicos de Cáncer de Mama

Sistema de **Retrieval Augmented Generation (GraphRAG)** diseñado para responder preguntas complejas y de múltiples saltos (multi-hop) sobre ensayos clínicos de cáncer de mama. Combina la búsqueda estructurada de un Grafo de Conocimiento (Neo4j) con la síntesis de lenguaje natural de LLMs, superando las limitaciones del RAG vectorial tradicional en dominios médicos.

---

## ✨ Características Clave

- **Ontología Médica Unificada:** Modelo de grafo diseñado para conectar Fármacos, Ensayos Clínicos, Enfermedades y Biomarcadores, permitiendo razonamiento multi-salto.
- **Patrón Repositorio:** Capa de abstracción de la base de datos que permite migrar de Neo4j AuraDB (Cloud) a Neo4j Community (Self-hosted) sin modificar la lógica de negocio.
- **Query Understanding con LLM:** Módulo que traduce preguntas en lenguaje natural a entidades estructuradas, manejando sinónimos y múltiples idiomas.
- **Evaluación Automatizada (LLM-as-a-Judge):** Pipeline de evaluación continua usando un Golden Dataset y un LLM juez para medir Relevancia, Completitud y Fidelidad (anti-alucinación).

---

## 🏗️ Arquitectura

El sistema sigue una arquitectura modular y extensible, separando claramente las responsabilidades de ingesta, almacenamiento, retrieval y generación.

```text
[ ClinicalTrials.gov API ] 
         ↓ (JSON)
[ Ingestion Pipeline (Pydantic + LLM Extraction) ]
         ↓ (Nodes & Edges)
[ Graph Repository Pattern (Neo4j AuraDB) ]
         ↓ (Cypher Queries)
[ GraphRAG Orchestrator (Query Understanding + Context Formatting) ]
         ↓ (Prompt)
[ LLM Generator (GPT-4o-mini) ] → Respuesta Natural
```

---

## 🛠️ Tech Stack

- **Lenguaje:** Python 3.12+
- **LLM & Embeddings:** OpenAI API (GPT-4o-mini)
- **Base de Datos de Grafos:** Neo4j AuraDB (con driver oficial `neo4j`)
- **Validación de Datos:** Pydantic
- **Gestión de Entorno:** `python-dotenv`, `venv`

---

## 📂 Estructura del Proyecto

```text
GraphVector/
├── config/
│   └── settings.py          # Configuración centralizada
├── data/
│   ├── raw/                 # Datos crudos de la API
│   ├── processed/           # Entidades y relaciones extraídas
│   └── gold_dataset/        # Dataset de evaluación y reportes
├── src/
│   ├── ingestion/           # Parsers, modelos Pydantic y extracción LLM
│   ├── graph/               # Patrón Repositorio e implementación Neo4j
│   ├── retrieval/           # Graph Retriever, Query Understanding y Generator
│   └── evaluation/          # Evaluator (LLM-as-a-Judge)
├── main.py                  # Script de entrada principal
├── requirements.txt         # Dependencias
└── README.md
```

---

## 🚀 Cómo ejecutar

### 1. Instalación
```bash
git clone https://github.com/josemaria500/graphrag-medical-knowledge.git
cd graphrag-medical-knowledge

python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configuración
Crea un archivo `.env` en la raíz del proyecto con tus credenciales:
```env
OPENAI_API_KEY=tu_api_key_de_openai
NEO4J_URI=neo4j+s://tu_instancia.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password_de_neo4j
```

### 3. Ejecución
**Ejecutar el pipeline completo (Ingesta + Pruebas de Retrieval):**
```bash
python main.py
```

**Ejecutar la Evaluación Automatizada (LLM-as-a-Judge):**
```bash
python main.py --evaluate
```

---

## 📊 Evaluación del Sistema

A diferencia de los proyectos tradicionales, este sistema incluye un pipeline de evaluación automatizada para medir la calidad y evitar alucinaciones. Utilizamos un **Golden Dataset** de 4 preguntas críticas y un LLM juez para calificar las respuestas.

### Resultados Finales

| Métrica | Puntuación (1-5) |
|---------|------------------|
| **Relevancia** | 5.00 / 5 |
| **Completitud** | 5.00 / 5 |
| **Fidelidad (Anti-alucinación)** | 5.00 / 5 |
| **Score Global** | **5.00 / 5** |

*Nota: El sistema partió de un score inicial de 2.92/5. Tras analizar los fallos del LLM-as-a-Judge, se iteró sobre el formateo del contexto y el prompt del generador, alcanzando la puntuación perfecta.*

---

## 🤔 Trade-offs y Decisiones de Diseño

Como Ingeniero de IA, cada decisión técnica se tomó evaluando los pros y los contras:

1. **¿Por qué GraphRAG y no RAG Vectorial?**
   El RAG vectorial falla en preguntas multi-salto (ej. *"¿Qué fármacos prueban ensayos que estudian la enfermedad X?"*). El grafo resuelve esto traversando relaciones explícitas (`Trial`-[:STUDIES]->`Disease`), garantizando precisión estructural.

2. **¿Por qué LLM API en lugar de Local?**
   Para la extracción de entidades médicas, la precisión de GPT-4o-mini justifica su coste (~$0.02 por 10 ensayos) frente al tiempo de ingeniería y la alta tasa de alucinación de modelos locales de 8B sin fine-tuning específico.

3. **¿Por qué el Patrón Repositorio?**
   Permite desacoplar la lógica de negocio de la base de datos. Si mañana el cliente exige que los datos sensibles no salgan de su VPC, podemos cambiar de AuraDB a Neo4j Community en Docker cambiando solo las variables de entorno.

---

## 🔮 Mejoras Futuras (Roadmap)

- **Ingesta Multi-fuente:** Extender el pipeline modular para ingerir Guías Clínicas (NCCN/SEOM) y Literatura Biomédica (PubMed).
- **API REST:** Exponer el sistema mediante FastAPI para su integración en aplicaciones clínicas.
- **Frontend Interactivo:** Interfaz web con Streamlit para visualización en tiempo real del grafo y las respuestas.
- **Text-to-Cypher Avanzado:** Implementar un agente que genere queries Cypher dinámicas en lugar de usar handlers predefinidos.

---

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.