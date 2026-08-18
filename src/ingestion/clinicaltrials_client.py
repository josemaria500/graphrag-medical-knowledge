"""
Cliente HTTP para la API v2 de ClinicalTrials.gov.

Documentación oficial: https://clinicaltrials.gov/data-api/api
Base URL: https://clinicaltrials.gov/api/v2/studies

Este cliente es GRATUITO (no usa LLM) y se encarga de:
- Buscar ensayos por condición/enfermedad
- Obtener detalle de un ensayo por NCT ID
- Manejar paginación automáticamente
"""

from typing import Iterator
import httpx


class ClinicalTrialsClient:
    """Cliente para la API pública de ClinicalTrials.gov."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    DEFAULT_TIMEOUT = 30.0
    MAX_PAGE_SIZE = 100  # Límite de la API

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def search(
        self,
        condition: str,
        max_studies: int = 30,
        page_size: int = 20,
        filters: dict | None = None,
    ) -> Iterator[dict]:
        """
        Busca ensayos clínicos por condición y devuelve un iterador de resultados.

        Args:
            condition: Enfermedad o condición a buscar (ej: "breast cancer")
            max_studies: Número máximo de estudios a devolver
            page_size: Cuántos resultados por página pedir a la API
            filters: Filtros adicionales (status, phase, intervention...)

        Yields:
            dict: Cada estudio en formato crudo de la API

        Example:
            client = ClinicalTrialsClient()
            for study in client.search("breast cancer", max_studies=10):
                print(study['protocolSection']['identificationModule']['nctId'])
        """
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        fetched = 0
        page_token = None

        with httpx.Client(timeout=self.timeout) as http:
            while fetched < max_studies:
                params = self._build_params(condition, page_size, filters, page_token)

                response = http.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                studies = data.get("studies", [])
                if not studies:
                    break

                for study in studies:
                    if fetched >= max_studies:
                        return
                    yield study
                    fetched += 1

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

    def get_by_nct_id(self, nct_id: str) -> dict | None:
        """
        Obtiene un ensayo específico por su NCT ID.

        Args:
            nct_id: Identificador del ensayo (ej: "NCT02689427")

        Returns:
            dict con los datos del estudio, o None si no se encuentra

        Raises:
            httpx.HTTPStatusError: Si la API devuelve un error
        """
        url = f"{self.BASE_URL}/{nct_id}"
        params = {"format": "json"}

        with httpx.Client(timeout=self.timeout) as http:
            response = http.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    def _build_params(
        self,
        condition: str,
        page_size: int,
        filters: dict | None,
        page_token: str | None,
    ) -> dict:
        """Construye los parámetros de la query para la API."""
        params = {
            "query.cond": condition,
            "pageSize": page_size,
            "format": "json",
        }

        if page_token:
            params["pageToken"] = page_token

        if filters:
            if filters.get("status"):
                params["filter.overallStatus"] = filters["status"]
            if filters.get("phase"):
                params["filter.phase"] = filters["phase"]
            if filters.get("intervention"):
                params["query.intr"] = filters["intervention"]

        return params