# Cargar variables de entorno ANTES de cualquier import
from dotenv import load_dotenv
load_dotenv()

# Ahora sí, importar los módulos
from src.ingestion.parsers import parse_clinical_trials
from src.ingestion.extractor import extract_all_trials
from src.graph.neo4j_repository import Neo4jRepository
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys
import json

def main():
    print("Iniciando pipeline de GraphRAG...")
    
    # Paso 1: Parsear
    trials = parse_clinical_trials('data/raw/clinical_trials_sample.json')
    print(f"\n✅ Parseados {len(trials)} ensayos clínicos")
    
    # Paso 2: Extraer entidades con LLM
    print("\n" + "="*60)
    print("EXTRACCIÓN DE ENTIDADES CON LLM")
    print("="*60)
    extracted_data = extract_all_trials(trials)
    
    # Paso 3: Guardar en Neo4j
    print("\n" + "="*60)
    print("INSERCIÓN EN NEO4J")
    print("="*60)
    
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        print("Limpiando grafo existente...")
        repo.clear()
        
        print(f"Guardando {len(extracted_data['nodes'])} nodos...")
        repo.save_nodes(extracted_data['nodes'])
        
        print(f"Guardando {len(extracted_data['edges'])} relaciones...")
        repo.save_edges(extracted_data['edges'])
        
        print("\n✅ Datos insertados en Neo4j correctamente")
    finally:
        repo.close()


def test_rag_system():
    """Prueba el sistema de GraphRAG con preguntas de ejemplo."""
    from src.retrieval.rag_system import GraphRAGSystem
    
    print("\n" + "="*60)
    print("SISTEMA GraphRAG - PRUEBAS")
    print("="*60)
    
    rag = GraphRAGSystem(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        questions = [
            "¿Qué fármacos se están probando para cáncer de mama?",
            "¿Qué ensayos clínicos prueban Olaparib?",
            "Dame detalles del ensayo NCT02689427"
        ]
        
        for question in questions:
            print(f"\n❓ Pregunta: {question}")
            answer = rag.ask(question)
            print(f" Respuesta: {answer}")
            print("-" * 60)
    
    finally:
        rag.close()


def run_evaluation():
    """Ejecuta la evaluación del sistema GraphRAG con el Golden Dataset."""
    from src.retrieval.rag_system import GraphRAGSystem
    from src.evaluation.evaluator import GraphRAGEvaluator
    
    print("\n" + "="*60)
    print("INICIANDO EVALUACIÓN DEL SISTEMA")
    print("="*60)
    
    # Inicializar sistema y evaluador
    rag = GraphRAGSystem(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    evaluator = GraphRAGEvaluator()
    
    try:
        # Ejecutar evaluación
        report = evaluator.evaluate_dataset(rag, 'data/gold_dataset/golden_dataset.json')
        
        # Guardar reporte
        with open('data/gold_dataset/evaluation_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("\n💾 Reporte guardado en data/gold_dataset/evaluation_report.json")
        
    finally:
        rag.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--evaluate":
        run_evaluation()
    else:
        main()
        test_rag_system()