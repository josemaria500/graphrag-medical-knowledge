from typing import Any
from neo4j import GraphDatabase

class GraphRetriever:
    """Traduce preguntas en consultas Cypher al grafo."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def find_drugs_for_disease(self, disease_name: str) -> list[dict]:
        """Encuentra todos los fármacos que se están probando para una enfermedad."""
        # Mapeo básico de términos en español a inglés
        disease_mapping = {
            "cáncer de mama": "breast",
            "cancer de mama": "breast",
            "mama": "breast",
            "cáncer": "cancer",
            "cancer": "cancer"
        }
        
        # Buscar término en inglés si es posible
        search_term = disease_name.lower()
        for spanish, english in disease_mapping.items():
            if spanish in search_term:
                search_term = english
                break
        
        query = """
        MATCH (t:ClinicalTrial)-[:TESTS]->(d:Drug),
              (t)-[:STUDIES]->(dis:Disease)
        WHERE toLower(dis.id) CONTAINS toLower($disease_name)
           OR toLower(dis.id) CONTAINS $search_term
        RETURN DISTINCT d.id AS drug, t.id AS trial
        """
        with self.driver.session() as session:
            result = session.run(query, disease_name=disease_name, search_term=search_term)
            return [record.data() for record in result]
    
    def find_trials_for_drug(self, drug_name: str) -> list[dict]:
        query = """
        MATCH (t:ClinicalTrial)-[:TESTS]->(d:Drug)
        WHERE toLower(d.id) CONTAINS toLower($drug_name)
        RETURN t.id AS trial_id, t.title AS title, t.status AS status
        """
        with self.driver.session() as session:
            result = session.run(query, drug_name=drug_name)
            return [record.data() for record in result]
    
    def find_biomarkers_for_drug(self, drug_name: str) -> list[str]:
        query = """
        MATCH (d:Drug)-[:TARGETS]->(b:Biomarker)
        WHERE toLower(d.id) CONTAINS toLower($drug_name)
        RETURN b.id AS biomarker
        """
        with self.driver.session() as session:
            result = session.run(query, drug_name=drug_name)
            return [record['biomarker'] for record in result]
    
    def get_trial_details(self, nct_id: str) -> dict:
        """
        Obtiene todos los detalles de un ensayo clínico, incluyendo papers relacionados
        directa (PUBLISHES_RESULTS_OF) o indirectamente (a través de fármacos/enfermedades).
        """
        with self.driver.session() as session:
            # Consulta 1: Datos básicos del ensayo + papers directos
            query1 = """
            MATCH (t:ClinicalTrial {id: $nct_id})
            OPTIONAL MATCH (t)-[:TESTS]->(d:Drug|Intervention)
            OPTIONAL MATCH (t)-[:STUDIES]->(dis:Disease)
            OPTIONAL MATCH (p:Paper)-[:PUBLISHES_RESULTS_OF]->(t)
            RETURN t.id AS id, t.title AS title, t.status AS status,
                   collect(DISTINCT d.id) AS treatments,
                   collect(DISTINCT dis.id) AS diseases,
                   collect(DISTINCT {
                       pmid: p.pmid, 
                       title: p.title, 
                       year: p.year,
                       relation_type: 'direct'
                   }) AS direct_papers
            """
            result1 = session.run(query1, nct_id=nct_id)
            record1 = result1.single()
            
            if not record1:
                return None
            
            data = record1.data()
            # Filtrar papers directos nulos
            direct_papers = [p for p in data['direct_papers'] if p['pmid'] is not None]
            
            # Consulta 2: Papers indirectos (a través de fármacos o enfermedades)
            query2 = """
            MATCH (t:ClinicalTrial {id: $nct_id})-[:TESTS|:STUDIES]-(entity)
            MATCH (p:Paper)-[:EVALUATES|:STUDIES]-(entity)
            WHERE NOT (p)-[:PUBLISHES_RESULTS_OF]->(t)
            RETURN DISTINCT p.pmid AS pmid, p.title AS title, p.year AS year
            """
            result2 = session.run(query2, nct_id=nct_id)
            indirect_papers = [
                {
                    'pmid': record['pmid'],
                    'title': record['title'],
                    'year': record['year'],
                    'relation_type': 'indirect'
                }
                for record in result2
                if record['pmid'] is not None
            ]
            
            # Combinar ambos tipos de papers
            data['papers'] = direct_papers + indirect_papers
            del data['direct_papers']
            
            return data
    
    def find_drugs_for_trial(self, nct_id: str) -> list[dict]:
        query = """
        MATCH (t:ClinicalTrial {id: $nct_id})-[:TESTS]->(d:Drug)
        RETURN d.id AS drug
        """
        with self.driver.session() as session:
            result = session.run(query, nct_id=nct_id)
            return [record.data() for record in result]

    def find_papers_for_drug_and_disease(self, drug_name: str, disease_name: str) -> list[dict]:
        query = """
        MATCH (p:Paper)-[:EVALUATES]->(d:Drug)
        MATCH (p)-[:STUDIES]->(dis:Disease)
        WHERE toLower(d.id) CONTAINS toLower($drug_name) 
          AND toLower(dis.id) CONTAINS toLower($disease_name)
        RETURN p.pmid AS pmid, p.title AS title, p.year AS year, p.url AS url, p.abstract AS abstract
        LIMIT 5
        """
        with self.driver.session() as session:
            result = session.run(query, drug_name=drug_name, disease_name=disease_name)
            return [record.data() for record in result]

    def find_papers_for_trial(self, nct_id: str) -> list[dict]:
        query = """
        MATCH (p:Paper)-[:PUBLISHES_RESULTS_OF]->(t:ClinicalTrial {id: $nct_id})
        RETURN p.pmid AS pmid, p.title AS title, p.year AS year, p.url AS url, p.abstract AS abstract
        """
        with self.driver.session() as session:
            result = session.run(query, nct_id=nct_id)
            return [record.data() for record in result]
        

    def get_complete_entity_info(self, entity_id: str, entity_type: str = None) -> dict:
        """
        Explora TODAS las relaciones de una entidad (fármaco, ensayo, enfermedad, paper, etc.)
        y devuelve un diccionario completo con toda la información conectada.
        """
        with self.driver.session() as session:
            # Consulta que explora todas las relaciones en 2 saltos
            query = """
            MATCH (entity)
            WHERE entity.id = $entity_id
            OPTIONAL MATCH (entity)-[r1]-(neighbor1)
            OPTIONAL MATCH (neighbor1)-[r2]-(neighbor2)
            RETURN entity.id AS entity_id, labels(entity)[0] AS entity_type,
                   neighbor1.id AS n1_id, labels(neighbor1)[0] AS n1_type, type(r1) AS r1_type,
                   neighbor2.id AS n2_id, labels(neighbor2)[0] AS n2_type, type(r2) AS r2_type
            LIMIT 100
            """
            result = session.run(query, entity_id=entity_id)
            
            info = {
                'entity_id': entity_id,
                'entity_type': entity_type or 'Unknown',
                'direct_relations': [],
                'indirect_relations': []
            }
            
            seen_direct = set()
            seen_indirect = set()
            
            for record in result:
                # Relaciones directas
                if record['n1_id'] and record['n1_id'] not in seen_direct:
                    seen_direct.add(record['n1_id'])
                    info['direct_relations'].append({
                        'id': record['n1_id'],
                        'type': record['n1_type'],
                        'relation': record['r1_type']
                    })
                
                # Relaciones indirectas (2 saltos)
                if record['n2_id'] and record['n2_id'] not in seen_indirect and record['n2_id'] != entity_id:
                    seen_indirect.add(record['n2_id'])
                    info['indirect_relations'].append({
                        'id': record['n2_id'],
                        'type': record['n2_type'],
                        'path': f"{entity_id} -[{record['r1_type']}]-> {record['n1_id']} -[{record['r2_type']}]-> {record['n2_id']}"
                    })
            
            return info