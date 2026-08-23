// ============================================
// app.js - Lógica general de la aplicación
// ============================================

// ---------- Cambio de pestañas ----------
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        document.getElementById('tab-' + this.dataset.tab).classList.add('active');

        if (this.dataset.tab === 'chat') {
            document.getElementById('chat-question').focus();
        }
        if (this.dataset.tab === 'trials') {
            loadImportedTrials();
        }
    });
});

// ---------- Estado de selección de ensayos ----------
let selectedNctIds = new Set();

function updateImportButton() {
    const btn = document.getElementById('btn-import-selected');
    btn.textContent = `⬇️ Importar seleccionados (${selectedNctIds.size})`;
    btn.disabled = selectedNctIds.size === 0;
}

// ---------- Búsqueda de ensayos (sin límite artificial: máx 100 de la API) ----------
const searchInput = document.getElementById('search-input');
const btnSearch = document.getElementById('btn-search');
const trialsResults = document.getElementById('trials-results');

async function searchTrials() {
    const condition = searchInput.value.trim();
    if (!condition) {
        trialsResults.innerHTML = '<div class="error">⚠️ Escribe una condición para buscar.</div>';
        return;
    }

    trialsResults.innerHTML = '<div class="loading">⏳ Buscando ensayos en ClinicalTrials.gov...</div>';

    try {
        const data = await API.searchTrials(condition, 100);
        const trials = data.results || [];

        if (trials.length === 0) {
            trialsResults.innerHTML = '<div class="loading">📭 No se encontraron ensayos de cáncer de mama para esa búsqueda.</div>';
            return;
        }

        trialsResults.innerHTML = trials.map(trial => `
            <div class="trial-card">
                <label>
                    <input type="checkbox" class="trial-checkbox" value="${trial.nct_id}">
                    Seleccionar para importar
                </label>
                <span class="nct-id">${trial.nct_id}</span>
                <span class="status status-${trial.status}">${trial.status}</span>
                <h3>${trial.title}</h3>
                <p><strong>Condiciones:</strong> ${(trial.conditions || []).join(', ')}</p>
            </div>
        `).join('');

        // Conectar checkboxes
        document.querySelectorAll('.trial-checkbox').forEach(cb => {
            cb.addEventListener('change', function() {
                if (this.checked) {
                    selectedNctIds.add(this.value);
                } else {
                    selectedNctIds.delete(this.value);
                }
                updateImportButton();
            });
        });

    } catch (error) {
        trialsResults.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

btnSearch.addEventListener('click', searchTrials);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchTrials();
});

// ---------- Importación con progreso SSE y control de límite ----------
const btnImport = document.getElementById('btn-import-selected');
const progressBox = document.getElementById('import-progress');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');

function handleImportEvent(event) {
    const total = event.total || 1;
    const current = event.current || 0;

    if (event.event === 'done') {
        progressFill.style.width = '100%';
        progressText.textContent = event.message;
    } else if (event.event === 'error') {
        progressText.textContent = `❌ ${event.message}`;
    } else {
        const pct = Math.min(95, Math.round((current / total) * 100));
        progressFill.style.width = pct + '%';
        progressText.textContent = event.message;
    }
}

// 🚦 Comprueba la capacidad del free tier y avisa solo si hace falta
async function checkCapacity(beforeImport) {
    try {
        const stats = await API.fetchGraphStats();

        if (beforeImport) {
            if (stats.is_at_limit) {
                alert('🚫 El grafo está al LÍMITE del free tier (200k nodos / 400k relaciones).\n\nNo se puede importar más. Borra ensayos importados primero.');
                return false;
            }
            if (stats.is_near_limit) {
                return confirm(`⚠️ El grafo ya usa el ${stats.overall_percentage}% del límite del free tier.\nImportar más ensayos podría excederlo.\n\n¿Continuar de todos modos?`);
            }
            return true;
        } else {
            // Después de importar: avisar solo si se excedió o se acercó al límite
            if (stats.is_at_limit) {
                alert('🚫 Tras la importación, el grafo ha ALCANZADO el límite del free tier.\nNo importes más ensayos sin borrar antes.');
            } else if (stats.is_near_limit) {
                alert(`⚠️ Tras la importación, el grafo usa el ${stats.overall_percentage}% del límite del free tier.`);
            }
            return true;
        }
    } catch (e) {
        // Si no se pueden leer las stats, no bloqueamos la importación
        return true;
    }
}

btnImport.addEventListener('click', async () => {
    const nctIds = Array.from(selectedNctIds);
    if (nctIds.length === 0) return;

    // 🚦 Comprobación previa de capacidad
    const canImport = await checkCapacity(true);
    if (!canImport) return;

    btnImport.disabled = true;
    progressBox.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '⏳ Iniciando importación...';

    try {
        const response = await API.importTrials(nctIds);
        if (!response.ok) throw new Error(`Error ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    handleImportEvent(JSON.parse(line.slice(6)));
                } catch (e) {
                    // línea incompleta, ignorar
                }
            }
        }
    } catch (error) {
        progressText.textContent = `❌ Error: ${error.message}`;
    }

    // 🚦 Comprobación posterior: avisar solo si se excedió el límite
    await checkCapacity(false);

    // Limpiar selección y refrescar
    selectedNctIds.clear();
    updateImportButton();
    document.querySelectorAll('.trial-checkbox').forEach(cb => cb.checked = false);
    loadImportedTrials();
    if (typeof loadGraph === 'function') loadGraph();
});

// ---------- Lista de ensayos en el grafo ----------
const importedList = document.getElementById('imported-list');

async function loadImportedTrials() {
    importedList.innerHTML = '<div class="loading">⏳ Cargando ensayos del grafo...</div>';
    try {
        const data = await API.fetchImportedTrials();
        const trials = data.trials || [];

        if (trials.length === 0) {
            importedList.innerHTML = '<div class="loading">📭 No hay ensayos en el grafo.</div>';
            return;
        }

        importedList.innerHTML = trials.map(trial => {
            const nctId = trial.nct_id || trial.id || '???';
            const title = (trial.title || '').slice(0, 90);
            const isDemo = trial.source === 'demo';
            return `
            <div class="imported-card">
                <div>
                    <span class="nct-id">${nctId}</span>
                    <span class="trial-title">${title}</span>
                </div>
                ${isDemo
                    ? '<span class="badge-demo">DEMO 🔒</span>'
                    : `<button class="btn-delete" data-nct="${nctId}">🗑️ Borrar</button>`}
            </div>`;
        }).join('');

        // Conectar botones de borrar
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', async function() {
                const nctId = this.dataset.nct;
                if (!confirm(`¿Borrar el ensayo ${nctId} del grafo?`)) return;
                this.textContent = '⏳ ...';
                try {
                    const result = await API.deleteTrial(nctId);
                    if (result.status !== 'ok') {
                        alert(`⚠️ ${result.message}`);
                    }
                    loadImportedTrials();
                    if (typeof loadGraph === 'function') loadGraph();
                } catch (error) {
                    alert(`❌ Error: ${error.message}`);
                }
            });
        });
    } catch (error) {
        importedList.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

// ---------- Borrar todos los importados ----------
const btnClearAll = document.getElementById('btn-clear-all');
btnClearAll.addEventListener('click', async () => {
    if (!confirm('⚠️ Se borrarán TODOS los ensayos importados desde la API.\nLos ensayos DEMO 🔒 están protegidos y NO se borrarán.\n\n¿Continuar?')) return;
    btnClearAll.textContent = '⏳ Borrando...';
    try {
        const result = await API.clearImported();
        alert(`✅ Borrados ${result.deleted_nodes} nodos del grafo.`);
        loadImportedTrials();
        if (typeof loadGraph === 'function') loadGraph();
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    } finally {
        btnClearAll.textContent = '🗑️ Borrar todos los importados';
    }
});

// Cargar lista al iniciar
document.addEventListener('DOMContentLoaded', loadImportedTrials);

// ---------- Chat RAG ----------
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-question');
const btnAsk = document.getElementById('btn-ask');

function addMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${sender}`;
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function askQuestion() {
    const question = chatInput.value.trim();
    if (!question) return;

    addMessage(question, 'user');
    chatInput.value = '';

    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'chat-message assistant';
    loadingMsg.textContent = '⏳ Analizando pregunta y consultando Neo4j...';
    chatMessages.appendChild(loadingMsg);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const result = await API.queryRAG(question);
        loadingMsg.textContent = result.answer || 'No se encontró respuesta.';
    } catch (error) {
        loadingMsg.textContent = `❌ Error: ${error.message}`;
        loadingMsg.classList.add('error');
    }
}

btnAsk.addEventListener('click', askQuestion);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') askQuestion();
});

// ---------- Botones de preguntas precargadas ----------
document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        chatInput.value = this.textContent;
        askQuestion();
    });
});