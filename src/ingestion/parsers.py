import json
from pathlib import Path
from .models import ClinicalTrial, Intervention

def parse_clinical_trials(json_path: str) -> list[ClinicalTrial]:
    """
    Parsea el JSON crudo de ClinicalTrials.gov y devuelve una lista de objetos ClinicalTrial.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    trials = []
    
    # La API devuelve los estudios en data['studies']
    for study in data.get('studies', []):
        protocol = study.get('protocolSection', {})
        
        # 1. Extraer identificador (obligatorio)
        nct_id = protocol.get('identificationModule', {}).get('nctId')
        if not nct_id:
            continue  # Saltar si no tiene identificador
        
        # 2. Extraer título
        title = protocol.get('identificationModule', {}).get('briefTitle', 'Sin título')
        
        # 3. Extraer estado
        status = protocol.get('statusModule', {}).get('overallStatus', 'unknown')
        
        # 4. Extraer condiciones médicas
        conditions_module = protocol.get('conditionsModule', {})
        conditions = conditions_module.get('conditions', [])
        
        # 5. Extraer intervenciones
        arms_interventions = protocol.get('armsInterventionsModule', {})
        interventions_raw = arms_interventions.get('interventions', [])
        
        interventions = []
        for intervention_data in interventions_raw:
            intervention = Intervention(
                name=intervention_data.get('name', 'Unknown'),
                intervention_type=intervention_data.get('type'),
                description=intervention_data.get('description')
            )
            interventions.append(intervention)
        
        # 6. Extraer criterios de elegibilidad
        eligibility_module = protocol.get('eligibilityModule', {})
        eligibility_criteria = eligibility_module.get('eligibilityCriteria')
        
        # 7. Extraer si tiene resultados
        # Este campo puede estar en differentPlaces, lo buscamos en varios sitios
        has_results = study.get('hasResults', False)
        
        # Crear el objeto ClinicalTrial
        trial = ClinicalTrial(
            nct_id=nct_id,
            title=title,
            status=status,
            conditions=conditions,
            interventions=interventions,
            eligibility_criteria=eligibility_criteria,
            has_results=has_results
        )
        
        trials.append(trial)
    
    return trials


# Script de prueba
if __name__ == "__main__":
    trials = parse_clinical_trials('data/raw/clinical_trials_sample.json')
    print(f"Parseados {len(trials)} ensayos")
    if trials:
        print("\nPrimer ensayo:")
        print(f"NCT ID: {trials[0].nct_id}")
        print(f"Título: {trials[0].title}")
        print(f"Estado: {trials[0].status}")
        print(f"Condiciones: {trials[0].conditions}")
        print(f"Intervenciones: {[i.name for i in trials[0].interventions]}")
        print(f"¿Tiene resultados?: {trials[0].has_results}")