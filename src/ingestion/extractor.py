import json
import os
from openai import OpenAI
from .models import ClinicalTrial
from .text_formatter import format_trial_for_llm
from .prompts import EXTRACTION_PROMPT_TEMPLATE

# Inicializa el cliente de OpenAI (necesitarás OPENAI_API_KEY en variables de entorno)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_entities_and_relations(trial: ClinicalTrial) -> dict:
    """
    Envía un ensayo clínico al LLM y extrae entidades y relaciones.
    Devuelve un dict con 'nodes' y 'edges'.
    """
    # 1. Convertir el trial a texto
    trial_text = format_trial_for_llm(trial)
    
    # 2. Formatear el prompt
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(trial_text=trial_text)
    
    # 3. Llamar al LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Barato y suficientemente bueno para extracción
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,  # Baja temperatura para consistencia
        response_format={"type": "json_object"}  # Fuerza output JSON
    )
    
    # 4. Parsear la respuesta
    result_text = response.choices[0].message.content
    
    try:
        result = json.loads(result_text)
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON del LLM para {trial.nct_id}: {e}")
        print(f"Respuesta cruda: {result_text}")
        return {"nodes": [], "edges": []}


def extract_all_trials(trials: list[ClinicalTrial]) -> dict:
    """
    Itera sobre todos los ensayos y extrae entidades/relaciones.
    Devuelve un dict consolidado con todos los nodos y edges.
    """
    all_nodes = []
    all_edges = []
    
    print(f"🔄 Extrayendo entidades de {len(trials)} ensayos clínicos...")
    
    for i, trial in enumerate(trials, 1):
        print(f"  [{i}/{len(trials)}] Procesando {trial.nct_id}...")
        
        result = extract_entities_and_relations(trial)
        
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))
    
    print(f"\n✅ Extracción completada:")
    print(f"   - Nodos extraídos: {len(all_nodes)}")
    print(f"   - Relaciones extraídas: {len(all_edges)}")
    
    return {
        "nodes": all_nodes,
        "edges": all_edges
    }