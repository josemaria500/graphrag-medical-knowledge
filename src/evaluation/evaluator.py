import json
import os
from typing import Dict, List
from openai import OpenAI

class GraphRAGEvaluator:
    """
    Evalúa la calidad de las respuestas del sistema GraphRAG usando LLM-as-a-Judge.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def evaluate_single(self, question: str, expected_answer: str, generated_answer: str) -> Dict[str, int]:
        """
        Evalúa una respuesta individual en 3 dimensiones: relevancia, completitud, fidelidad.
        Devuelve puntuaciones de 1 a 5.
        """
        prompt = f"""
Eres un evaluador experto de sistemas de IA. Tu tarea es calificar la calidad de una respuesta generada por un sistema GraphRAG.

## PREGUNTA ORIGINAL:
{question}

## RESPUESTA ESPERADA (referencia):
{expected_answer}

## RESPUESTA GENERADA (por el sistema):
{generated_answer}

## CRITERIOS DE EVALUACIÓN:

1. **Relevancia** (1-5): ¿La respuesta aborda directamente la pregunta?
   - 1: Completamente irrelevante
   - 3: Parcialmente relevante pero con información innecesaria
   - 5: Altamente relevante y enfocada

2. **Completitud** (1-5): ¿La respuesta contiene toda la información importante?
   - 1: Falta información crítica
   - 3: Contiene información parcial
   - 5: Respuesta completa y detallada

3. **Fidelidad** (1-5): ¿La respuesta es fiel a los datos del grafo (sin alucinaciones)?
   - 1: Contiene información inventada o incorrecta
   - 3: Mayormente correcta pero con errores menores
   - 5: Completamente fiel a los datos

## FORMATO DE SALIDA:
Devuelve un JSON con esta estructura exacta:
{{
  "relevancia": <1-5>,
  "completitud": <1-5>,
  "fidelidad": <1-5>,
  "justificacion": "<explicación breve de las puntuaciones>"
}}

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
    
    def evaluate_dataset(self, rag_system, dataset_path: str) -> Dict:
        """
        Evalúa todo el dataset y genera un reporte completo.
        """
        # Cargar dataset
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        print(f"\n{'='*60}")
        print(f"EVALUACIÓN DE {len(dataset)} PREGUNTAS")
        print(f"{'='*60}\n")
        
        results = []
        total_scores = {"relevancia": 0, "completitud": 0, "fidelidad": 0}
        
        for item in dataset:
            question = item['question']
            expected = item['expected_answer']
            
            print(f"❓ Pregunta: {question}")
            
            # Generar respuesta con el sistema GraphRAG
            generated = rag_system.ask(question)
            
            print(f"🤖 Respuesta generada: {generated[:100]}...")
            
            # Evaluar con LLM-as-a-Judge
            scores = self.evaluate_single(question, expected, generated)
            
            print(f"📊 Puntuaciones: Relevancia={scores['relevancia']}, Completitud={scores['completitud']}, Fidelidad={scores['fidelidad']}")
            print(f"💬 Justificación: {scores['justificacion']}")
            print("-" * 60)
            
            # Acumular resultados
            results.append({
                "question": question,
                "expected": expected,
                "generated": generated,
                "scores": scores
            })
            
            for key in total_scores:
                total_scores[key] += scores[key]
        
        # Calcular promedios
        avg_scores = {key: total_scores[key] / len(dataset) for key in total_scores}
        
        print(f"\n{'='*60}")
        print("RESUMEN DE EVALUACIÓN")
        print(f"{'='*60}")
        print(f"Total de preguntas evaluadas: {len(dataset)}")
        print(f"Relevancia promedio: {avg_scores['relevancia']:.2f}/5")
        print(f"Completitud promedio: {avg_scores['completitud']:.2f}/5")
        print(f"Fidelidad promedio: {avg_scores['fidelidad']:.2f}/5")
        print(f"Score global promedio: {sum(avg_scores.values())/3:.2f}/5")
        print(f"{'='*60}\n")
        
        return {
            "results": results,
            "average_scores": avg_scores,
            "total_questions": len(dataset)
        }