from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class Intervention(BaseModel):
    """Representa un fármaco o tratamiento probado en el ensayo."""
    name: str
    intervention_type: Optional[str] = None  # DRUG, BIOLOGICAL, etc.
    description: Optional[str] = None

class ClinicalTrial(BaseModel):
    """Representa un ensayo clínico normalizado."""
    nct_id: str = Field(..., description="Identificador único NCT01234567")
    title: str
    status: str  # recruiting, completed, etc.
    conditions: list[str] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    eligibility_criteria: Optional[str] = None
    has_results: bool = False
    
    class Config:
        # Esto permite crear el modelo desde un dict con keys en camelCase
        populate_by_name = True