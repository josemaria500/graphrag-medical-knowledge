# test_paper_ingestion.py
from src.ingestion.pubmed_client import PubMedClient
from src.ingestion.paper_extractor import PaperEntityExtractor
from src.graph.neo4j_repository import Neo4jRepository
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

if __name__ == "__main__":
    pubmed = PubMedClient()
    extractor = PaperEntityExtractor()
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    print("1. Buscando papers en PubMed...")
    papers = pubmed.search_papers("Olaparib breast cancer", max_results=2)
    
    for p in papers:
        print(f"\nProcesando: {p['title']}")
        print("2. Extrayendo entidades con LLM...")
        entities = extractor.extract_entities(p["abstract"])
        print(f"   Entidades: {entities}")
        
        print("3. Guardando en Neo4j...")
        repo.save_paper_with_relations(p, entities)
        print("   ✅ Guardado.")

    repo.close()
    print("\n🎉 Ingesta dinámica completada. Revisa tu instancia de Neo4j.")