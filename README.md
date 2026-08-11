# 🩺 GraphRAG Medical Knowledge

**Sistema GraphRAG sobre un grafo de conocimiento de ensayos clínicos de cáncer de mama: pregunta en lenguaje natural y explora el grafo en vivo.**

🔗 **Demo en producción:** [https://josemariagalvez.es](https://josemariagalvez.es)
- Portfolio → `/`
- Aplicación (Streamlit + grafo interactivo) → `/graphrag/`
- API (FastAPI + Swagger) → `/api/docs`

---

## 📌 ¿Qué es este proyecto?

Pipeline **GraphRAG completo** sobre datos reales de ensayos clínicos (ClinicalTrials.gov), desplegado de punta a punta:

1. **Ingesta** – Parseo de ensayos y extracción de entidades (fármacos, enfermedades, biomarcadores) con LLM.
2. **Grafo de conocimiento** – Almacenamiento en **Neo4j** con esquema tipado.
3. **Retrieval** – Traducción de preguntas en lenguaje natural a consultas **Cypher** (query understanding con LLM).
4. **Generación** – Respuestas fundamentadas con **GPT-4o-mini** (RAG sobre el contexto del grafo).
5. **Visualización** – Grafo interactivo que reacciona a cada consulta (pyvis).
6. **Serving** – API FastAPI + frontend Streamlit + home estática de portfolio, todo tras **Nginx** con **HTTPS** (Let's Encrypt) en un VPS, 100 % **Dockerizado**.

## 🏗️ Arquitectura

```text
                     Internet (443/80)
                            │
                 ┌──────────▼──────────┐
                 │  Nginx (reverse     │
                 │  proxy + home)      │
                 └──┬────────┬────────┬┘
                    │        │        │
              /     │   /graphrag/    │   /api/
        (home estática)      │        │
                    │ ┌──────▼──────┐ │ ┌─────────────┐
                    │ │  Streamlit  │─┼▶│   FastAPI   │
                    │ │  (frontend) │   │  (backend)  │
                    │ └─────────────┘   └──┬───────┬──┘
                    │                      │       │
                    │              ┌───────▼──┐ ──▼───────────┐
                    │              │ Neo4j    │ │ OpenAI       │
                    │              │ AuraDB   │ │ GPT-4o-mini  │
                    │              └──────────┘ └──────────────┘
                    └─ Todo orquestado con Docker Compose
```

## 🧬 Esquema del grafo

```cypher
(:ClinicalTrial)-[:TESTS]->(:Drug | :Intervention)
(:ClinicalTrial)-[:STUDIES]->(:Disease)
(:Drug)-[:TARGETS]->(:Biomarker)
```

## ❓ Consultas soportadas

| Tipo | Ejemplo |
|---|---|
| Fármacos por enfermedad | *¿Qué fármacos se están probando para cáncer de mama?* |
| Ensayos por fármaco | *¿Qué ensayos clínicos prueban Abemaciclib?* |
| Detalles de un ensayo | *Dame detalles del ensayo NCT02689427* |
| Fármacos de un ensayo | *¿Qué fármacos se prueban en NCT02689427?* |
| Biomarcadores por fármaco | *¿Qué biomarcadores targetea Olaparib?* |

## 🔌 API

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/health` | GET | Estado del servicio |
| `/api/graph?limit=200` | GET | Muestra del grafo completo (nodos + enlaces) |
| `/api/query` | POST | `{question}` → `{answer, graph, query_type}` |

```bash
curl -X POST https://josemariagalvez.es/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué ensayos clínicos prueban Abemaciclib?"}'
```

## 📊 Evaluación

El sistema incluye un **golden dataset** con preguntas de referencia y respuestas esperadas, y un **evaluador LLM-as-judge** que puntúa cada respuesta generada en tres dimensiones (escala 1–5):

- **Relevancia** – ¿responde directamente a lo preguntado, sin ruido?
- **Completitud** – ¿incluye toda la información requerida?
- **Fidelidad** – ¿es fiel a los datos del grafo, sin inventar nada?

### Resultados

| Métrica | Puntuación media |
|---|---|
| 🎯 Relevancia | **5.0 / 5** |
| 📋 Completitud | **5.0 / 5** |
| 🔒 Fidelidad | **5.0 / 5** |

> Evaluado sobre **4 preguntas** del golden dataset. Todas las respuestas obtuvieron **5/5** en las tres dimensiones.

### Detalle por pregunta

| Pregunta | Relevancia | Completitud | Fidelidad |
|---|:---:|:---:|:---:|
| ¿Qué fármacos se están probando para cáncer de mama? | 5 | 5 | 5 |
| Dame detalles del ensayo NCT02689427 | 5 | 5 | 5 |
| ¿Qué ensayos clínicos prueban Fulvestrant? | 5 | 5 | 5 |
| ¿Qué fármacos se prueban en el ensayo NCT04565054? | 5 | 5 | 5 |

Reproducir la evaluación:

```bash
python main.py --evaluate
```

## 🚀 Ejecutar en local

```bash
git clone https://github.com/josemaria500/graphrag-medical-knowledge.git
cd graphrag-medical-knowledge

cat > .env <<EOF
NEO4J_URI=neo4j+s://TU_INSTANCIA.databases.neo4j.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=TU_PASSWORD
OPENAI_API_KEY=TU_KEY
EOF

python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python main.py

docker compose up --build -d
```

## 🐳 Producción

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- **Nginx** sirve la home estática, enruta `/graphrag/` (Streamlit, con WebSockets) y `/api/` (FastAPI).
- **HTTPS** con Let's Encrypt (Certbot + webroot) y renovación automática.

## 🗂️ Estructura del proyecto

```text
├── backend/            # API FastAPI (Dockerfile, api.py)
├── frontend/           # Streamlit + visualización pyvis
├── nginx/              # Reverse proxy + home del portfolio
│   └── home/index.html
├── config/settings.py  # Carga de configuración (.env)
├── src/
│   ├── ingestion/      # Parseo ClinicalTrials.gov + extracción LLM
│   ├── graph/          # Repositorio Neo4j
│   ├── retrieval/      # GraphRAG: retriever Cypher, generator, query understanding
│   └── evaluation/     # Evaluador con golden dataset
├── data/
│   ├── raw/            # Muestra de ensayos clínicos
│   └── gold_dataset/   # Dataset de evaluación
├── docker-compose.yml       # Entorno base (HTTP)
├── docker-compose.prod.yml  # Override producción (HTTPS)
└── main.py                  # Pipeline de ingesta + pruebas + evaluación
```

## 🛠️ Stack

`Python` · `FastAPI` · `Streamlit` · `Neo4j (Cypher)` · `OpenAI GPT-4o-mini` · `pyvis` · `Docker` · `Nginx` · `Let's Encrypt` · `Git`

## 📬 Contacto

**José María Gálvez** — Data & AI Engineer
- 🌐 [josemariagalvez.es](https://josemariagalvez.es)
- 💼 [LinkedIn](https://www.linkedin.com/in/josemariagalvez/)
- 🐙 [GitHub](https://github.com/josemaria500)
