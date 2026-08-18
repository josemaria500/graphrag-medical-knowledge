"""
Verifica que el etiquetado 'source' funciona correctamente.
Uso: python test_source_tagging.py
"""

from dotenv import load_dotenv
load_dotenv()

from src.graph.neo4j_repository import Neo4jRepository
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def main():
    print("🏷️ Verificando etiquetado 'source' en Neo4j...\n")
    
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        with repo.driver.session() as session:
            # 1. Nodos por source
            print("1. NODOS POR SOURCE")
            result = session.run("""
                MATCH (n)
                RETURN n.source AS source, count(n) AS count
                ORDER BY count DESC
            """)
            for r in result:
                print(f"  {r['source'] or 'SIN_SOURCE'}: {r['count']}")
            
            # 2. Relaciones por source
            print("\n2. RELACIONES POR SOURCE")
            result = session.run("""
                MATCH ()-[r]->()
                RETURN r.source AS source, count(r) AS count
                ORDER BY count DESC
            """)
            for r in result:
                print(f"  {r['source'] or 'SIN_SOURCE'}: {r['count']}")
            
            # 3. Muestra de ClinicalTrial nodes
            print("\n3. MUESTRA DE ENSAYOS (ClinicalTrial)")
            result = session.run("""
                MATCH (t:ClinicalTrial)
                RETURN t.id, t.source, t.imported_at
                LIMIT 5
            """)
            for r in result:
                print(f"  [{r['t.id']}] source={r['t.source']} imported_at={r['t.imported_at']}")
            
            print("\n✅ Verificación completada")
    
    finally:
        repo.close()


if __name__ == "__main__":
    main()