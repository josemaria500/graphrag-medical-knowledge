from .graph_retriever import GraphRetriever
from .generator import ResponseGenerator
from .query_understanding import QueryUnderstanding

class GraphRAGSystem:
    """Sistema principal de GraphRAG que orquesta retrieval y generación."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.graph_retriever = GraphRetriever(neo4j_uri, neo4j_user, neo4j_password)
        self.generator = ResponseGenerator()
        self.query_understanding = QueryUnderstanding()

    def close(self):
        self.graph_retriever.close()

    def get_full_graph(self, limit: int = 200) -> dict:
        """Muestrea un subgrafo conectado incluyendo Papers, Biomarkers, Outcomes, AdverseEvents, etc."""
        driver = self.graph_retriever.driver
        with driver.session() as session:
            # Consulta actualizada para incluir Outcome y AdverseEvent
            query_ids = """
            MATCH (n)
            WHERE n:ClinicalTrial OR n:Paper OR n:Drug OR n:Biomarker 
                OR n:Outcome OR n:AdverseEvent OR n:Disease OR n:Intervention
            RETURN n.id AS id, labels(n)[0] AS label, n.title AS title, n.year AS year
            LIMIT $limit
            """
            records = session.run(query_ids, limit=limit).data()
            nodes, links, seen_nodes, seen_links = [], [], set(), set()

            def add_node(nid, nlabel, title=None, year=None):
                if nid is None: 
                    return
                if nid in seen_nodes:
                    for node in nodes:
                        if node["id"] == nid:
                            if title and not node.get("title"): 
                                node["title"] = title
                            if year and not node.get("year"): 
                                node["year"] = str(year)
                            break
                    return
                seen_nodes.add(nid)
                node_data = {"id": nid, "label": nlabel, "type": nlabel}
                if title: 
                    node_data["title"] = title
                if year: 
                    node_data["year"] = str(year)
                nodes.append(node_data)

            def add_link(source, target, rel):
                if not rel or not source or not target: 
                    return
                if (source, target, rel) not in seen_links:
                    seen_links.add((source, target, rel))
                    links.append({"source": source, "target": target, "rel": rel})

            for record in records:
                add_node(record["id"], record["label"], record["title"], record["year"])
                neighbor_query = """
                MATCH (root {id: $root_id})-[r]-(neighbor)
                RETURN root.id AS root_id, labels(root)[0] AS root_label,
                       neighbor.id AS n_id, labels(neighbor)[0] AS n_label,
                       neighbor.title AS n_title, neighbor.year AS n_year,
                       type(r) AS rel_type, startNode(r).id AS source_id, endNode(r).id AS target_id
                LIMIT 50
                """
                for n_record in session.run(neighbor_query, root_id=record["id"]):
                    add_node(n_record["n_id"], n_record["n_label"], n_record["n_title"], n_record["n_year"])
                    add_link(n_record["source_id"], n_record["target_id"], n_record["rel_type"])
            
            return {"nodes": nodes, "links": links}

        
    def ask(self, question: str) -> str:
        """Responde una pregunta usando GraphRAG."""
        print(f"  [DEBUG] Entendiendo pregunta...")
        entities = self.query_understanding.extract_entities(question)
        print(f"  [DEBUG] Entidades extraídas: {entities}")

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
            if context['trial'] and context['trial'].get('papers'):
                context['trial_papers'] = context['trial']['papers']
                
        elif query_type == 'drugs_for_trial' and entities.get('nct_id'):
            context['drugs_in_trial'] = self.graph_retriever.find_drugs_for_trial(entities['nct_id'])
            context['query_entity'] = f"Ensayo: {entities['nct_id']}"
            
        elif query_type == 'biomarkers_for_drug' and entities.get('drug'):
            context['biomarkers'] = self.graph_retriever.find_biomarkers_for_drug(entities['drug'])
            context['query_entity'] = f"Fármaco: {entities['drug']}"
            
        elif query_type == 'papers_for_trial' and entities.get('nct_id'):
            context['papers'] = self.graph_retriever.find_papers_for_trial(entities['nct_id'])
            context['query_entity'] = f"Ensayo: {entities['nct_id']}"
            
        elif query_type == 'papers_for_drug_disease' and entities.get('drug') and entities.get('disease'):
            context['papers'] = self.graph_retriever.find_papers_for_drug_and_disease(
                entities['drug'], entities['disease']
            )
            context['query_entity'] = f"Fármaco: {entities['drug']}, Enfermedad: {entities['disease']}"
            
        # 🆕 NUEVO: Exploración completa de una entidad
        elif query_type == 'entity_exploration' and entities.get('entity_id'):
            context['entity_info'] = self.graph_retriever.get_complete_entity_info(
                entities['entity_id'], 
                entities.get('entity_type')
            )
            context['query_entity'] = f"Entidad: {entities['entity_id']} ({entities.get('entity_type', 'Desconocido')})"
            
        else:
            context['message'] = "No se pudieron extraer entidades específicas de la pregunta o el tipo de consulta no es reconocido."

        print(f"  [DEBUG] Contexto del grafo: {context}")
        return self.generator.generate(question, context)

    
    def ask_with_graph(self, question: str) -> dict:
        """Responde una pregunta y devuelve el subgrafo asociado para visualizar."""
        answer = self.ask(question)
        entities = self.query_understanding.extract_entities(question)
        graph_data = {"nodes": [], "links": []}

        try:
            driver = self.graph_retriever.driver
            with driver.session() as session:
                nct_id = entities.get('nct_id')
                # Si es entity_exploration, usamos entity_id como fallback
                drug = entities.get('drug') or (entities.get('entity_id') if entities.get('entity_type') == 'Drug' else None)
                disease = entities.get('disease') or (entities.get('entity_id') if entities.get('entity_type') == 'Disease' else None)
                entity_id = entities.get('entity_id')

                seen_nodes = set()
                nodes = []
                links = []

                def add_node(nid, nlabel, ntitle, nyear):
                    if nid and nid not in seen_nodes:
                        seen_nodes.add(nid)
                        node_data = {"id": nid, "label": nlabel, "type": nlabel}
                        if nlabel == "Paper" and ntitle:
                            node_data["title"] = ntitle
                            node_data["year"] = str(nyear) if nyear else "N/A"
                        nodes.append(node_data)

                # PASO 1: Obtener el nodo central y sus vecinos directos
                query_main = """
                MATCH (center)
                WHERE ($nct_id IS NOT NULL AND center.id = $nct_id)
                   OR ($drug IS NOT NULL AND toLower(center.id) CONTAINS toLower($drug))
                   OR ($disease IS NOT NULL AND (
                       toLower(center.id) CONTAINS toLower($disease)
                       OR toLower(center.id) CONTAINS 'breast'
                       OR toLower(center.id) CONTAINS 'cancer'
                   ))
                   OR ($entity_id IS NOT NULL AND toLower(center.id) CONTAINS toLower($entity_id))
                OPTIONAL MATCH (center)-[r]-(neighbor)
                RETURN center.id AS c_id, labels(center)[0] AS c_label, center.title AS c_title, toString(center.year) AS c_year,
                       neighbor.id AS n_id, labels(neighbor)[0] AS n_label, neighbor.title AS n_title, toString(neighbor.year) AS n_year,
                       type(r) AS rel_type, startNode(r).id AS source_id, endNode(r).id AS target_id
                LIMIT 200
                """
                result_main = session.run(query_main, nct_id=nct_id, drug=drug, disease=disease, entity_id=entity_id)
                
                for record in result_main:
                    add_node(record["c_id"], record["c_label"], record["c_title"], record["c_year"])
                    
                    if record["n_id"]:
                        add_node(record["n_id"], record["n_label"], record["n_title"], record["n_year"])
                        if record["rel_type"] and record["source_id"] and record["target_id"]:
                            links.append({
                                "source": record["source_id"],
                                "target": record["target_id"],
                                "rel": record["rel_type"]
                            })

                # PASO 2: Si el nodo central es un ensayo, buscar papers relacionados indirectamente
                indirect_papers = []
                if nct_id:
                    query_papers = """
                    MATCH (t:ClinicalTrial {id: $nct_id})-[:TESTS|:STUDIES]-(mid)
                    MATCH (p:Paper)-[:EVALUATES|:STUDIES]-(mid)
                    WHERE NOT (p)-[:PUBLISHES_RESULTS_OF]->(t)
                    RETURN DISTINCT p.id AS p_id, p.title AS p_title, toString(p.year) AS p_year
                    """
                    result_papers = session.run(query_papers, nct_id=nct_id)
                    for prec in result_papers:
                        add_node(prec["p_id"], "Paper", prec["p_title"], prec["p_year"])
                        indirect_papers.append(prec["p_id"])

                    # PASO 3: Obtener las relaciones de esos papers indirectos
                    if indirect_papers:
                        query_paper_rels = """
                        MATCH (p:Paper) WHERE p.id IN $paper_ids
                        OPTIONAL MATCH (p)-[r]-(neighbor)
                        RETURN p.id AS p_id, neighbor.id AS n_id, labels(neighbor)[0] AS n_label, 
                               neighbor.title AS n_title, toString(neighbor.year) AS n_year,
                               type(r) AS rel_type, startNode(r).id AS source_id, endNode(r).id AS target_id
                        """
                        result_rels = session.run(query_paper_rels, paper_ids=list(set(indirect_papers)))
                        for rel_rec in result_rels:
                            if rel_rec["n_id"]:
                                add_node(rel_rec["n_id"], rel_rec["n_label"], rel_rec["n_title"], rel_rec["n_year"])
                                if rel_rec["rel_type"] and rel_rec["source_id"] and rel_rec["target_id"]:
                                    links.append({
                                        "source": rel_rec["source_id"],
                                        "target": rel_rec["target_id"],
                                        "rel": rel_rec["rel_type"]
                                    })

                graph_data = {"nodes": nodes, "links": links}
        except Exception as e:
            print(f"  [WARN] Error obteniendo subgrafo: {e}")

        return {
            "answer": answer,
            "graph": graph_data,
            "query_type": entities.get('query_type')
        }