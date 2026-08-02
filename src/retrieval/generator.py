import os
from openai import OpenAI

class ResponseGenerator:
    """
    Genera respuestas naturales usando el contexto del grafo.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    

    def generate(self, question: str, context: dict) -> str:
        """
        Genera una respuesta usando el contexto extraído del grafo.
        """
        formatted_context = self._format_context(context)
        
        prompt = f"""
    Eres un asistente experto en ensayos clínicos de cáncer de mama.

    ## INFORMACIÓN DISPONIBLE DEL GRAFO DE CONOCIMIENTO:
    {formatted_context}

    ## PREGUNTA DEL USUARIO:
    {question}

    ## INSTRUCCIONES:
    1. La información del grafo es TU ÚNICA fuente de verdad
    2. Si el grafo contiene datos relevantes (fármacos, ensayos, detalles), ÚSALOS para responder
    3. Solo responde "No tengo información suficiente" si la sección relevante del grafo está vacía
    4. Sé específico y menciona IDs, nombres, estados, etc.

    ## RESPUESTA:
    """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    

    def _format_context(self, context: dict) -> str:
        """Formatea el contexto del grafo en texto legible y explícito."""
        text = ""
        
        # Añadir la entidad consultada al inicio
        if 'query_entity' in context:
            text += f"## CONSULTA REALIZADA: {context['query_entity']}\n\n"
        
        if 'drugs' in context:
            drugs = context['drugs']
            if drugs:
                text += "## FÁRMACOS ENCONTRADOS:\n"
                for item in drugs:
                    if 'trial' in item:
                        text += f"- {item['drug']} (ensayo {item['trial']})\n"
                    else:
                        text += f"- {item['drug']}\n"
            else:
                text += "## FÁRMACOS ENCONTRADOS:\nNo se encontraron fármacos.\n"
        
        if 'trials' in context:
            trials = context['trials']
            if trials:
                text += "## ENSAYOS CLÍNICOS ENCONTRADOS:\n"
                text += f"Estos ensayos prueban el fármaco consultado:\n"
                for item in trials:
                    text += f"- {item['trial_id']}: {item['title']} (Estado: {item['status']})\n"
            else:
                text += "## ENSAYOS CLÍNICOS ENCONTRADOS:\nNo se encontraron ensayos clínicos.\n"
        
        if 'trial' in context:
            trial = context['trial']
            if trial:
                text += "## DETALLES DEL ENSAYO:\n"
                text += f"- ID: {trial['id']}\n"
                text += f"- Título: {trial['title']}\n"
                text += f"- Estado: {trial['status']}\n"
                text += f"- Tratamientos: {', '.join(trial['treatments'])}\n"
                text += f"- Enfermedades: {', '.join(trial['diseases'])}\n"
        
        if 'drugs_in_trial' in context:
            drugs = context['drugs_in_trial']
            if drugs:
                text += "## FÁRMACOS EN ESTE ENSAYO:\n"
                for item in drugs:
                    text += f"- {item['drug']}\n"
            else:
                text += "## FÁRMACOS EN ESTE ENSAYO:\nNo se encontraron fármacos.\n"
        
        if 'biomarkers' in context:
            biomarkers = context['biomarkers']
            if biomarkers:
                text += f"## BIOMARCADORES: {', '.join(biomarkers)}\n"
        
        if 'message' in context:
            text += context['message']
        
        return text