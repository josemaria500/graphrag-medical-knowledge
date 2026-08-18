"""
Cliente HTTP centralizado para la API FastAPI.
Detecta automáticamente si corre en Docker o local.
"""

import os
import requests
import json
from typing import Generator

# Detectar entorno: Docker (api:8000) o local (localhost:8000)
if os.getenv("API_URL"):
    # Docker: API_URL viene con /query al final, lo limpiamos
    _raw = os.getenv("API_URL")
    API_BASE = _raw.replace("/query", "")
else:
    API_BASE = "http://localhost:8000/api"


def health_check() -> dict:
    """Verifica que la API esté corriendo."""
    r = requests.get(f"{API_BASE}/health", timeout=5)
    r.raise_for_status()
    return r.json()


# ─── Endpoints de Chat RAG ───

def query_rag(question: str) -> dict:
    """Hace una pregunta al sistema RAG."""
    r = requests.post(
        f"{API_BASE}/query",
        json={"question": question},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def fetch_full_graph(limit: int = 200) -> dict:
    """Obtiene el grafo completo para visualización."""
    r = requests.get(f"{API_BASE}/graph", params={"limit": limit}, timeout=15)
    r.raise_for_status()
    return r.json()


# ─── Endpoints de Importación (v2) ───

def search_trials(
    condition: str,
    max_studies: int = 30,
    status: str | None = None,
    intervention: str | None = None,
) -> dict:
    """Busca ensayos en ClinicalTrials.gov (gratis, sin LLM)."""
    params = {"condition": condition, "max_studies": max_studies}
    if status:
        params["status"] = status
    if intervention:
        params["intervention"] = intervention
    
    r = requests.get(f"{API_BASE}/search", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_study_detail(nct_id: str) -> dict | None:
    """Obtiene detalle de un ensayo desde la API."""
    r = requests.get(f"{API_BASE}/study/{nct_id}", timeout=15)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def import_trials(nct_ids: list[str]) -> Generator[dict, None, None]:
    """
    Importa un batch de ensayos al grafo.
    Devuelve un generador de eventos SSE con el progreso.
    """
    r = requests.post(
        f"{API_BASE}/import",
        json={"nct_ids": nct_ids},
        stream=True,
        timeout=300  # 5 minutos para imports largos
    )
    r.raise_for_status()
    
    for line in r.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data_str = decoded[6:]  # Quitar "data: "
                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError:
                    continue


def get_imported_trials() -> dict:
    """Lista los ensayos ya importados (source=clinicaltrials_api)."""
    r = requests.get(f"{API_BASE}/imported-trials", timeout=10)
    r.raise_for_status()
    return r.json()


def delete_trial(nct_id: str) -> dict:
    """Borra un ensayo específico del grafo."""
    r = requests.delete(f"{API_BASE}/trial/{nct_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def clear_imported() -> dict:
    """Borra todos los ensayos importados."""
    r = requests.post(f"{API_BASE}/clear-imported", timeout=30)
    r.raise_for_status()
    return r.json()


def get_graph_stats() -> dict:
    """Estadísticas de capacidad del grafo."""
    r = requests.get(f"{API_BASE}/graph/stats", timeout=10)
    r.raise_for_status()
    return r.json()