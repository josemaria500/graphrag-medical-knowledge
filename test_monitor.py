"""
Script de prueba para el monitor de capacidad de Neo4j.
Uso: python test_monitor.py
"""

from dotenv import load_dotenv
load_dotenv()

from src.graph.neo4j_repository import Neo4jRepository
from src.graph.graph_monitor import GraphMonitor
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def main():
    print("📊 Probando monitor de capacidad de Neo4j...\n")
    
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    monitor = GraphMonitor(repo)
    
    try:
        # 1. Estado actual
        print("=" * 60)
        print("1. ESTADO ACTUAL DEL GRAFO")
        print("=" * 60)
        status = monitor.get_status()
        print(f"  Nodos: {status['node_count']:,} / {status['node_limit']:,} ({status['node_percentage']}%)")
        print(f"  Relaciones: {status['rel_count']:,} / {status['rel_limit']:,} ({status['rel_percentage']}%)")
        print(f"  Uso global: {status['overall_percentage']}%")
        print(f"  Cerca del límite: {status['is_near_limit']}")
        print(f"  Mensaje: {monitor.get_capacity_message()}")
        
        # 2. Estimar impacto de un batch
        print("\n" + "=" * 60)
        print("2. ESTIMAR IMPACTO DE IMPORTAR 10 ENSAYOS")
        print("=" * 60)
        impact = monitor.estimate_batch_impact(10)
        print(f"  Nodos estimados: +{impact['estimated_nodes']}")
        print(f"  Relaciones estimadas: +{impact['estimated_rels']}")
        print(f"  Nuevo uso de nodos: {impact['new_node_percentage']}%")
        print(f"  Superaría límite: {impact['would_exceed_limit']}")
        print(f"  Activaría warning: {impact['would_trigger_warning']}")
        
        # 3. Verificar si se puede importar
        print("\n" + "=" * 60)
        print("3. ¿SE PUEDE IMPORTAR UN BATCH DE 30 ENSAYOS?")
        print("=" * 60)
        can_import, message = monitor.can_import(30)
        print(f"  Puede importar: {can_import}")
        print(f"  Mensaje: {message}")
        
        # 4. Listar ensayos por fuente
        print("\n" + "=" * 60)
        print("4. ENSAYOS POR FUENTE")
        print("=" * 60)
        
        demo_trials = repo.get_trials_by_source("demo")
        print(f"  Demo: {len(demo_trials)} ensayos")
        for t in demo_trials[:3]:
            print(f"    - [{t['nct_id']}] {t['title'][:50]}...")
        
        imported_trials = repo.get_trials_by_source("clinicaltrials_api")
        print(f"  Importados: {len(imported_trials)} ensayos")
        for t in imported_trials[:3]:
            print(f"    - [{t['nct_id']}] {t['title'][:50]}...")
        
        print("\n✅ Pruebas del monitor completadas")
        
    finally:
        repo.close()


if __name__ == "__main__":
    main()