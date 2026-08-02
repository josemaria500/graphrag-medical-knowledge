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
        Devuelve un dict con: query_type, disease, drug, nct_id, etc.
        """
        prompt = f"""
Eres un sistema que analiza preguntas sobre ensayos clínicos de cáncer de mama.
Extrae las entidades relevantes de la pregunta.

## PREGUNTA:
{question}

## ENTIDADES A EXTRAER:
- query_type: tipo de consulta (uno de: "drugs_for_disease", "trials_for_drug", "trial_details", "drugs_for_trial", "biomarkers_for_drug", "general")
  - drugs_for_disease: buscar fármacos para una enfermedad
  - trials_for_drug: buscar ensayos que prueban un fármaco
  - trial_details: obtener detalles de un ensayo específico por NCT ID
  - drugs_for_trial: buscar qué fármacos se prueban en un ensayo específico
  - biomarkers_for_drug: buscar biomarcadores que targetea un fármaco

## FORMATO DE SALIDA:
Devuelve un JSON con esta estructura:
{{
  "query_type": "drugs_for_disease",
  "disease": "Breast Cancer",
  "drug": null,
  "nct_id": null,
  "biomarker": null
}}

Si una entidad no está presente, usa null.
Solo devuelve el JSON, sin texto adicional.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result