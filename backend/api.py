from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from src.ingestion.pubmed_client import PubMedClient
from src.ingestion.paper_extractor import PaperEntityExtractor
import json
import time
import os
from pathlib import Path

load_dotenv()

from src.retrieval.rag_system import GraphRAGSystem
from src.graph.neo4j_repository import Neo4jRepository
from src.graph.graph_monitor import GraphMonitor
from src.ingestion.import_service import ImportService
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MAX_BATCH_SIZE

# Ruta base del proyecto (para servir archivos estáticos)
BASE_DIR = Path(__file__).resolve().parent.parent

rag_system = None

def _cleanup_orphan_nodes(session) -> int:
    """Elimina nodos sin relaciones y devuelve la cantidad borrada."""
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        WITH n LIMIT 1000
        DETACH DELETE n
        RETURN count(n) AS deleted
    """)
    return result.single()["deleted"]


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
    version="2.1.0",
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

# ============================================================
# FRONTEND: Servir archivos estáticos y plantilla HTML
# ============================================================
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")


@app.get("/graphrag/", include_in_schema=False)
async def frontend_home(request: Request):
    """Sirve la página principal del frontend (FastAPI + Cytoscape.js)."""
    return templates.TemplateResponse(request, "index.html")


# ─── Modelos existentes ───

class QueryRequest(BaseModel):
    question: str


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    title: str | None = None    
    year: str | None = None     


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

class IngestPapersRequest(BaseModel):
    query: str = Field(..., description="Consulta de búsqueda para PubMed (ej: 'Olaparib breast cancer')")
    max_results: int = Field(default=5, le=10, description="Número máximo de papers a ingerir (máx 10)")

class IngestedPaper(BaseModel):
    pmid: str
    title: str
    nct_ids_found: list[str]
    url: str

class IngestPapersResponse(BaseModel):
    status: str
    message: str
    papers: list[IngestedPaper]


# ─── Filtro de cáncer de mama (enfoque de la app) ───

BREAST_KEYWORDS = ["breast", "mama", "mammary", "mamaria"]


def _is_breast_related(trial_dict: dict) -> bool:
    """Devuelve True si el ensayo está relacionado con cáncer de mama."""
    text = " ".join([
        " ".join(trial_dict.get("conditions") or []),
        trial_dict.get("title") or "",
    ]).lower()
    return any(k in text for k in BREAST_KEYWORDS)


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


# ─── Endpoints de importación ───

@app.post("/import")
def import_studies(request: ImportRequest):
    """
    Importa un batch de ensayos clínicos al grafo.
    Devuelve un stream SSE con el progreso en tiempo real.
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
            "X-Accel-Buffering": "no",
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
        # 🧹 Limpieza automática de huérfanos tras borrar ensayos
        with repo.driver.session() as session:
            deleted_orphans = _cleanup_orphan_nodes(session)
        return {"status": "ok", "deleted_nodes": deleted, "orphans_cleaned": deleted_orphans}
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
            # 🧹 Limpieza automática de huérfanos tras borrar un ensayo
            with repo.driver.session() as session:
                deleted_orphans = _cleanup_orphan_nodes(session)
            return DeleteResponse(
                status="ok", 
                deleted=nct_id, 
                message=f"Se limpiaron {deleted_orphans} nodos huérfanos"
            )
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
    """Lista los ensayos importados y los demo (marcados con source)."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        imported = repo.get_trials_by_source("clinicaltrials_api")
        for t in imported:
            t["source"] = "clinicaltrials_api"
        demo = repo.get_trials_by_source("demo")
        for t in demo:
            t["source"] = "demo"
        trials = imported + demo
        return ImportedTrialsResponse(trials=trials, count=len(trials))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.get("/graph/stats")
async def get_graph_stats():
    """Devuelve estadísticas básicas del grafo."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        stats = repo.get_stats()
        NODE_LIMIT = 20000
        REL_LIMIT = 40000

        node_count = stats.get("node_count", 0)
        rel_count = stats.get("rel_count", 0)
        
        return {
            "node_count": node_count,
            "rel_count": rel_count,
            "node_limit": NODE_LIMIT,
            "rel_limit": REL_LIMIT,
            "node_percentage": round((node_count / NODE_LIMIT) * 100, 2) if NODE_LIMIT > 0 else 0,
            "rel_percentage": round((rel_count / REL_LIMIT) * 100, 2) if REL_LIMIT > 0 else 0,
            "overall_percentage": round(((node_count + rel_count) / (NODE_LIMIT + REL_LIMIT)) * 100, 2),
            "is_near_limit": node_count > NODE_LIMIT * 0.8 or rel_count > REL_LIMIT * 0.8,
            "is_at_limit": node_count >= NODE_LIMIT or rel_count >= REL_LIMIT,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


# ─── Búsqueda en ClinicalTrials.gov con filtro de cáncer de mama ───

@app.get("/search")
async def search_studies(
    condition: str,
    max_studies: int = 30,
    status: str | None = None,
    intervention: str | None = None,
):
    """
    Busca ensayos en la API de ClinicalTrials.gov (GRATIS, sin LLM).
    Aplica SIEMPRE el filtro de cáncer de mama (enfoque de la app).
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

        # 🎯 Filtro de cáncer de mama: solo se muestran ensayos relevantes
        trials_dicts = [trial.model_dump() for trial in results]
        filtered = [t for t in trials_dicts if _is_breast_related(t)]

        return {
            "results": filtered,
            "count": len(filtered),
            "condition": condition,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/papers", response_model=IngestPapersResponse)
async def ingest_papers_on_demand(request: IngestPapersRequest):
    """
    Busca papers en PubMed bajo demanda, extrae entidades y los guarda en Neo4j.
    Permite al usuario ampliar la base de conocimientos dinámicamente.
    """
    try:
        pubmed = PubMedClient()
        extractor = PaperEntityExtractor()
        repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        # 1. Buscar papers
        papers = pubmed.search_papers(request.query, max_results=request.max_results)
        if not papers:
            raise HTTPException(status_code=404, detail="No se encontraron papers para esta consulta en PubMed.")
        
        ingested = []
        
        # 2. Procesar y guardar cada paper
        for p in papers:
            entities = extractor.extract_entities(p["abstract"])
            repo.save_paper_with_relations(p, entities)
            
            ingested.append(IngestedPaper(
                pmid=p["pmid"],
                title=p["title"],
                nct_ids_found=entities.get("nct_ids", []),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"
            ))
            
        repo.close()
        
        return IngestPapersResponse(
            status="success",
            message=f"Se ingestaron {len(ingested)} papers correctamente en el grafo.",
            papers=ingested
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la ingesta: {str(e)}")


@app.post("/ingest/paper/{pmid}")
async def ingest_single_paper(pmid: str):
    """Importa un paper específico en el grafo usando su PMID."""
    try:
        pubmed = PubMedClient()
        extractor = PaperEntityExtractor()
        repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        # Buscar específicamente por PMID en PubMed
        papers = pubmed.search_papers(f"{pmid}[pmid]", max_results=1)
        if not papers:
            raise HTTPException(status_code=404, detail="Paper no encontrado en PubMed.")
        
        p = papers[0]
        entities = extractor.extract_entities(p.get("abstract", ""))
        repo.save_paper_with_relations(p, entities)
        repo.close()
        
        return {"status": "success", "message": f"Paper {pmid} importado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-papers")
async def search_papers(query: str, max_results: int = 10):
    """Busca papers en PubMed sin importarlos aún (para previsualizar en la UI)."""
    try:
        client = PubMedClient()
        papers = client.search_papers(query, max_results=min(max_results, 50))
        return {"results": papers, "count": len(papers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers")
async def list_papers():
    """Lista todos los papers importados en el grafo."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        with repo.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)
                RETURN p.pmid AS pmid, p.title AS title, p.year AS year, p.journal AS journal, p.url AS url
                ORDER BY p.year DESC
            """)
            papers = [record.data() for record in result]
        return {"papers": papers, "count": len(papers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.delete("/paper/{pmid}")
async def delete_paper(pmid: str):
    """Borra un paper específico del grafo."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        with repo.driver.session() as session:
            session.run("MATCH (p:Paper {pmid: $pmid}) DETACH DELETE p", pmid=pmid)
            # 🧹 Limpieza automática de huérfanos tras borrar un paper
            deleted_orphans = _cleanup_orphan_nodes(session)
        return {"status": "ok", "deleted": pmid, "orphans_cleaned": deleted_orphans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.delete("/papers")
async def delete_all_papers():
    """Borra todos los papers del grafo."""
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        with repo.driver.session() as session:
            result = session.run("MATCH (p:Paper) DETACH DELETE p RETURN count(p) AS deleted")
            deleted = result.single()["deleted"]
            # 🧹 Limpieza automática de huérfanos tras borrar todos los papers
            deleted_orphans = _cleanup_orphan_nodes(session)
        return {"status": "ok", "deleted": deleted, "orphans_cleaned": deleted_orphans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


@app.delete("/cleanup/orphans")
async def cleanup_orphan_nodes():
    """
    Elimina todos los nodos huérfanos (sin relaciones) del grafo.
    Endpoint manual por si se necesita una limpieza explícita.
    """
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        with repo.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                WITH n LIMIT 1000
                DETACH DELETE n
                RETURN count(n) AS deleted
            """)
            deleted = result.single()["deleted"]
        return {"status": "ok", "deleted": deleted, "message": f"Se eliminaron {deleted} nodos huérfanos"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()


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