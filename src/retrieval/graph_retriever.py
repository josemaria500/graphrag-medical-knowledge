from typing import Any
from neo4j import GraphDatabase

class GraphRetriever:
    """
    Traduce preguntas en consultas Cypher al grafo.
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def find_drugs_for_disease(self, disease_name: str) -> list[dict]:
        """
        Encuentra todos los fármacos que se están probando para una enfermedad.
        Query: (Trial)-[:TESTS]->(Drug) y (Trial)-[:STUDIES]->(Disease)
        """
        query = """
        MATCH (t:ClinicalTrial)-[:TESTS]->(d:Drug),
              (t)-[:STUDIES]->(dis:Disease)
        WHERE dis.id CONTAINS $disease_name
        RETURN DISTINCT d.id AS drug, t.id AS trial
        """
        
        with self.driver.session() as session:
            result = session.run(query, disease_name=disease_name)
            return [record.data() for record in result]
    
    def find_trials_for_drug(self, drug_name: str) -> list[dict]:
        """
        Encuentra todos los ensayos que prueban un fármaco específico.
        """
        query = """
        MATCH (t:ClinicalTrial)-[:TESTS]->(d:Drug)
        WHERE d.id CONTAINS $drug_name
        RETURN t.id AS trial_id, t.title AS title, t.status AS status
        """
        
        with self.driver.session() as session:
            result = session.run(query, drug_name=drug_name)
            return [record.data() for record in result]
    
    def find_biomarkers_for_drug(self, drug_name: str) -> list[str]:
        """
        Encuentra qué biomarcadores targetea un fármaco.
        """
        query = """
        MATCH (d:Drug {id: $drug_name})-[:TARGETS]->(b:Biomarker)
        RETURN b.id AS biomarker
        """
        
        with self.driver.session() as session:
            result = session.run(query, drug_name=drug_name)
            return [record['biomarker'] for record in result]
    
    def get_trial_details(self, nct_id: str) -> dict:
        """
        Obtiene todos los detalles de un ensayo clínico.
        """
        query = """
        MATCH (t:ClinicalTrial {id: $nct_id})
        OPTIONAL MATCH (t)-[:TESTS]->(d:Drug|Intervention)
        OPTIONAL MATCH (t)-[:STUDIES]->(dis:Disease)
        RETURN t.id AS id, t.title AS title, t.status AS status,
               collect(DISTINCT d.id) AS treatments,
               collect(DISTINCT dis.id) AS diseases
        """
        
        with self.driver.session() as session:
            result = session.run(query, nct_id=nct_id)
            record = result.single()
            return record.data() if record else None

    def find_drugs_for_trial(self, nct_id: str) -> list[dict]:
        """
        Encuentra todos los fármacos que se prueban en un ensayo específico.
        """
        query = """
        MATCH (t:ClinicalTrial {id: $nct_id})-[:TESTS]->(d:Drug)
        RETURN d.id AS drug
        """
        
        with self.driver.session() as session:
            result = session.run(query, nct_id=nct_id)
            return [record.data() for record in result]

    # =========================================================
    # Métodos para visualización del grafo
    # =========================================================

    def get_full_graph(self, limit: int = 200) -> dict:
        """Devuelve una muestra del grafo completo (nodos + enlaces)."""
        query = """
        MATCH (a)-[r]->(b)
        RETURN a.id AS source, labels(a)[0] AS source_type,
               type(r) AS rel,
               b.id AS target, labels(b)[0] AS target_type
        LIMIT $limit
        """
        with self.driver.session() as session:
            rows = [record.data() for record in session.run(query, limit=limit)]
        return self._triples_to_graph(rows)

    def get_subgraph_for_query(self, query_type: str, entities: dict) -> dict:
        """Devuelve el subgrafo asociado a una pregunta ya entendida."""
        if query_type == "drugs_for_disease" and entities.get("disease"):
            return self._subgraph_disease(entities["disease"])
        if query_type in ("trials_for_drug", "biomarkers_for_drug") and entities.get("drug"):
            return self._subgraph_drug(entities["drug"])
        if query_type in ("trial_details", "drugs_for_trial") and entities.get("nct_id"):
            return self._subgraph_trial(entities["nct_id"])
        return {"nodes": [], "links": []}

    def _subgraph_disease(self, disease: str) -> dict:
        query = """
        MATCH (t:ClinicalTrial)-[:STUDIES]->(dis:Disease)
        WHERE dis.id CONTAINS $name
        WITH t, dis LIMIT 50
        OPTIONAL MATCH (t)-[:TESTS]->(x)
        RETURN dis.id AS disease, t.id AS trial,
               x.id AS target_id, labels(x)[0] AS target_type
        """
        triples = []
        with self.driver.session() as session:
            for row in [r.data() for r in session.run(query, name=disease)]:
                triples.append({"source": row["trial"], "source_type": "ClinicalTrial",
                                "rel": "STUDIES", "target": row["disease"], "target_type": "Disease"})
                if row["target_id"]:
                    triples.append({"source": row["trial"], "source_type": "ClinicalTrial",
                                    "rel": "TESTS", "target": row["target_id"], "target_type": row["target_type"]})
        return self._triples_to_graph(triples)

    def _subgraph_drug(self, drug: str) -> dict:
        triples = []
        with self.driver.session() as session:
            rows = [r.data() for r in session.run("""
                MATCH (t:ClinicalTrial)-[:TESTS]->(d:Drug)
                WHERE d.id CONTAINS $name
                WITH t, d LIMIT 50
                OPTIONAL MATCH (t)-[:STUDIES]->(dis:Disease)
                RETURN d.id AS drug, t.id AS trial, dis.id AS disease
            """, name=drug)]
            for row in rows:
                triples.append({"source": row["trial"], "source_type": "ClinicalTrial",
                                "rel": "TESTS", "target": row["drug"], "target_type": "Drug"})
                if row["disease"]:
                    triples.append({"source": row["trial"], "source_type": "ClinicalTrial",
                                    "rel": "STUDIES", "target": row["disease"], "target_type": "Disease"})
            biomarkers = [r.data() for r in session.run("""
                MATCH (d:Drug)-[:TARGETS]->(b:Biomarker)
                WHERE d.id CONTAINS $name
                RETURN d.id AS drug, b.id AS biomarker
            """, name=drug)]
            for row in biomarkers:
                triples.append({"source": row["drug"], "source_type": "Drug",
                                "rel": "TARGETS", "target": row["biomarker"], "target_type": "Biomarker"})
        return self._triples_to_graph(triples)

    def _subgraph_trial(self, nct_id: str) -> dict:
        query = """
        MATCH (t:ClinicalTrial {id: $nct_id})
        OPTIONAL MATCH (t)-[r:TESTS|STUDIES]->(x)
        RETURN t.id AS trial, type(r) AS rel,
               x.id AS target_id, labels(x)[0] AS target_type
        """
        # Añadimos el nodo central aunque no tenga relaciones
        triples = [{"source": nct_id, "source_type": "ClinicalTrial",
                    "rel": None, "target": None, "target_type": None}]
        with self.driver.session() as session:
            for row in [r.data() for r in session.run(query, nct_id=nct_id)]:
                if row["target_id"]:
                    triples.append({"source": row["trial"], "source_type": "ClinicalTrial",
                                    "rel": row["rel"], "target": row["target_id"], "target_type": row["target_type"]})
        return self._triples_to_graph(triples)

    @staticmethod
    def _triples_to_graph(rows: list[dict]) -> dict:
        """Convierte filas source/target en {nodes, links} deduplicados."""
        nodes: dict[str, dict] = {}

        def add_node(nid, ntype):
            if nid is not None and nid not in nodes:
                nodes[nid] = {"id": nid, "label": nid, "type": ntype or "Unknown"}

        links = []
        for row in rows:
            add_node(row.get("source"), row.get("source_type"))
            add_node(row.get("target"), row.get("target_type"))
            if row.get("source") and row.get("target") and row.get("rel"):
                links.append({"source": row["source"], "target": row["target"], "rel": row["rel"]})
        return {"nodes": list(nodes.values()), "links": links}