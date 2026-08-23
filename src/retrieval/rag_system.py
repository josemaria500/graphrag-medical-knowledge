from .graph_retriever import GraphRetriever
from .generator import ResponseGenerator
from .query_understanding import QueryUnderstanding


class GraphRAGSystem:
    """
    Sistema principal de GraphRAG que orquesta retrieval y generación.
    """

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.graph_retriever = GraphRetriever(neo4j_uri, neo4j_user, neo4j_password)
        self.generator = ResponseGenerator()
        self.query_understanding = QueryUnderstanding()

    def close(self):
        self.graph_retriever.close()

    def get_full_graph(self, limit: int = 200) -> dict:
        """
        Obtiene el grafo completo (nodos y relaciones) hasta un límite.
        Usado por el endpoint /api/graph para visualización con Cytoscape.js.
        """
        driver = self.graph_retriever.driver
        with driver.session() as session:
            # Obtener nodos
            nodes_query = """
            MATCH (n)
            WHERE n.id IS NOT NULL
            RETURN n.id AS id, labels(n) AS labels
            LIMIT $limit
            """
            nodes_result = session.run(nodes_query, limit=limit)
            nodes = []
            for record in nodes_result:
                labels = record["labels"]
                node_type = labels[0] if labels else "Unknown"
                nodes.append({
                    "id": record["id"],
                    "label": node_type,
                    "type": node_type
                })

            # Obtener relaciones
            edges_query = """
            MATCH (a)-[r]->(b)
            WHERE a.id IS NOT NULL AND b.id IS NOT NULL
            RETURN a.id AS source, b.id AS target, type(r) AS rel
            LIMIT $limit
            """
            edges_result = session.run(edges_query, limit=limit * 3)
            links = []
            for record in edges_result:
                links.append({
                    "source": record["source"],
                    "target": record["target"],
                    "rel": record["rel"]
                })

        return {"nodes": nodes, "links": links}

    def ask(self, question: str) -> str:
        """
        Responde una pregunta usando GraphRAG.
        """
        # Paso 1: Entender la pregunta con LLM
        print(f"  [DEBUG] Entendiendo pregunta...")
        entities = self.query_understanding.extract_entities(question)
        print(f"  [DEBUG] Entidades extraídas: {entities}")

        # Paso 2: Ejecutar la query apropiada según el tipo
        context = {}
        query_type = entities.get('query_type')

        if query_type == 'drugs_for_disease' and entities.get('disease'):
            context['drugs'] = self.graph_retriever.find_drugs_for_disease(entities['disease'])
            context['query_entity'] = f"Enfermedad: {entities['disease']}"
        elif query_type == 'trials_for_drug' and entities.get('drug'):
            context['trials'] = self.graph_retriever.find_trials_for_drug(entities['drug'])
            context['query_entity'] = f"Fármaco buscado: {entities['drug']}"
        elif query_type == 'trial_details' and entities.get('nct_id'):
            context['trial'] = self.graph_retriever.get_trial_details(entities['nct_id'])
            context['query_entity'] = f"Ensayo: {entities['nct_id']}"
        elif query_type == 'drugs_for_trial' and entities.get('nct_id'):
            context['drugs_in_trial'] = self.graph_retriever.find_drugs_for_trial(entities['nct_id'])
            context['query_entity'] = f"Ensayo: {entities['nct_id']}"
        elif query_type == 'biomarkers_for_drug' and entities.get('drug'):
            context['biomarkers'] = self.graph_retriever.find_biomarkers_for_drug(entities['drug'])
            context['query_entity'] = f"Fármaco: {entities['drug']}"
        else:
            context['message'] = "No se pudieron extraer entidades específicas de la pregunta."

        print(f"  [DEBUG] Contexto del grafo: {context}")

        # Paso 3: Generar respuesta
        return self.generator.generate(question, context)

    def ask_with_graph(self, question: str) -> dict:
        """
        Responde una pregunta y devuelve el subgrafo asociado.
        Usado por el endpoint /api/query para mostrar grafo en la UI.
        """
        # Obtener respuesta textual
        answer = self.ask(question)

        # Obtener subgrafo relacionado con la pregunta
        entities = self.query_understanding.extract_entities(question)
        graph_data = {"nodes": [], "links": []}

        try:
            driver = self.graph_retriever.driver
            with driver.session() as session:
                # Buscar nodos relacionados con las entidades extraídas
                nct_id = entities.get('nct_id')
                drug = entities.get('drug')
                disease = entities.get('disease')

                if nct_id:
                    query = """
                    MATCH (t:ClinicalTrial {id: $nct_id})
                    OPTIONAL MATCH (t)-[r]-(related)
                    RETURN t, r, related
                    LIMIT 50
                    """
                    result = session.run(query, nct_id=nct_id)
                elif drug:
                    query = """
                    MATCH (d:Drug) WHERE d.id CONTAINS $drug
                    OPTIONAL MATCH (d)-[r]-(related)
                    RETURN d, r, related
                    LIMIT 50
                    """
                    result = session.run(query, drug=drug)
                elif disease:
                    query = """
                    MATCH (dis:Disease) WHERE dis.id CONTAINS $disease
                    OPTIONAL MATCH (dis)-[r]-(related)
                    RETURN dis, r, related
                    LIMIT 50
                    """
                    result = session.run(query, disease=disease)
                else:
                    result = None

                if result:
                    seen_nodes = set()
                    nodes = []
                    links = []
                    for record in result:
                        for key in ['t', 'd', 'dis', 'related']:
                            node = record.get(key)
                            if node and hasattr(node, 'id'):
                                node_id = node.get('id')
                                if node_id and node_id not in seen_nodes:
                                    seen_nodes.add(node_id)
                                    labels = list(node.labels)
                                    node_type = labels[0] if labels else "Unknown"
                                    nodes.append({
                                        "id": node_id,
                                        "label": node_type,
                                        "type": node_type
                                    })
                        rel = record.get('r')
                        if rel:
                            try:
                                source = rel.start_node.get('id')
                                target = rel.end_node.get('id')
                                if source and target:
                                    links.append({
                                        "source": source,
                                        "target": target,
                                        "rel": rel.type
                                    })
                            except:
                                pass
                    graph_data = {"nodes": nodes, "links": links}
        except Exception as e:
            print(f"  [WARN] Error obteniendo subgrafo: {e}")

        return {
            "answer": answer,
            "graph": graph_data,
            "query_type": entities.get('query_type')
        }