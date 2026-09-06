// ============================================
// chat-graph.js - Grafo contextual en el Chat RAG
// ============================================

let cyChat = null;

// Colores por tipo de nodo (mismos que graph.js)
const CHAT_NODE_COLORS = {
    'ClinicalTrial': '#ff4b4b',
    'Drug': '#4ecdc4',
    'Disease': '#ffa07a',
    'Biomarker': '#9b59b6',
    'Intervention': '#3498db',
    'Paper': '#8e44ad'
};

/**
 * Dibuja el subgrafo contextual en el panel derecho del chat.
 */
function drawChatGraph(graphData) {
    const container = document.getElementById('cy-chat');
    if (!container) return;

    // Si ya existe una instancia, destruirla
    if (cyChat) {
        cyChat.destroy();
    }

    // Si no hay datos, mostrar mensaje
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
        container.innerHTML = '<p style="color: #a0aec0; text-align: center; padding: 2rem;">Sin grafo contextual para esta consulta.</p>';
        return;
    }

    // Transformar datos al formato de Cytoscape
    const cyNodes = graphData.nodes.map(node => ({
        data: {
            id: node.id,
            label: node.id,
            type: node.label || node.type || 'Unknown',
            title: node.title || null,
            year: node.year || null
        }
    }));

    const cyEdges = graphData.links.map(link => ({
        data: {
            source: link.source,
            target: link.target,
            label: link.rel || ''
        }
    }));

    // Inicializar Cytoscape
    cyChat = cytoscape({
        container: container,
        elements: { nodes: cyNodes, edges: cyEdges },
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': function(ele) {
                        return CHAT_NODE_COLORS[ele.data('type')] || '#95a5a6';
                    },
                    'label': 'data(label)',
                    'color': '#ffffff',
                    'font-size': '10px',
                    'text-valign': 'bottom',
                    'text-margin-y': '5px',
                    'width': 30,
                    'height': 30,
                    'border-width': 2,
                    'border-color': '#2c3e50'
                }
            },
            // Estilo específico para nodos Paper (hexágono morado)
            {
                selector: 'node[type = "Paper"]',
                style: {
                    'shape': 'hexagon',
                    'width': 40,
                    'height': 40,
                    'background-color': '#8e44ad',
                    'border-color': '#6c3483',
                    'label': 'data(id)',
                    'font-size': '9px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'text-margin-y': 0
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#5a6270',
                    'target-arrow-color': '#5a6270',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'font-size': '8px',
                    'color': '#a0aec0',
                    'text-rotation': 'autorotate'
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': 4,
                    'border-color': '#f39c12'
                }
            }
        ],
        layout: {
            name: 'cose',
            animate: true,
            animationDuration: 800,
            nodeRepulsion: 6000,
            idealEdgeLength: 80,
            gravity: 0.25
        },
        wheelSensitivity: 0.3
    });

    // Evento: click en nodo muestra info
    cyChat.on('tap', 'node', function(evt) {
        const data = evt.target.data();
        console.log('Nodo seleccionado en chat:', data);
        
        // Si es un Paper, mostrar detalles en el panel flotante del grafo principal
        if (data.type === 'Paper') {
            const detailsPanel = document.getElementById('node-details');
            const detailsContent = document.getElementById('node-details-content');
            if (detailsPanel && detailsContent) {
                const pmid = data.id;
                const title = data.title || 'Título no disponible';
                const year = data.year || 'N/A';
                
                detailsContent.innerHTML = `
                    <h3>📄 Paper Científico</h3>
                    <p><strong>PMID:</strong> ${pmid}</p>
                    <p><strong>Año:</strong> ${year}</p>
                    <p><strong>Título:</strong> <em>${title}</em></p>
                    <a href="https://pubmed.ncbi.nlm.nih.gov/${pmid}/" target="_blank" class="pubmed-link">
                        🔗 Ver en PubMed
                    </a>
                `;
                detailsPanel.style.display = 'block';
            }
        }
    });

    // Click en fondo para cerrar panel
    cyChat.on('tap', function(evt) {
        if (evt.target === cyChat) {
            const detailsPanel = document.getElementById('node-details');
            if (detailsPanel) detailsPanel.style.display = 'none';
        }
    });
}

/**
 * Intercepta las respuestas del chat para extraer el grafo.
 * Se conecta con app.js modificando el fetch original.
 */
function initChatGraphInterceptor() {
    const originalFetch = window.fetch;
    window.fetch = async function(url, options) {
        const response = await originalFetch.apply(this, arguments);
        
        // Si es la petición de query, interceptar la respuesta
        if (url.includes('/api/query') && response.ok) {
            const clonedResponse = response.clone();
            try {
                const data = await clonedResponse.json();
                if (data.graph) {
                    // Esperar un poco para que el chat se renderice
                    setTimeout(() => drawChatGraph(data.graph), 300);
                }
            } catch (e) {
                console.warn('No se pudo parsear respuesta del chat:', e);
            }
        }
        
        return response;
    };
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    initChatGraphInterceptor();
});