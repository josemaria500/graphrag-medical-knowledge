import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Límites de Neo4j Aura Free (verificar en tu consola de AuraDB)
# https://neo4j.com/cloud/aura-free/
NEO4J_NODE_LIMIT = int(os.getenv("NEO4J_NODE_LIMIT", "200000"))
NEO4J_REL_LIMIT = int(os.getenv("NEO4J_REL_LIMIT", "400000"))

# Umbral de aviso (85% del límite)
LIMIT_WARNING_THRESHOLD = float(os.getenv("LIMIT_WARNING_THRESHOLD", "0.85"))

# Límite de importación por batch
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "30"))

# Estimación de nodos por ensayo (se ajustará dinámicamente)
AVG_NODES_PER_TRIAL = int(os.getenv("AVG_NODES_PER_TRIAL", "15"))
AVG_RELS_PER_TRIAL = int(os.getenv("AVG_RELS_PER_TRIAL", "20"))

# Límites Neo4j Aura Free
NEO4J_NODE_LIMIT = int(os.getenv("NEO4J_NODE_LIMIT", "200000"))
NEO4J_REL_LIMIT = int(os.getenv("NEO4J_REL_LIMIT", "400000"))
LIMIT_WARNING_THRESHOLD = float(os.getenv("LIMIT_WARNING_THRESHOLD", "0.85"))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "30"))