import json
import re
from openai import OpenAI
from config.settings import OPENAI_API_KEY

class PaperEntityExtractor:
    """Extrae entidades médicas de abstracts usando LLM y Regex."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def extract_entities(self, abstract: str) -> dict:
        if not abstract:
            return self._empty_result()

        # 1. Extraer NCT IDs con Regex (es más fiable y barato que el LLM)
        nct_ids = list(set(re.findall(r'NCT\d{8}', abstract)))

        # 2. Prompt optimizado para extraer relaciones complejas
        prompt = f"""
        Eres un experto en oncología y ensayos clínicos. Analiza el siguiente abstract y extrae las entidades en formato JSON estricto.
        Si no encuentras algo, devuelve una lista vacía [].

        Abstract:
        "{abstract}"

        Entidades a extraer:
        1. drugs: Fármacos o intervenciones farmacológicas (nombres genéricos preferiblemente).
        2. diseases: Enfermedades, condiciones o tipos de cáncer estudiados.
        3. biomarkers: Biomarcadores, mutaciones genéticas (ej. BRCA1, HER2, PALB2) o receptores.
        4. outcomes: Resultados clínicos clave o hallazgos principales (ej. "mejora de la supervivencia global", "reducción del riesgo"). Máximo 3 puntos concisos.
        5. adverse_events: Efectos secundarios o toxicidades mencionadas (ej. "náuseas", "fatiga", "toxicidad hematológica").

        Responde ÚNICAMENTE con un objeto JSON válido con esta estructura:
        {{
            "drugs": ["..."],
            "diseases": ["..."],
            "biomarkers": ["..."],
            "outcomes": ["..."],
            "adverse_events": ["..."]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Puedes cambiar a gpt-3.5-turbo si prefieres
                messages=[
                    {"role": "system", "content": "Eres un asistente útil que responde solo con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            entities = json.loads(content)
            
            # Asegurar que todas las claves existan
            for key in ["drugs", "diseases", "biomarkers", "outcomes", "adverse_events"]:
                if key not in entities:
                    entities[key] = []
            
            entities['nct_ids'] = nct_ids
            # Normalizar antes de retornar
            return self._normalize_entities(entities)

        except Exception as e:
            print(f"  [WARN] Error extrayendo entidades con LLM: {e}")
            return {**self._empty_result(), 'nct_ids': nct_ids}

    def _empty_result(self) -> dict:
        return {
            "drugs": [], "diseases": [], "biomarkers": [], 
            "outcomes": [], "adverse_events": [], "nct_ids": []
        }
    
    def _normalize_entities(self, entities: dict) -> dict:
        """Normaliza entidades para evitar duplicados (case-insensitive, sin espacios extras)."""
        normalized = {}
        for key, values in entities.items():
            if isinstance(values, list):
                # Capitalizar primera letra de cada entidad
                normalized[key] = [v.strip().title() if v else v for v in values]
            else:
                normalized[key] = values
        return normalized
    