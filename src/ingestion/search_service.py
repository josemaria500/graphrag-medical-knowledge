"""
Servicio de búsqueda de ensayos clínicos en ClinicalTrials.gov.

Este servicio es GRATUITO (no usa LLM). Solo consulta la API pública
y devuelve resultados crudos para mostrar en el panel izquierdo.
"""

from .clinicaltrials_client import ClinicalTrialsClient
from .api_parser import parse_api_study


class SearchService:
    """Servicio de búsqueda en la API de ClinicalTrials.gov."""

    def __init__(self):
        self.client = ClinicalTrialsClient()

    def search(
        self,
        condition: str,
        max_studies: int = 30,
        filters: dict | None = None,
    ) -> list:
        """
        Busca ensayos clínicos y devuelve resultados parseados.

        Args:
            condition: Enfermedad o condición (ej: "breast cancer")
            max_studies: Límite de resultados
            filters: Filtros adicionales (status, phase, intervention)

        Returns:
            Lista de objetos ClinicalTrial
        """
        parsed_results = []

        for study in self.client.search(condition, max_studies, filters=filters):
            # parse_api_study ya asigna source="clinicaltrials_api" internamente
            parsed = parse_api_study(study)
            parsed_results.append(parsed)

        return parsed_results

    def get_study_detail(self, nct_id: str):
        """
        Obtiene el detalle completo de un ensayo por NCT ID.

        Args:
            nct_id: Identificador del ensayo (ej: "NCT02689427")

        Returns:
            Objeto ClinicalTrial, o None si no existe
        """
        study = self.client.get_by_nct_id(nct_id)
        if study is None:
            return None
        return parse_api_study(study)