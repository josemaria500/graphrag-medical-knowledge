from .models import ClinicalTrial

def format_trial_for_llm(trial: ClinicalTrial) -> str:
    """
    Convierte un objeto ClinicalTrial en texto legible para el LLM.
    """
    text = f"""
NCT ID: {trial.nct_id}
Título: {trial.title}
Estado: {trial.status}
Condiciones médicas: {', '.join(trial.conditions) if trial.conditions else 'No especificadas'}

Intervenciones/Fármacos:
"""
    
    for intervention in trial.interventions:
        text += f"- {intervention.name}"
        if intervention.intervention_type:
            text += f" (Tipo: {intervention.intervention_type})"
        if intervention.description:
            text += f": {intervention.description}"
        text += "\n"
    
    if trial.eligibility_criteria:
        text += f"\nCriterios de elegibilidad:\n{trial.eligibility_criteria[:1000]}..."  # Limitamos a 1000 chars para no gastar tokens
    
    text += f"\n¿Tiene resultados publicados?: {'Sí' if trial.has_results else 'No'}"
    
    return text