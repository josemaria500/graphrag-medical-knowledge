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
            context['query_entity'] = f"Fármaco buscado: {entities['drug']}"  # ← CLAVE
        
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