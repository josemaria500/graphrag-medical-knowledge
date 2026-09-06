// ============================================
// papers.js - Gestión de Papers (Búsqueda e Importación)
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('paper-search-input');
    const btnSearch = document.getElementById('btn-paper-search');
    const searchResults = document.getElementById('paper-search-results');
    const importedList = document.getElementById('imported-papers-list');
    const btnClearAll = document.getElementById('btn-clear-all-papers');

    // Cargar papers importados al iniciar
    loadImportedPapers();

    // Evento: Buscar en PubMed
    btnSearch.addEventListener('click', async () => {
        const query = searchInput.value.trim();
        if (!query) return alert('Por favor, introduce una consulta de búsqueda.');

        searchResults.innerHTML = '<p class="loading">🔎 Buscando en PubMed...</p>';
        
        try {
            const response = await fetch(`/api/search-papers?query=${encodeURIComponent(query)}&max_results=10`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                searchResults.innerHTML = data.results.map(paper => `
                    <div class="trial-card">
                        <h3>${paper.title}</h3>
                        <p class="nct-id">PMID: ${paper.pmid} | ${paper.year} | ${paper.journal}</p>
                        <p style="font-size: 0.85rem; color: #cbd5e0; margin: 0.5rem 0;">
                            ${paper.abstract.substring(0, 200)}...
                        </p>
                        <button class="btn-primary btn-import-paper" data-pmid="${paper.pmid}">
                            ⬇️ Importar al Grafo
                        </button>
                    </div>
                `).join('');

                // Añadir eventos a los botones de importar
                document.querySelectorAll('.btn-import-paper').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const pmid = e.target.dataset.pmid;
                        e.target.disabled = true;
                        e.target.textContent = '⏳ Importando...';
                        
                        try {
                            const res = await fetch(`/api/ingest/paper/${pmid}`, { method: 'POST' });
                            const result = await res.json();
                            if (res.ok) {
                                e.target.textContent = '✅ Importado';
                                loadImportedPapers(); // Recargar lista derecha
                            } else {
                                alert(`Error: ${result.detail}`);
                                e.target.disabled = false;
                                e.target.textContent = '⬇️ Importar al Grafo';
                            }
                        } catch (err) {
                            alert('Error de red al importar.');
                            e.target.disabled = false;
                            e.target.textContent = '⬇️ Importar al Grafo';
                        }
                    });
                });
            } else {
                searchResults.innerHTML = '<p class="error">No se encontraron papers para esta consulta.</p>';
            }
        } catch (error) {
            searchResults.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        }
    });

    // Evento: Borrar todos los papers
    if (btnClearAll) {
        btnClearAll.addEventListener('click', async () => {
            if (!confirm('¿Estás seguro de que quieres borrar TODOS los papers del grafo?')) return;
            
            try {
                const res = await fetch('/api/papers', { method: 'DELETE' });
                const result = await res.json();
                if (res.ok) {
                    alert(`Se borraron ${result.deleted} papers.`);
                    loadImportedPapers();
                } else {
                    alert(`Error: ${result.detail}`);
                }
            } catch (error) {
                alert('Error de red al borrar.');
            }
        });
    }

    // Función para cargar la lista de papers importados
    async function loadImportedPapers() {
        importedList.innerHTML = '<p class="loading">Cargando papers...</p>';
        try {
            const response = await fetch('/api/papers');
            const data = await response.json();
            
            if (data.papers && data.papers.length > 0) {
                importedList.innerHTML = data.papers.map(paper => `
                    <div class="imported-card">
                        <div>
                            <span class="nct-id">PMID: ${paper.pmid} (${paper.year})</span>
                            <span class="trial-title">${paper.title}</span>
                        </div>
                        <button class="btn-delete btn-delete-paper" data-pmid="${paper.pmid}">
                            🗑️ Borrar
                        </button>
                    </div>
                `).join('');

                // Eventos para borrar individualmente
                document.querySelectorAll('.btn-delete-paper').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const pmid = e.target.dataset.pmid;
                        if (!confirm('¿Borrar este paper del grafo?')) return;
                        
                        try {
                            const res = await fetch(`/api/paper/${pmid}`, { method: 'DELETE' });
                            if (res.ok) {
                                loadImportedPapers(); // Recargar
                            } else {
                                alert('Error al borrar.');
                            }
                        } catch (err) {
                            alert('Error de red.');
                        }
                    });
                });
            } else {
                importedList.innerHTML = '<p style="color: #718096; text-align: center;">No hay papers importados aún.</p>';
            }
        } catch (error) {
            importedList.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        }
    }
});