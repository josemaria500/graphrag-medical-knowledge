from neo4j import GraphDatabase
from .repository import GraphRepository

class Neo4jRepository(GraphRepository):
    """Implementación completa de GraphRepository para Neo4j."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def save_nodes(self, nodes: list[dict]) -> None:
        """Guarda nodos en Neo4j usando MERGE para evitar duplicados."""
        with self.driver.session() as session:
            for node in nodes:
                label = node['label']
                node_id = node['id']
                properties = node.get('properties', {})
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $properties
                """
                params = {'id': node_id, 'properties': properties}
                session.run(query, params)
    
    def save_edges(self, edges: list[dict]) -> None:
        """
        Guarda relaciones en Neo4j.
        Usa MERGE para los nodos (por si no existen) y luego crea la relación.
        """
        with self.driver.session() as session:
            for i, edge in enumerate(edges):
                source = edge['source']
                target = edge['target']
                rel_type = edge['type']
                properties = edge.get('properties', {})
                
                try:
                    # Paso 1: Asegurar que ambos nodos existan
                    session.run("""
                        MERGE (a {id: $source})
                        MERGE (b {id: $target})
                    """, {'source': source, 'target': target})
                    
                    # Paso 2: Crear la relación (con o sin propiedades)
                    if properties:
                        query = f"""
                        MATCH (a {{id: $source}}), (b {{id: $target}})
                        MERGE (a)-[r:{rel_type}]->(b)
                        SET r += $properties
                        """
                        session.run(query, {'source': source, 'target': target, 'properties': properties})
                    else:
                        query = f"""
                        MATCH (a {{id: $source}}), (b {{id: $target}})
                        MERGE (a)-[r:{rel_type}]->(b)
                        """
                        session.run(query, {'source': source, 'target': target})
                    
                    # Log cada 10 relaciones para no saturar la terminal
                    if (i + 1) % 10 == 0:
                        print(f"  ✅ Guardadas {i + 1}/{len(edges)} relaciones...")
                        
                except Exception as e:
                    print(f"  ⚠️ Error guardando relación {source} -[{rel_type}]-> {target}: {e}")
            
            print(f"  ✅ Total de relaciones procesadas: {len(edges)}")
    
    def clear(self) -> None:
        """Limpia todos los datos del grafo."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def get_stats(self) -> dict:
        """Obtiene estadísticas básicas del grafo."""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            return {"node_count": node_count, "rel_count": rel_count}

    def get_trials_by_source(self, source: str) -> list[dict]:
        """Lista ensayos por fuente (demo o clinicaltrials_api)."""
        query = """
        MATCH (t:ClinicalTrial)
        WHERE t.source = $source
        RETURN t.id AS nct_id, t.title AS title, t.status AS status, t.imported_at AS imported_at
        ORDER BY t.imported_at DESC
        """
        with self.driver.session() as session:
            return [record.data() for record in session.run(query, source=source)]

    def delete_trial(self, nct_id: str) -> bool:
        """Borra un ensayo específico. Protege los de source='demo'."""
        with self.driver.session() as session:
            record = session.run(
                "MATCH (t:ClinicalTrial {id: $nct_id}) RETURN t.source AS source", 
                nct_id=nct_id
            ).single()
            if record is None or record["source"] == "demo":
                return False
            session.run("MATCH (t:ClinicalTrial {id: $nct_id}) DETACH DELETE t", nct_id=nct_id)
            return True

    def clear_by_source(self, source: str) -> int:
        """Borra nodos con un source específico. Protege demo."""
        if source == "demo":
            return 0
        with self.driver.session() as session:
            session.run("MATCH ()-[r]->() WHERE r.source = $source DELETE r", source=source)
            result = session.run(
                "MATCH (n) WHERE n.source = $source DETACH DELETE n RETURN count(n) AS deleted", 
                source=source
            )
            return result.single()["deleted"] if result.single() else 0

    def save_paper_with_relations(self, paper: dict, entities: dict) -> None:
        """Guarda un paper y sus relaciones con fármacos, enfermedades, biomarcadores, ensayos, outcomes y eventos adversos."""
        with self.driver.session() as session:
            # Guardar el nodo Paper
            paper_query = """
            MERGE (p:Paper {pmid: $pmid})
            SET p.id = $pmid, p.title = $title, p.abstract = $abstract, 
                p.journal = $journal, p.year = $year, p.url = $url
            """
            paper_params = {
                'pmid': paper['pmid'], 'title': paper['title'], 'abstract': paper['abstract'],
                'journal': paper['journal'], 'year': paper['year'],
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"
            }
            session.run(paper_query, paper_params)

            # Relaciones con ensayos clínicos
            for nct_id in entities.get('nct_ids', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (t:ClinicalTrial {id: $nct_id})
                    MERGE (p)-[:PUBLISHES_RESULTS_OF]->(t)
                """, {'pmid': paper['pmid'], 'nct_id': nct_id})

            # Relaciones con fármacos
            for drug in entities.get('drugs', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (d:Drug {id: $drug})
                    MERGE (p)-[:EVALUATES]->(d)
                """, {'pmid': paper['pmid'], 'drug': drug})

            # Relaciones con enfermedades
            for disease in entities.get('diseases', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (dis:Disease {id: $disease})
                    MERGE (p)-[:STUDIES]->(dis)
                """, {'pmid': paper['pmid'], 'disease': disease})

            # Relaciones con biomarcadores
            for biomarker in entities.get('biomarkers', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (b:Biomarker {id: $biomarker})
                    MERGE (p)-[:MEASURES]->(b)
                """, {'pmid': paper['pmid'], 'biomarker': biomarker})

            # NUEVO: Relaciones con outcomes (resultados clínicos)
            for outcome in entities.get('outcomes', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (o:Outcome {id: $outcome})
                    MERGE (p)-[:REPORTS]->(o)
                """, {'pmid': paper['pmid'], 'outcome': outcome})

            # NUEVO: Relaciones con adverse_events (efectos secundarios)
            for adverse_event in entities.get('adverse_events', []):
                session.run("""
                    MATCH (p:Paper {pmid: $pmid})
                    MERGE (ae:AdverseEvent {id: $adverse_event})
                    MERGE (p)-[:MENTIONS]->(ae)
                """, {'pmid': paper['pmid'], 'adverse_event': adverse_event})