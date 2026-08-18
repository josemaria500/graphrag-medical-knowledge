from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import json
import time

load_dotenv()

from src.retrieval.rag_system import GraphRAGSystem
from src.graph.neo4j_repository import Neo4jRepository
from src.graph.graph_monitor import GraphMonitor
from src.ingestion.import_service import ImportService
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MAX_BATCH_SIZE

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
    version="2.0.0",
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


# ─── Modelos existentes ───

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


# ─── Modelos nuevos para importación ───

class ImportRequest(BaseModel):
    nct_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_SIZE,
        description="Lista de NCT IDs a importar (máx 30)"
    )


class DeleteResponse(BaseModel):
    status: str
    deleted: str | None = None
    message: str | None = None


class ImportedTrialsResponse(BaseModel):
    trials: list[dict]
    count: int


class GraphStatsResponse(BaseModel):
    node_count: int
    rel_count: int
    node_limit: int
    rel_limit: int
    node_percentage: float
    rel_percentage: float
    overall_percentage: float
    is_near_limit: bool
    is_at_limit: bool


# ─── Endpoints existentes ───

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


# ─── Endpoints nuevos: Importación (Fase 4) ───

@app.post("/import")
def import_studies(request: ImportRequest):
    """
    Importa un batch de ensayos clínicos al grafo.
    Devuelve un stream SSE con el progreso en tiempo real.
    
    Nota: Endpoint síncrono para que FastAPI lo ejecute en thread pool,
    evitando bloquear el event loop durante la importación (1-2 min).
    """
    def event_stream():
        repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        service = ImportService(repo)
        try:
            for progress in service.run_import(request.nct_ids):
                event_data = {
                    "event": progress.event.value,
                    "current": progress.current,
                    "total": progress.total,
                    "message": progress.message,
                    "success": progress.success,
                    "data": progress.data,
                }
                yield f"data: {json.dumps(event_data)}\n\n"
        except Exception as e:
            error_data = {
                "event": "error",
                "message": f"Error inesperado: {str(e)}",
                "success": False,
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            repo.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # ← CRÍTICO: deshabilita buffering de Nginx
        }
    )


@app.post("/clear-imported")
async def clear_imported_studies():
    """
    Borra todos los ensayos importados (source='clinicaltrials_api').
    Los datos demo (source='demo') están protegidos.
    """
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        deleted = repo.clear_by_source("clinicaltrials_api")
        return {"status": "ok", "deleted_nodes": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.delete("/trial/{nct_id}")
async def delete_trial(nct_id: str):
    """
    Borra un ensayo específico del grafo.
    Solo permite borrar ensayos importados (protege los demo).
    """
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        success = repo.delete_trial(nct_id)
        if success:
            return DeleteResponse(status="ok", deleted=nct_id)
        else:
            return DeleteResponse(
                status="error",
                message=f"No se pudo borrar {nct_id} (no existe o es un ensayo demo protegido)"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.get("/imported-trials", response_model=ImportedTrialsResponse)
async def list_imported_trials():
    """Lista todos los ensayos importados (source='clinicaltrials_api')."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        trials = repo.get_trials_by_source("clinicaltrials_api")
        return ImportedTrialsResponse(trials=trials, count=len(trials))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.get("/graph/stats", response_model=GraphStatsResponse)
async def get_graph_stats():
    """
    Devuelve estadísticas de capacidad del grafo.
    Útil para el monitor de límite de Neo4j Aura Free.
    """
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        monitor = GraphMonitor(repo)
        status = monitor.get_status()
        return GraphStatsResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


# ─── Endpoint de búsqueda en ClinicalTrials.gov (para el panel izquierdo) ───

@app.get("/search")
async def search_studies(
    condition: str,
    max_studies: int = 30,
    status: str | None = None,
    intervention: str | None = None,
):
    """
    Busca ensayos en la API de ClinicalTrials.gov (GRATIS, sin LLM).
    Se usa para poblar el panel izquierdo de la UI.
    """
    from src.ingestion.search_service import SearchService

    try:
        service = SearchService()
        filters = {}
        if status:
            filters["status"] = status
        if intervention:
            filters["intervention"] = intervention

        results = service.search(
            condition=condition,
            max_studies=min(max_studies, 100),
            filters=filters if filters else None,
        )

        # Convertir a dicts serializables (ClinicalTrial → dict)
        return {
            "results": [trial.model_dump() for trial in results],
            "count": len(results),
            "condition": condition,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/study/{nct_id}")
async def get_study_detail(nct_id: str):
    """Obtiene el detalle completo de un ensayo desde la API."""
    from src.ingestion.search_service import SearchService

    try:
        service = SearchService()
        trial = service.get_study_detail(nct_id)
        if trial is None:
            raise HTTPException(status_code=404, detail=f"Ensayo {nct_id} no encontrado")
        return trial.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))