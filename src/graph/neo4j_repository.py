from neo4j import GraphDatabase
from .repository import GraphRepository

class Neo4jRepository(GraphRepository):
    """Implementación de GraphRepository para Neo4j."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def save_nodes(self, nodes: list[dict]) -> None:
        """
        Guarda nodos en Neo4j usando MERGE para evitar duplicados.
        """
        with self.driver.session() as session:
            for node in nodes:
                label = node['label']
                node_id = node['id']
                properties = node.get('properties', {})
                
                # Query corregida: usar += para añadir propiedades
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $properties
                """
                
                params = {
                    'id': node_id,
                    'properties': properties
                }
                session.run(query, params)
    
    def save_edges(self, edges: list[dict]) -> None:
        """
        Guarda relaciones en Neo4j.
        """
        with self.driver.session() as session:
            for edge in edges:
                source = edge['source']
                target = edge['target']
                rel_type = edge['type']
                properties = edge.get('properties', {})
                
                # Construir query Cypher
                props_str = ', '.join([f'{k}: ${k}' for k in properties.keys()])
                if props_str:
                    props_str = ' {' + props_str + '}'
                
                query = f"""
                MATCH (a {{id: $source}}), (b {{id: $target}})
                MERGE (a)-[r:{rel_type}{props_str}]->(b)
                """
                
                params = {'source': source, 'target': target, **properties}
                session.run(query, params)
    
    def clear(self) -> None:
        """Limpia todos los datos del grafo."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")