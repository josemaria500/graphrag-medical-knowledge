import json
import os
from datetime import datetime
from openai import OpenAI
from .models import ClinicalTrial
from .text_formatter import format_trial_for_llm
from .prompts import EXTRACTION_PROMPT_TEMPLATE

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _inject_source_metadata(result: dict, source: str, imported_at: datetime) -> dict:
    """
    Inyecta el campo 'source' e 'imported_at' en cada nodo y edge
    devuelto por el LLM.
    """
    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    
    # Añadir source a cada nodo
    for node in nodes:
        if "properties" not in node:
            node["properties"] = {}
        node["properties"]["source"] = source
        node["properties"]["imported_at"] = imported_at.isoformat()
        
        # Campo especial para ClinicalTrial nodes (para poder borrarlos)
        if node.get("label") == "ClinicalTrial":
            node["properties"]["source"] = source
    
    # Añadir source a cada edge
    for edge in edges:
        if "properties" not in edge:
            edge["properties"] = {}
        edge["properties"]["source"] = source
    
    return {"nodes": nodes, "edges": edges}


def extract_entities_and_relations(trial: ClinicalTrial) -> dict:
    """
    Envía un ensayo clínico al LLM y extrae entidades y relaciones.
    Añade el campo 'source' a cada nodo y edge.
    """
    trial_text = format_trial_for_llm(trial)
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(trial_text=trial_text)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content
    
    try:
        result = json.loads(result_text)
        
        # ← INYECTAR METADATA DE ORIGEN
        result = _inject_source_metadata(
            result,
            source=trial.source,
            imported_at=trial.imported_at or datetime.utcnow()
        )
        
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON del LLM para {trial.nct_id}: {e}")
        print(f"Respuesta cruda: {result_text}")
        return {"nodes": [], "edges": []}


def extract_all_trials(trials: list[ClinicalTrial]) -> dict:
    """Itera sobre todos los ensayos y extrae entidades/relaciones."""
    all_nodes = []
    all_edges = []
    
    print(f"🔄 Extrayendo entidades de {len(trials)} ensayos clínicos...")
    
    for i, trial in enumerate(trials, 1):
        print(f"  [{i}/{len(trials)}] Procesando {trial.nct_id} (source={trial.source})...")
        
        result = extract_entities_and_relations(trial)
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))
    
    print(f"\n✅ Extracción completada:")
    print(f"   - Nodos extraídos: {len(all_nodes)}")
    print(f"   - Relaciones extraídas: {len(all_edges)}")
    
    return {"nodes": all_nodes, "edges": all_edges}