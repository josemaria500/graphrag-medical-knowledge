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

    def ask(self, question: str) -> str:
        """Responde una pregunta (compatible con main.py y el evaluador)."""
        entities = self.query_understanding.extract_entities(question)
        context = self._build_context(entities)
        return self.generator.generate(question, context)

    def ask_with_graph(self, question: str) -> dict:
        """Responde y además devuelve el subgrafo asociado a la pregunta."""
        entities = self.query_understanding.extract_entities(question)
        context = self._build_context(entities)
        answer = self.generator.generate(question, context)
        graph = self.graph_retriever.get_subgraph_for_query(
            entities.get("query_type"), entities
        )
        return {
            "answer": answer,
            "graph": graph,
            "query_type": entities.get("query_type"),
        }

    def get_full_graph(self, limit: int = 200) -> dict:
        """Muestra del grafo completo para visualización."""
        return self.graph_retriever.get_full_graph(limit)

    def _build_context(self, entities: dict) -> dict:
        """Construye el contexto del grafo según el tipo de query."""
        query_type = entities.get("query_type")
        context = {}

        if query_type == "drugs_for_disease" and entities.get("disease"):
            context["drugs"] = self.graph_retriever.find_drugs_for_disease(entities["disease"])
            context["query_entity"] = f"Enfermedad: {entities['disease']}"
        elif query_type == "trials_for_drug" and entities.get("drug"):
            context["trials"] = self.graph_retriever.find_trials_for_drug(entities["drug"])
            context["query_entity"] = f"Fármaco buscado: {entities['drug']}"
        elif query_type == "trial_details" and entities.get("nct_id"):
            context["trial"] = self.graph_retriever.get_trial_details(entities["nct_id"])
            context["query_entity"] = f"Ensayo: {entities['nct_id']}"
        elif query_type == "drugs_for_trial" and entities.get("nct_id"):
            context["drugs_in_trial"] = self.graph_retriever.find_drugs_for_trial(entities["nct_id"])
            context["query_entity"] = f"Ensayo: {entities['nct_id']}"
        elif query_type == "biomarkers_for_drug" and entities.get("drug"):
            context["biomarkers"] = self.graph_retriever.find_biomarkers_for_drug(entities["drug"])
            context["query_entity"] = f"Fármaco: {entities['drug']}"
        else:
            context["message"] = "No se pudieron extraer entidades específicas de la pregunta."
        return context