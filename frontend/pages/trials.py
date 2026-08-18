"""
Página de Ensayos Clínicos: doble panel (API ↔ Grafo) con detalle inferior.
"""

import streamlit as st
import pandas as pd
from api_client import (
    search_trials,
    import_trials,
    get_imported_trials,
    delete_trial,
    clear_imported,
    get_graph_stats,
)
from config.settings import MAX_BATCH_SIZE


def render():
    st.markdown("""
    Busca ensayos en **ClinicalTrials.gov** (panel izquierdo) y añádelos al grafo (panel derecho).
    """)
    
    # ─── Inicializar estado ───
    if "selected_ids" not in st.session_state:
        st.session_state.selected_ids = set()
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "selected_trial" not in st.session_state:
        st.session_state.selected_trial = None
    
    # ═══════════════════════════════════════════════════════════════
    # DOBLE PANEL PRINCIPAL
    # ═══════════════════════════════════════════════════════════════
    left_col, right_col = st.columns(2, gap="medium")
    
    # ─────────────────────────────────────────────────────────────
    # PANEL IZQUIERDO: Búsqueda en la API
    # ─────────────────────────────────────────────────────────────
    with left_col:
        st.subheader("🔍 Catálogo (ClinicalTrials.gov)")
        
        with st.form("search_form"):
            condition = st.text_input(
                "Condición / Enfermedad",
                value=st.session_state.get("last_condition", "breast cancer"),
                placeholder="breast cancer, lung cancer..."
            )
            
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                max_results = st.slider("Máx resultados", 5, 50, 20)
            with filter_col2:
                status_filter = st.selectbox(
                    "Status",
                    ["(Todos)", "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", "TERMINATED"]
                )
            
            intervention_filter = st.text_input(
                "Filtro por medicación (opcional)",
                placeholder="Ej: Pembrolizumab"
            )
            
            submitted = st.form_submit_button("🔎 Buscar", type="primary", use_container_width=True)
        
        # Ejecutar búsqueda
        if submitted and condition:
            with st.spinner(f"Buscando '{condition}' en ClinicalTrials.gov..."):
                try:
                    status = None if status_filter == "(Todos)" else status_filter
                    intervention = intervention_filter if intervention_filter else None
                    
                    results = search_trials(
                        condition=condition,
                        max_studies=max_results,
                        status=status,
                        intervention=intervention,
                    )
                    st.session_state.search_results = results["results"]
                    st.session_state.last_condition = condition
                except Exception as e:
                    st.error(f"Error en la búsqueda: {e}")
        
        # Obtener IDs ya importados para marcarlos
        try:
            imported = get_imported_trials()
            imported_ids = {t["nct_id"] for t in imported["trials"]}
        except Exception:
            imported_ids = set()
        
        # Mostrar resultados
        if st.session_state.search_results:
            st.markdown(f"**{len(st.session_state.search_results)} resultados**")
            
            # Construir filas para la lista
            for trial in st.session_state.search_results:
                nct_id = trial["nct_id"]
                is_imported = nct_id in imported_ids
                is_selected = nct_id in st.session_state.selected_ids
                
                # Checkbox (deshabilitado si ya está importado)
                checkbox_key = f"chk_{nct_id}"
                
                col_check, col_info = st.columns([0.5, 8])
                with col_check:
                    if is_imported:
                        st.markdown("✅")
                    else:
                        checked = st.checkbox(
                            "sel",
                            key=checkbox_key,
                            value=is_selected,
                            label_visibility="collapsed"
                        )
                        if checked:
                            st.session_state.selected_ids.add(nct_id)
                        else:
                            st.session_state.selected_ids.discard(nct_id)
                
                with col_info:
                    # Fila clickeable: muestra detalle abajo
                    button_label = f"**{nct_id}** · {trial['title'][:70]}{'...' if len(trial['title']) > 70 else ''}"
                    if st.button(button_label, key=f"btn_{nct_id}", use_container_width=True):
                        st.session_state.selected_trial = trial
                    
                    # Metadatos en caption
                    status_color = {
                        "RECRUITING": "🟢",
                        "COMPLETED": "🔵",
                        "ACTIVE_NOT_RECRUITING": "🟡",
                        "TERMINATED": "🔴",
                    }.get(trial["status"], "⚪")
                    
                    st.caption(
                        f"{status_color} {trial['status']} · "
                        f"{', '.join(trial['conditions'][:2])}"
                    )
                    
                    if is_imported:
                        st.caption("✅ Ya en el grafo")
                    
                    st.divider()
        else:
            st.info("👈 Haz una búsqueda para ver resultados")
    
    # ─────────────────────────────────────────────────────────────
    # PANEL DERECHO: Ensayos en el grafo
    # ─────────────────────────────────────────────────────────────
    with right_col:
        st.subheader("📊 Ensayos en el Grafo")
        
        # Controles de batch
        selected_count = len(st.session_state.selected_ids)
        st.markdown(f"**Seleccionados: {selected_count}/{MAX_BATCH_SIZE}**")
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            import_clicked = st.button(
                f"➡️ Importar ({selected_count})",
                type="primary",
                disabled=selected_count == 0,
                use_container_width=True,
            )
        with btn_col2:
            clear_clicked = st.button(
                "🗑️ Limpiar importados",
                use_container_width=True,
            )
        
        # ─── Acciones ───
        
        # IMPORTAR
        if import_clicked and st.session_state.selected_ids:
            nct_ids = list(st.session_state.selected_ids)
            
            # Confirmación
            with st.expander("⚠️ Confirmar importación", expanded=True):
                st.markdown(f"Se procesarán **{len(nct_ids)} ensayos** con LLM.")
                st.caption(f"IDs: {', '.join(nct_ids[:10])}{'...' if len(nct_ids) > 10 else ''}")
                confirm = st.button("✅ Sí, importar", type="primary")
                
                if confirm:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    error_messages = []
                    
                    for event in import_trials(nct_ids):
                        event_type = event.get("event")
                        message = event.get("message", "")
                        current = event.get("current", 0)
                        total = event.get("total", 0)
                        
                        if total > 0:
                            progress_bar.progress(current / total)
                        status_text.text(f"{event_type}: {message}")
                        
                        if event_type == "error" and not event.get("success", True):
                            error_messages.append(message)
                    
                    # Resultado final
                    if error_messages:
                        st.error("\n".join(error_messages))
                    else:
                        st.success(status_text.text)
                        st.session_state.selected_ids.clear()
                        st.rerun()
        
        # LIMPIAR
        if clear_clicked:
            with st.expander("⚠️ ¿Borrar todos los importados?", expanded=True):
                st.warning("Esto borrará todos los ensayos de fuente 'importado'. Los datos demo están protegidos.")
                if st.button("🗑️ Sí, borrar"):
                    try:
                        result = clear_imported()
                        st.success(f"Borrados {result.get('deleted_nodes', 0)} nodos")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        st.divider()
        
        # ─── Lista de ensayos ya en el grafo ───
        try:
            imported = get_imported_trials()
            trials = imported["trials"]
            
            if trials:
                st.markdown(f"**{len(trials)} ensayos importados**")
                
                for trial in trials:
                    col_info, col_del = st.columns([8, 1])
                    with col_info:
                        st.markdown(f"**{trial['nct_id']}**")
                        st.caption(trial['title'][:80])
                        st.caption(f"📅 {trial.get('imported_at', 'N/A')[:10]}")
                    with col_del:
                        if st.button("🗑️", key=f"del_{trial['nct_id']}"):
                            try:
                                delete_trial(trial["nct_id"])
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    st.divider()
            else:
                st.info("Aún no has importado ningún ensayo.")
        
        except Exception as e:
            st.error(f"Error cargando ensayos importados: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # PANEL INFERIOR: Detalle del ensayo seleccionado
    # ═══════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📋 Detalle del Ensayo")
    
    trial = st.session_state.selected_trial
    if trial is None:
        st.info("👆 Haz clic en un ensayo de cualquiera de los dos paneles para ver sus detalles aquí.")
        return
    
    st.markdown(f"### {trial['title']}")
    st.markdown(f"**NCT ID:** `{trial['nct_id']}` · **Status:** `{trial['status']}`")
    
    if trial.get("conditions"):
        st.markdown(f"**Condiciones:** {', '.join(trial['conditions'])}")
    
    if trial.get("interventions"):
        st.markdown("**Intervenciones:**")
        for intv in trial["interventions"]:
            tipo = intv.get("intervention_type", "?")
            nombre = intv.get("name", "Sin nombre")
            desc = intv.get("description", "")
            st.markdown(f"- **{nombre}** ({tipo}){': ' + desc if desc else ''}")
    
    if trial.get("eligibility_criteria"):
        with st.expander("Criterios de elegibilidad"):
            st.text(trial["eligibility_criteria"])