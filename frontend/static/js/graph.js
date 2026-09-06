// ============================================
// graph.js - Renderizado del grafo con Cytoscape.js
// ============================================

// Colores por tipo de nodo
const NODE_COLORS = {
    'ClinicalTrial': '#ff4b4b',
    'Drug': '#4ecdc4',
    'Disease': '#ffa07a',
    'Biomarker': '#9b59b6',
    'Intervention': '#3498db',
    'Paper': '#8e44ad',
    'Outcome': '#2ecc71',           
    'AdverseEvent': '#e74c3c'       
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
                type: node.label || node.type || 'Unknown',
                title: node.title || null,
                year: node.year || null
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
                // Estilo específico para nodos Paper
                {
                    selector: 'node[type = "Paper"]',
                    style: {
                        'shape': 'hexagon',
                        'width': 40,
                        'height': 40,
                        'background-color': '#8e44ad',
                        'border-color': '#6c3483',
                        'label': 'data(id)', // Muestra el PMID
                        'font-size': '9px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'text-margin-y': 0
                    }
                },
                // Estilo para nodos Outcome (resultados clínicos) - diamante verde
                {
                    selector: 'node[type = "Outcome"]',
                    style: {
                        'shape': 'diamond',
                        'width': 45,
                        'height': 45,
                        'background-color': '#2ecc71',
                        'border-color': '#27ae60',
                        'label': 'data(label)',
                        'font-size': '8px',
                        'color': '#ffffff',
                        'text-valign': 'bottom',
                        'text-halign': 'center',
                        'text-margin-y': '8px',
                        'text-wrap': 'wrap',
                        'text-max-width': '120px'
                    }
                },
                // Estilo para nodos AdverseEvent (efectos secundarios) - triángulo rojo
                {
                    selector: 'node[type = "AdverseEvent"]',
                    style: {
                        'shape': 'triangle',
                        'width': 40,
                        'height': 40,
                        'background-color': '#e74c3c',
                        'border-color': '#c0392b',
                        'label': 'data(label)',
                        'font-size': '9px',
                        'color': '#ffffff',
                        'text-valign': 'bottom',
                        'text-halign': 'center',
                        'text-margin-y': '6px'
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
                        'border-color': '#f39c12',
                        'background-color': function(ele) {
                            return NODE_COLORS[ele.data('type')] || '#95a5a6';
                        }
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

        // Evento: click en nodo muestra info en panel flotante
        cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            const data = node.data();
            const detailsPanel = document.getElementById('node-details');
            const detailsContent = document.getElementById('node-details-content');

            if (data.type === 'Paper') {
                const pmid = data.id;
                const title = data.title || 'Título no disponible en vista de grafo';
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
            } else {
                detailsContent.innerHTML = `
                    <h3>${data.type}</h3>
                    <p><strong>ID:</strong> ${data.id}</p>
                `;
                detailsPanel.style.display = 'block';
            }
            
            console.log('Nodo seleccionado:', data);
        });

        // Evento: click en el fondo del grafo oculta el panel
        cy.on('tap', function(evt) {
            if (evt.target === cy) {
                document.getElementById('node-details').style.display = 'none';
            }
        });

        // Botón para cerrar el panel manualmente
        const closeBtn = document.getElementById('close-details');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                document.getElementById('node-details').style.display = 'none';
            });
        }

    } catch (error) {
        statsEl.textContent = `❌ Error: ${error.message}`;
        console.error('Error cargando grafo:', error);
    }
}

// Cargar grafo al iniciar
document.addEventListener('DOMContentLoaded', loadGraph);

// Botón recargar
const reloadBtn = document.getElementById('btn-reload');
if (reloadBtn) {
    reloadBtn.addEventListener('click', loadGraph);
}