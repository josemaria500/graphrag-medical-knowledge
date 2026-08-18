"""
Prueba la importación batch sin Streamlit.
Uso: python test_import.py
"""

from dotenv import load_dotenv
load_dotenv()

from src.ingestion.import_service import ImportService
from src.graph.neo4j_repository import Neo4jRepository
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def main():
    print("🚀 Probando importación batch...\n")

    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    service = ImportService(repo)

    # NCT IDs reales para probar (cáncer de mama)
    test_ids = [
        "NCT05976516",
        "NCT05127655",
        "NCT04861220",  # Este ya está en demo, debería saltarse
    ]

    try:
        print(f"Importando {len(test_ids)} ensayos...\n")
        print("=" * 70)

        for progress in service.run_import(test_ids):
            # Formatear barra de progreso
            bar = ""
            if progress.total > 0:
                pct = progress.current / progress.total
                filled = int(pct * 30)
                bar = f"[{'█' * filled}{'░' * (30 - filled)}] {progress.current}/{progress.total}"

            icon = "✅" if progress.success else "❌"
            print(f"  {icon} [{progress.event.value:>10}] {bar} {progress.message}")

        print("=" * 70)
        print("\n📊 Verificando en Neo4j...")
        
        imported = repo.get_trials_by_source("clinicaltrials_api")
        print(f"  Ensayos importados en el grafo: {len(imported)}")
        for t in imported:
            print(f"    - [{t['nct_id']}] {t['title'][:60]}...")

    finally:
        repo.close()

    print("\n✅ Prueba completada")


if __name__ == "__main__":
    main()