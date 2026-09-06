import os
import json
from openai import OpenAI

class QueryUnderstanding:
    """
    Usa LLM para entender la pregunta y extraer entidades relevantes.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def extract_entities(self, question: str) -> dict:
        """
        Extrae entidades de la pregunta usando LLM.
        Devuelve un dict con: query_type, disease, drug, nct_id, entity_id, entity_type, etc.
        """
        prompt = f"""
Eres un sistema que analiza preguntas médicas y sobre ensayos clínicos.
Extrae las entidades relevantes de la pregunta.

## PREGUNTA:
{question}

## ENTIDADES A EXTRAER:
- query_type: tipo de consulta (uno de: "drugs_for_disease", "trials_for_drug", "trial_details", "drugs_for_trial", "biomarkers_for_drug", "papers_for_drug_disease", "papers_for_trial", "entity_exploration")
  - drugs_for_disease: buscar fármacos para una enfermedad (ej: "qué fármacos para cáncer de mama")
  - trials_for_drug: buscar ensayos que prueban un fármaco (ej: "qué ensayos prueban Olaparib")
  - trial_details: obtener detalles de un ensayo específico por NCT ID (ej: "detalles del NCT02689427")
  - drugs_for_trial: buscar qué fármacos se prueban en un ensayo específico (ej: "qué fármacos usa el NCT02689427")
  - biomarkers_for_drug: buscar biomarcadores que targetea un fármaco (ej: "biomarcadores de Olaparib")
  - papers_for_drug_disease: buscar papers/evidencia científica publicada sobre un fármaco y una enfermedad (ej: "qué papers hablan de Olaparib y cáncer")
  - papers_for_trial: buscar papers que publiquen resultados de un ensayo específico (ej: "papers del NCT02689427")
  - entity_exploration: explorar TODAS las relaciones de una entidad (fármaco, ensayo, enfermedad, paper) para obtener información completa (ej: "qué me puedes decir de Abemaciclib", "qué sabes de Olaparib", "información sobre NCT02689427")

- entity_id: identificador de la entidad cuando query_type es "entity_exploration" (puede ser un fármaco, NCT ID, PMID, enfermedad)
- entity_type: tipo de entidad cuando query_type es "entity_exploration" (uno de: "Drug", "ClinicalTrial", "Paper", "Disease", "Biomarker", null si no se puede determinar)

## FORMATO DE SALIDA:
Devuelve un JSON con esta estructura exacta:
{{
  "query_type": "entity_exploration",
  "disease": null,
  "drug": null,
  "nct_id": null,
  "biomarker": null,
  "entity_id": "Abemaciclib",
  "entity_type": "Drug"
}}

Si una entidad no está presente, usa null.
Solo devuelve el JSON, sin texto adicional ni markdown.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result