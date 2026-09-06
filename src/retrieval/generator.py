import os
from openai import OpenAI

class ResponseGenerator:
    """
    Genera respuestas naturales usando el contexto del grafo.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    

    def generate(self, question: str, context: dict) -> str:
        papers = context.get('papers', [])
        papers_text = ""
        if papers:
            papers_text = "\n\nPAPERS CIENTÍFICOS DISPONIBLES:\n"
            for p in papers:
                abstract_preview = (p.get('abstract') or '')[:300]
                papers_text += f"- [{p['pmid']}] {p['title']} ({p['year']}): {abstract_preview}...\n  URL: {p['url']}\n"

        prompt = f"""Eres un asistente médico experto. Responde basándote en el contexto del grafo proporcionado.

REGLAS DE CITACIÓN:
- Si hay papers en el contexto, DEBES citarlos usando formato markdown: [Título del paper](URL)
- Incluye al final una sección "📚 Referencias:" con todos los papers citados.
- Si no hay papers, responde normalmente sin inventar citas.
- Sé conciso y basado en evidencia.

CONTEXTO DEL GRAFO:
{context}
{papers_text}

PREGUNTA DEL USUARIO:
{question}
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
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