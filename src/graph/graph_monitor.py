"""
Monitor de capacidad del grafo Neo4j.

Vigila el uso del free tier de Neo4j Aura y avisa cuando
estamos cerca del límite. También estima el impacto de
importaciones antes de ejecutarlas.
"""

from config.settings import (
    NEO4J_NODE_LIMIT,
    NEO4J_REL_LIMIT,
    LIMIT_WARNING_THRESHOLD,
    AVG_NODES_PER_TRIAL,
    AVG_RELS_PER_TRIAL,
)


class GraphMonitor:
    """Monitor de capacidad del grafo."""

    def __init__(self, repository):
        """
        Args:
            repository: Instancia de Neo4jRepository
        """
        self.repo = repository

    def get_status(self) -> dict:
        """
        Obtiene el estado actual de capacidad del grafo.
        
        Returns:
            dict con:
                - node_count: nodos actuales
                - rel_count: relaciones actuales
                - node_limit: límite de nodos
                - rel_limit: límite de relaciones
                - node_percentage: % de uso de nodos
                - rel_percentage: % de uso de relaciones
                - overall_percentage: % máximo (el más restrictivo)
                - is_near_limit: True si supera el umbral de aviso
                - is_at_limit: True si está al 100%
        """
        stats = self.repo.get_stats()
        
        node_count = stats["node_count"]
        rel_count = stats["rel_count"]
        
        node_percentage = (node_count / NEO4J_NODE_LIMIT) * 100
        rel_percentage = (rel_count / NEO4J_REL_LIMIT) * 100
        overall_percentage = max(node_percentage, rel_percentage)
        
        return {
            "node_count": node_count,
            "rel_count": rel_count,
            "node_limit": NEO4J_NODE_LIMIT,
            "rel_limit": NEO4J_REL_LIMIT,
            "node_percentage": round(node_percentage, 1),
            "rel_percentage": round(rel_percentage, 1),
            "overall_percentage": round(overall_percentage, 1),
            "is_near_limit": overall_percentage >= (LIMIT_WARNING_THRESHOLD * 100),
            "is_at_limit": overall_percentage >= 100,
        }

    def estimate_batch_impact(self, batch_size: int) -> dict:
        """
        Estima el impacto de importar un batch de ensayos.
        
        Args:
            batch_size: Número de ensayos a importar
        
        Returns:
            dict con:
                - estimated_nodes: nodos que se añadirán
                - estimated_rels: relaciones que se añadirán
                - new_node_percentage: % de nodos tras importar
                - new_rel_percentage: % de relaciones tras importar
                - would_exceed_limit: True si superaría el límite
                - would_trigger_warning: True si superaría el umbral de aviso
        """
        stats = self.repo.get_stats()
        
        estimated_nodes = batch_size * AVG_NODES_PER_TRIAL
        estimated_rels = batch_size * AVG_RELS_PER_TRIAL
        
        new_node_count = stats["node_count"] + estimated_nodes
        new_rel_count = stats["rel_count"] + estimated_rels
        
        new_node_percentage = (new_node_count / NEO4J_NODE_LIMIT) * 100
        new_rel_percentage = (new_rel_count / NEO4J_REL_LIMIT) * 100
        new_overall = max(new_node_percentage, new_rel_percentage)
        
        return {
            "estimated_nodes": estimated_nodes,
            "estimated_rels": estimated_rels,
            "new_node_percentage": round(new_node_percentage, 1),
            "new_rel_percentage": round(new_rel_percentage, 1),
            "new_overall_percentage": round(new_overall, 1),
            "would_exceed_limit": new_overall >= 100,
            "would_trigger_warning": new_overall >= (LIMIT_WARNING_THRESHOLD * 100),
        }

    def can_import(self, batch_size: int) -> tuple[bool, str]:
        """
        Verifica si se puede importar un batch sin superar límites.
        
        Args:
            batch_size: Número de ensayos a importar
        
        Returns:
            tupla (puede_importar: bool, mensaje: str)
        """
        status = self.get_status()
        
        # Si ya estamos al límite, no se puede importar
        if status["is_at_limit"]:
            return False, (
                f"🚫 El grafo ha alcanzado el límite del plan gratuito de Neo4j. "
                f"Nodos: {status['node_count']}/{status['node_limit']} | "
                f"Relaciones: {status['rel_count']}/{status['rel_limit']}. "
                f"Borra ensayos importados para liberar espacio."
            )
        
        # Estimar impacto del batch
        impact = self.estimate_batch_impact(batch_size)
        
        # Si superaría el límite, bloquear
        if impact["would_exceed_limit"]:
            return False, (
                f"🚫 La importación de {batch_size} ensayos añadiría ~{impact['estimated_nodes']} nodos "
                f"y ~{impact['estimated_rels']} relaciones, superando el límite del plan gratuito. "
                f"Reduce el tamaño del batch o borra ensayos existentes."
            )
        
        # Si superaría el umbral de aviso, permitir pero con warning
        if impact["would_trigger_warning"]:
            return True, (
                f"⚠️ Atención: esta importación llevará el grafo al "
                f"{impact['new_overall_percentage']}% de capacidad. "
                f"Considera limpiar ensayos antiguos pronto."
            )
        
        # Todo OK
        return True, "✅ Capacidad suficiente para importar."

    def get_capacity_message(self) -> str:
        """
        Devuelve un mensaje legible sobre el estado de capacidad.
        Útil para mostrar en la UI.
        """
        status = self.get_status()
        
        if status["is_at_limit"]:
            icon = "🚫"
            color = "red"
        elif status["is_near_limit"]:
            icon = "⚠️"
            color = "orange"
        else:
            icon = "✅"
            color = "green"
        
        return (
            f"{icon} Grafo: {status['node_count']:,} / {status['node_limit']:,} nodos "
            f"({status['node_percentage']}%) | "
            f"{status['rel_count']:,} / {status['rel_limit']:,} relaciones "
            f"({status['rel_percentage']}%)"
        )