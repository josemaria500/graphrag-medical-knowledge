// ============================================
// api.js - Cliente HTTP para la API GraphRAG
// ============================================

const API = {
    async fetchGraphStats() {
        const response = await fetch('/api/graph/stats');
        if (!response.ok) throw new Error(`Error ${response.status}: stats`);
        return response.json();
    },

    async fetchGraph(limit = 200) {
        const response = await fetch(`/api/graph?limit=${limit}`);
        if (!response.ok) throw new Error(`Error ${response.status}: graph`);
        return response.json();
    },

    async searchTrials(condition, maxStudies = 10) {
        const params = new URLSearchParams({
            condition: condition,
            max_studies: maxStudies
        });
        const response = await fetch(`/api/search?${params}`);
        if (!response.ok) throw new Error(`Error ${response.status}: search`);
        return response.json();
    },

    async queryRAG(question) {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });
        if (!response.ok) throw new Error(`Error ${response.status}: query`);
        return response.json();
    },

    importTrials(nctIds) {
        return fetch('/api/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nct_ids: nctIds })
        });
    },

    async fetchImportedTrials() {
        const response = await fetch('/api/imported-trials');
        if (!response.ok) throw new Error(`Error ${response.status}: imported-trials`);
        return response.json();
    },

    // 🆕 Borrar un ensayo específico (protegido en backend si es demo)
    async deleteTrial(nctId) {
        const response = await fetch(`/api/trial/${nctId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(`Error ${response.status}: delete`);
        return response.json();
    },

    // 🆕 Borrar todos los importados (los demo quedan intactos)
    async clearImported() {
        const response = await fetch('/api/clear-imported', { method: 'POST' });
        if (!response.ok) throw new Error(`Error ${response.status}: clear`);
        return response.json();
    }
};