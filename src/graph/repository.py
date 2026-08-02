from abc import ABC, abstractmethod
from typing import Any

class GraphRepository(ABC):
    """Interfaz abstracta para operaciones de grafo."""
    
    @abstractmethod
    def save_nodes(self, nodes: list[dict[str, Any]]) -> None:
        """Guarda una lista de nodos en el grafo."""
        pass
    
    @abstractmethod
    def save_edges(self, edges: list[dict[str, Any]]) -> None:
        """Guarda una lista de relaciones en el grafo."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Limpia todos los datos del grafo."""
        pass