from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from src.retrieval.rag_system import GraphRAGSystem
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

rag_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_system
    print("🚀 Inicializando GraphRAGSystem...")
    rag_system = GraphRAGSystem(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    yield
    print("🛑 Cerrando GraphRAGSystem...")
    rag_system.close()


app = FastAPI(
    title="GraphRAG Medical Knowledge API",
    description="API para consultar ensayos clínicos de cáncer de mama usando GraphRAG con Neo4j",
    version="1.1.0",
    lifespan=lifespan,
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modelos ---

class QueryRequest(BaseModel):
    question: str


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphLink(BaseModel):
    source: str
    target: str
    rel: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class QueryResponse(BaseModel):
    answer: str
    graph: GraphData
    query_type: str | None = None


# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "GraphRAG Medical Knowledge API is running"}


@app.get("/graph", response_model=GraphData)
async def get_full_graph(limit: int = 200):
    """Muestra del grafo completo para visualización."""
    if rag_system is None:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    try:
        return rag_system.get_full_graph(limit=min(limit, 500))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Responde una pregunta y devuelve el subgrafo asociado."""
    if rag_system is None:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    try:
        result = rag_system.ask_with_graph(request.question)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la pregunta: {str(e)}")