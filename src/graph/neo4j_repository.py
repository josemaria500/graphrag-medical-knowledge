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
        """Guarda relaciones en Neo4j con MERGE."""
        with self.driver.session() as session:
            for edge in edges:
                source = edge['source']
                target = edge['target']
                rel_type = edge['type']
                properties = edge.get('properties', {})
                
                # Si no hay propiedades, usar dict vacío
                if not properties:
                    properties = {}
                
                # Construir SET para actualizar propiedades de la relación
                set_clauses = []
                params = {'source': source, 'target': target}
                for k, v in properties.items():
                    param_name = f"prop_{k}"
                    set_clauses.append(f"r.{k} = ${param_name}")
                    params[param_name] = v
                
                set_clause = ", ".join(set_clauses) if set_clauses else ""
                
                query = f"""
                MATCH (a {{id: $source}}), (b {{id: $target}})
                MERGE (a)-[r:{rel_type}]->(b)
                {f"SET {set_clause}" if set_clause else ""}
                """
                
                session.run(query, params)
    
    def clear(self) -> None:
        """Limpia todos los datos del grafo."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


    def get_stats(self) -> dict:
        """
        Obtiene estadísticas del grafo: nº de nodos y relaciones.
        
        Returns:
            dict con 'node_count' y 'rel_count'
        """
        with self.driver.session() as session:
            # Contar nodos
            node_result = session.run("MATCH (n) RETURN count(n) AS count")
            node_count = node_result.single()["count"]
            
            # Contar relaciones
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            rel_count = rel_result.single()["count"]
            
            return {
                "node_count": node_count,
                "rel_count": rel_count,
            }

    def get_trials_by_source(self, source: str) -> list[dict]:
        """
        Lista todos los ensayos clínicos con un source específico.
        
        Args:
            source: "demo" o "clinicaltrials_api"
        
        Returns:
            Lista de ensayos con sus propiedades básicas
        """
        query = """
        MATCH (t:ClinicalTrial {source: $source})
        RETURN t.id AS nct_id, t.title AS title, t.status AS status,
            t.imported_at AS imported_at
        ORDER BY t.imported_at DESC
        """
        with self.driver.session() as session:
            result = session.run(query, source=source)
            return [record.data() for record in result]

    def delete_trial(self, nct_id: str) -> bool:
        """
        Borra un ensayo clínico específico del grafo.
        Solo borra si NO es de fuente 'demo' (protección).
        
        Args:
            nct_id: Identificador del ensayo
        
        Returns:
            True si se borró, False si no se encontró o está protegido
        """
        with self.driver.session() as session:
            # Verificar que no sea demo
            check_query = """
            MATCH (t:ClinicalTrial {id: $nct_id})
            RETURN t.source AS source
            """
            result = session.run(check_query, nct_id=nct_id)
            record = result.single()
            
            if record is None:
                return False
            
            if record["source"] == "demo":
                return False  # Protegido
            
            # Borrar el ensayo y sus relaciones
            delete_query = """
            MATCH (t:ClinicalTrial {id: $nct_id})
            DETACH DELETE t
            """
            session.run(delete_query, nct_id=nct_id)
            return True

    def clear_by_source(self, source: str) -> int:
        """
        Borra todos los nodos y relaciones con un source específico.
        NO borra nodos de fuente 'demo' si source es diferente.
        
        Args:
            source: "demo" o "clinicaltrials_api"
        
        Returns:
            Número de nodos borrados
        """
        if source == "demo":
            return 0  # Protección: nunca borrar demo
        
        with self.driver.session() as session:
            # Primero borrar relaciones
            session.run(
                "MATCH ()-[r]->() WHERE r.source = $source DELETE r",
                source=source
            )
            # Luego borrar nodos
            result = session.run(
                "MATCH (n {source: $source}) DETACH DELETE n RETURN count(n) AS deleted",
                source=source
            )
            record = result.single()
            return record["deleted"] if record else 0

    def get_stats(self) -> dict:
        """Obtiene estadísticas del grafo: nº de nodos y relaciones."""
        with self.driver.session() as session:
            node_result = session.run("MATCH (n) RETURN count(n) AS count")
            node_count = node_result.single()["count"]
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            rel_count = rel_result.single()["count"]
            return {"node_count": node_count, "rel_count": rel_count}

    def get_trials_by_source(self, source: str) -> list[dict]:
        """Lista todos los ensayos con un source específico."""
        query = """
        MATCH (t:ClinicalTrial)
        WHERE t.source = $source
        RETURN t.id AS nct_id, t.title AS title, t.status AS status,
            t.imported_at AS imported_at
        ORDER BY t.imported_at DESC
        """
        with self.driver.session() as session:
            result = session.run(query, source=source)
            return [record.data() for record in result]

    def delete_trial(self, nct_id: str) -> bool:
        """Borra un ensayo específico. Protege los de source='demo'."""
        with self.driver.session() as session:
            check = session.run(
                "MATCH (t:ClinicalTrial {id: $nct_id}) RETURN t.source AS source",
                nct_id=nct_id
            )
            record = check.single()
            if record is None or record["source"] == "demo":
                return False
            session.run(
                "MATCH (t:ClinicalTrial {id: $nct_id}) DETACH DELETE t",
                nct_id=nct_id
            )
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
            record = result.single()
            return record["deleted"] if record else 0