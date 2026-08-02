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