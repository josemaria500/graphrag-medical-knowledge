"""
Script de prueba para verificar la búsqueda en ClinicalTrials.gov.
Uso: python test_search.py
"""

from src.ingestion.search_service import SearchService


def main():
    print("🔍 Probando búsqueda en ClinicalTrials.gov...\n")

    service = SearchService()

    # Prueba 1: Búsqueda básica
    print("=" * 60)
    print("PRUEBA 1: Búsqueda de 'breast cancer' (10 resultados)")
    print("=" * 60)

    results = service.search("breast cancer", max_studies=10)
    print(f"\n✅ Encontrados {len(results)} ensayos:\n")

    for i, trial in enumerate(results, 1):
        print(f"  {i}. [{trial['nct_id']}] {trial['title'][:80]}...")
        print(f"     Status: {trial['status']} | Phase: {trial['phase']}")
        print(f"     Conditions: {', '.join(trial['conditions'][:3])}")
        print()

    # Prueba 2: Búsqueda con filtros
    print("=" * 60)
    print("PRUEBA 2: Búsqueda con filtro de status 'RECRUITING'")
    print("=" * 60)

    results_filtered = service.search(
        "lung cancer",
        max_studies=5,
        filters={"status": "RECRUITING"}
    )
    print(f"\n✅ Encontrados {len(results_filtered)} ensayos recruiting:\n")

    for trial in results_filtered:
        print(f"  [{trial['nct_id']}] {trial['title'][:60]}...")

    # Prueba 3: Detalle de un ensayo específico
    print("\n" + "=" * 60)
    print("PRUEBA 3: Detalle de NCT02689427")
    print("=" * 60)

    detail = service.get_study_detail("NCT02689427")
    if detail:
        print(f"\n  NCT ID: {detail['nct_id']}")
        print(f"  Title: {detail['title']}")
        print(f"  Status: {detail['status']}")
        print(f"  Phase: {detail['phase']}")
        print(f"  Conditions: {', '.join(detail['conditions'])}")
        print(f"  Interventions:")
        for intv in detail['interventions']:
            print(f"    - {intv['name']} ({intv['type']})")
    else:
        print("\n  ❌ Ensayo no encontrado")

    print("\n✅ Todas las pruebas completadas")


if __name__ == "__main__":
    main()