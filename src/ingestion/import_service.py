"""
Servicio de importación batch de ensayos clínicos desde ClinicalTrials.gov.

Orquesta el flujo completo:
1. Validar capacidad del grafo (GraphMonitor)
2. Fetch ensayos por NCT ID desde la API
3. Parsear al formato interno (ClinicalTrial)
4. Extraer entidades con LLM
5. Insertar en Neo4j

Emite progreso en cada paso mediante un generador.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Generator

from .clinicaltrials_client import ClinicalTrialsClient
from .api_parser import parse_api_study
from .extractor import extract_entities_and_relations
from ..graph.neo4j_repository import Neo4jRepository
from ..graph.graph_monitor import GraphMonitor
from config.settings import MAX_BATCH_SIZE


class ImportEvent(str, Enum):
    """Tipos de eventos de progreso durante la importación."""
    VALIDATING = "validating"
    FETCHING = "fetching"
    EXTRACTING = "extracting"
    SAVING = "saving"
    DONE = "done"
    ERROR = "error"


@dataclass
class ImportProgress:
    """Evento de progreso emitido durante la importación."""
    event: ImportEvent
    current: int = 0
    total: int = 0
    message: str = ""
    success: bool = True
    data: dict = field(default_factory=dict)


class ImportService:
    """Servicio de importación batch de ensayos clínicos."""

    def __init__(self, repository: Neo4jRepository):
        self.repo = repository
        self.client = ClinicalTrialsClient()
        self.monitor = GraphMonitor(repository)

    def run_import(self, nct_ids: list[str]) -> Generator[ImportProgress, None, None]:
        """
        Ejecuta la importación batch de ensayos.
        
        Args:
            nct_ids: Lista de NCT IDs a importar (ej: ["NCT02689427", "NCT04565054"])
        
        Yields:
            ImportProgress con el estado actual en cada paso
        """
        total = len(nct_ids)

        # ─── Paso 0: Validar tamaño del batch ───
        yield ImportProgress(
            event=ImportEvent.VALIDATING,
            message=f"Validando batch de {total} ensayos..."
        )

        if total > MAX_BATCH_SIZE:
            yield ImportProgress(
                event=ImportEvent.ERROR,
                message=f"❌ El batch supera el máximo permitido ({MAX_BATCH_SIZE}). Recibidos: {total}",
                success=False
            )
            return

        if total == 0:
            yield ImportProgress(
                event=ImportEvent.ERROR,
                message="❌ No se proporcionaron ensayos para importar.",
                success=False
            )
            return

        # ─── Paso 1: Verificar capacidad del grafo ───
        can_import, capacity_msg = self.monitor.can_import(total)
        if not can_import:
            yield ImportProgress(
                event=ImportEvent.ERROR,
                message=capacity_msg,
                success=False
            )
            return

        yield ImportProgress(
            event=ImportEvent.VALIDATING,
            message=capacity_msg,
            data={"capacity": self.monitor.get_status()}
        )

        # ─── Paso 2: Filtrar ensayos que ya existen ───
        new_ids = []
        skipped_ids = []
        for nct_id in nct_ids:
            if self._trial_exists(nct_id):
                skipped_ids.append(nct_id)
            else:
                new_ids.append(nct_id)

        if skipped_ids:
            yield ImportProgress(
                event=ImportEvent.VALIDATING,
                message=f"⏭️ Saltando {len(skipped_ids)} ensayos ya existentes: {', '.join(skipped_ids[:5])}...",
                data={"skipped": skipped_ids}
            )

        if not new_ids:
            yield ImportProgress(
                event=ImportEvent.DONE,
                message="ℹ️ Todos los ensayos ya están en el grafo. No se importó nada nuevo.",
                data={"skipped": skipped_ids}
            )
            return

        total_to_import = len(new_ids)
        all_nodes = []
        all_edges = []
        imported_ids = []

        # ─── Paso 3: Fetch + Parse + Extract por cada ensayo ───
        for i, nct_id in enumerate(new_ids, 1):
            # Fetch desde la API
            yield ImportProgress(
                event=ImportEvent.FETCHING,
                current=i,
                total=total_to_import,
                message=f"[{i}/{total_to_import}] Descargando {nct_id} de ClinicalTrials.gov..."
            )

            try:
                raw_study = self.client.get_by_nct_id(nct_id)
                if raw_study is None:
                    yield ImportProgress(
                        event=ImportEvent.FETCHING,
                        current=i,
                        total=total_to_import,
                        message=f"⚠️ {nct_id} no encontrado en la API. Saltando.",
                        success=True
                    )
                    continue

                # Parsear a ClinicalTrial
                trial = parse_api_study(raw_study)

            except Exception as e:
                yield ImportProgress(
                    event=ImportEvent.ERROR,
                    current=i,
                    total=total_to_import,
                    message=f"⚠️ Error descargando {nct_id}: {str(e)}",
                    success=True  # No abortar todo el batch
                )
                continue

            # Extraer entidades con LLM
            yield ImportProgress(
                event=ImportEvent.EXTRACTING,
                current=i,
                total=total_to_import,
                message=f"[{i}/{total_to_import}] Extrayendo entidades de {nct_id} con LLM..."
            )

            try:
                result = extract_entities_and_relations(trial)
                nodes = result.get("nodes", [])
                edges = result.get("edges", [])

                if nodes:
                    all_nodes.extend(nodes)
                    all_edges.extend(edges)
                    imported_ids.append(nct_id)
                else:
                    yield ImportProgress(
                        event=ImportEvent.EXTRACTING,
                        current=i,
                        total=total_to_import,
                        message=f"⚠️ {nct_id}: LLM no extrajo entidades. Saltando.",
                        success=True
                    )

            except Exception as e:
                yield ImportProgress(
                    event=ImportEvent.ERROR,
                    current=i,
                    total=total_to_import,
                    message=f"⚠️ Error extrayendo {nct_id}: {str(e)}",
                    success=True  # Continuar con el resto
                )
                continue

        # ─── Paso 4: Guardar en Neo4j ───
        if all_nodes:
            yield ImportProgress(
                event=ImportEvent.SAVING,
                message=f"Guardando {len(all_nodes)} nodos y {len(all_edges)} relaciones en Neo4j..."
            )

            try:
                self.repo.save_nodes(all_nodes)
                self.repo.save_edges(all_edges)
            except Exception as e:
                yield ImportProgress(
                    event=ImportEvent.ERROR,
                    message=f"❌ Error guardando en Neo4j: {str(e)}",
                    success=False
                )
                return

        # ─── Paso 5: Completado ───
        yield ImportProgress(
            event=ImportEvent.DONE,
            message=(
                f"✅ Importación completada: {len(imported_ids)} ensayos nuevos, "
                f"{len(all_nodes)} nodos, {len(all_edges)} relaciones."
            ),
            data={
                "imported": imported_ids,
                "skipped": skipped_ids,
                "nodes_added": len(all_nodes),
                "edges_added": len(all_edges),
            }
        )

    def _trial_exists(self, nct_id: str) -> bool:
        """Verifica si un ensayo ya existe en el grafo."""
        with self.repo.driver.session() as session:
            result = session.run(
                "MATCH (t:ClinicalTrial {id: $nct_id}) RETURN count(t) AS count",
                nct_id=nct_id
            )
            record = result.single()
            return record["count"] > 0 if record else False