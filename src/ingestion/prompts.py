EXTRACTION_PROMPT_TEMPLATE = """
Eres un experto en oncología y ensayos clínicos. Tu tarea es extraer entidades y relaciones de un ensayo clínico sobre cáncer de mama.

## ENSAYO CLÍNICO:
{trial_text}

## ENTIDADES A EXTRAER:
1. ClinicalTrial: El ensayo en sí (usa el NCT ID como identificador)
2. Drug: Fármacos o tratamientos farmacológicos (ej. Olaparib, Paclitaxel)
3. Intervention: Intervenciones no farmacológicas (ej. ejercicio físico, terapia psicológica, procedimientos quirúrgicos, técnicas de imagen)
4. Disease: Condiciones médicas o subtipos de cáncer
5. Biomarker: Genes, proteínas o marcadores biológicos mencionados

## RELACIONES A EXTRAER:
1. (ClinicalTrial)-[:TESTS {{phase: "Phase I/II/III/IV"}}]->(Drug o Intervention)
   - Si el ensayo prueba un fármaco, usa Drug
   - Si el ensayo prueba una intervención no farmacológica (ejercicio, terapia, procedimiento), usa Intervention
2. (ClinicalTrial)-[:STUDIES]->(Disease)
3. (Drug)-[:TARGETS]->(Biomarker) - solo si el fármaco está diseñado para atacar ese biomarcador específico

## FORMATO DE SALIDA:
Devuelve un JSON con esta estructura exacta:
{{
  "nodes": [
    {{"id": "NCT01234567", "label": "ClinicalTrial", "properties": {{"title": "...", "status": "..."}}}},
    {{"id": "Olaparib", "label": "Drug", "properties": {{}}}},
    {{"id": "Physical exercise", "label": "Intervention", "properties": {{}}}},
    {{"id": "BRCA1", "label": "Biomarker", "properties": {{}}}}
  ],
  "edges": [
    {{"source": "NCT01234567", "target": "Olaparib", "type": "TESTS", "properties": {{"phase": "Phase II"}}}},
    {{"source": "NCT01234567", "target": "Physical exercise", "type": "TESTS", "properties": {{"phase": "N/A"}}}},
    {{"source": "Olaparib", "target": "BRCA1", "type": "TARGETS", "properties": {{}}}}
  ]
}}

Solo devuelve el JSON, sin texto adicional.
"""