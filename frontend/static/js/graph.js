// ============================================
// graph.js - Renderizado del grafo con Cytoscape.js
// ============================================

// Colores por tipo de nodo
const NODE_COLORS = {
    'ClinicalTrial': '#ff4b4b',
    'Drug': '#4ecdc4',
    'Disease': '#ffa07a',
    'Biomarker': '#9b59b6',
    'Intervention': '#3498db'
};

let cy = null;

/**
 * Inicializa o actualiza el grafo con datos de la API.
 */
async function loadGraph() {
    const statsEl = document.getElementById('graph-stats');
    const cyContainer = document.getElementById('cy');

    try {
        statsEl.textContent = '⏳ Cargando grafo...';

        // Obtener datos del grafo
        const graphData = await API.fetchGraph(200);
        const stats = await API.fetchGraphStats();

        // Actualizar estadísticas
        statsEl.textContent = `📊 ${stats.node_count} nodos · ${stats.rel_count} relaciones · ${stats.node_percentage}% del límite`;

        // Transformar datos al formato de Cytoscape
        const cyNodes = graphData.nodes.map(node => ({
            data: {
                id: node.id,
                label: node.id,
                type: node.label || node.type || 'Unknown'
            }
        }));

        const cyEdges = graphData.links.map(link => ({
            data: {
                source: link.source,
                target: link.target,
                label: link.type || link.rel || ''
            }
        }));

        // Destruir instancia anterior si existe
        if (cy) {
            cy.destroy();
        }

        // Inicializar Cytoscape
        cy = cytoscape({
            container: cyContainer,
            elements: { nodes: cyNodes, edges: cyEdges },
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': function(ele) {
                            return NODE_COLORS[ele.data('type')] || '#95a5a6';
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
                        'border-color': '#ffffff',
                        'background-color': '#f39c12'
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 1000,
                nodeRepulsion: 8000,
                idealEdgeLength: 100,
                gravity: 0.25
            },
            wheelSensitivity: 0.3
        });

        // Evento: click en nodo muestra info
        cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            console.log('Nodo seleccionado:', node.data());
        });

    } catch (error) {
        statsEl.textContent = `❌ Error: ${error.message}`;
        console.error('Error cargando grafo:', error);
    }
}

// Cargar grafo al iniciar
document.addEventListener('DOMContentLoaded', loadGraph);

// Botón recargar
document.getElementById('btn-reload').addEventListener('click', loadGraph);