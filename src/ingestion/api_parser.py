"""
Adapter que transforma el formato JSON de la API v2 de ClinicalTrials.gov
a objetos ClinicalTrial del dominio.
"""

from datetime import datetime
from .models import ClinicalTrial, Intervention


def parse_api_study(study: dict) -> ClinicalTrial:
    """
    Transforma un estudio del formato API v2 a un objeto ClinicalTrial.
    """
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status_module = proto.get("statusModule", {})
    conditions_module = proto.get("conditionsModule", {})
    interventions_module = proto.get("armsInterventionsModule", {})

    title = (
        ident.get("officialTitle")
        or ident.get("briefTitle")
        or "Untitled Study"
    )

    conditions = conditions_module.get("conditions", [])

    interventions = []
    for intervention in interventions_module.get("interventions", []):
        interventions.append(Intervention(
            name=intervention.get("name", ""),
            intervention_type=intervention.get("type"),
            description=intervention.get("description", ""),
        ))

    return ClinicalTrial(
        nct_id=ident.get("nctId", ""),
        title=title,
        status=status_module.get("overallStatus", "Unknown"),
        conditions=conditions,
        interventions=interventions,
        source="clinicaltrials_api",  # ← ETIQUETADO DE ORIGEN
        imported_at=datetime.utcnow(),
    )


def parse_api_studies(studies: list[dict]) -> list[ClinicalTrial]:
    """Transforma una lista de estudios a objetos ClinicalTrial."""
    return [parse_api_study(study) for study in studies]