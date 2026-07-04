// Global State for Curriculum Workspace Projections
window.curriculumActiveSubTab = 'map';
window.simulatedMastery = {};
window.lastCurriculumData = null;
window.cyMapInstance = null;
window.cyLearnerInstance = null;

function switchCurriculumSubTab(subTabName) {
    window.curriculumActiveSubTab = subTabName;

    // Update tab button CSS classes
    document.getElementById('sub-tab-map').classList.remove('active');
    document.getElementById('sub-tab-coverage').classList.remove('active');
    document.getElementById('sub-tab-learner').classList.remove('active');

    document.getElementById('sub-tab-' + subTabName).classList.add('active');

    // Toggle panel visibility
    document.getElementById('curriculum-map-section').style.display = 'none';
    document.getElementById('curriculum-coverage-section').style.display = 'none';
    document.getElementById('curriculum-learner-section').style.display = 'none';

    if (subTabName === 'map') {
        document.getElementById('curriculum-map-section').style.display = 'flex';
        renderCurriculumMapTab();
    } else if (subTabName === 'coverage') {
        document.getElementById('curriculum-coverage-section').style.display = 'flex';
        renderCurriculumCoverageTab();
    } else if (subTabName === 'learner') {
        document.getElementById('curriculum-learner-section').style.display = 'flex';
        renderCurriculumLearnerTab();
    }
}

async function renderCurriculumDashboard() {
    const container = document.getElementById('curriculum-area');
    if (!window.pyodideInstance) {
        container.innerHTML = `<div style="text-align: center; margin: 40px auto; color: #a1a1aa;">Python WebAssembly environment is loading... Please wait.</div>`;
        return;
    }

    const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
    const curriculumYaml = window.curriculumModel ? window.curriculumModel.getValue() : '';

    try {
        const jsonStr = pyGetCurriculumDashboard(contentYaml, curriculumYaml);
        const data = JSON.parse(jsonStr);

        if (data.error) {
            container.innerHTML = `<div style="color: #ef4444; padding: 20px; border: 1px solid #ef4444; border-radius: 8px; background: rgba(239, 68, 68, 0.1);">Error loading curriculum data: ${data.error}</div>`;
            return;
        }

        window.lastCurriculumData = data;

        // Initialize simulated mastery if not populated or if concepts list changed
        if (!window.simulatedMastery || Object.keys(window.simulatedMastery).length !== data.concepts.length) {
            window.simulatedMastery = {};
            data.concepts.forEach(c => {
                const isCovered = data.coverage.covered_concepts.includes(c.code);
                // Pre-populate covered ones with 0.8 (mastered), others with 0.0
                window.simulatedMastery[c.code] = isCovered ? 0.8 : 0.0;
            });
        }

        // Trigger sub-tab view updates
        switchCurriculumSubTab(window.curriculumActiveSubTab);

    } catch (err) {
        container.innerHTML = `<div style="color: #ef4444; padding: 20px; border: 1px solid #ef4444; border-radius: 8px; background: rgba(239, 68, 68, 0.1);">WASM Execution Error: ${err.message}</div>`;
    }
}

function renderCurriculumMapTab() {
    const data = window.lastCurriculumData;
    if (!data) return;

    resetInspectorPlaceholder();

    const canvas = document.getElementById('curriculum-graph-canvas');
    if (!canvas) return;

    if (!window.cytoscape) {
        canvas.innerHTML = `<div style="padding: 20px; color: #94a3b8; text-align: center; font-size: 0.9rem;">Cytoscape.js library not loaded. Check internet connection.</div>`;
        return;
    }

    setTimeout(() => {
        const elements = [];

        // Add nodes
        data.concepts.forEach(c => {
            const isCovered = data.coverage.covered_concepts.includes(c.code);
            const hasGap = data.gaps.some(g => g.concept === c.code);

            let statusClass = 'uncovered';
            if (hasGap) {
                statusClass = 'gap';
            } else if (isCovered) {
                statusClass = 'covered';
            }

            elements.push({
                data: {
                    id: c.code,
                    label: `${c.name}\n(Weight: ${Math.round(c.exam_weight * 100)}%)`
                },
                classes: statusClass
            });
        });

        // Add edges
        data.dependencies.forEach(d => {
            elements.push({
                data: { id: `${d.from}-${d.to}`, source: d.from, target: d.to }
            });
        });

        // Initialize Cytoscape Map
        window.cyMapInstance = window.cytoscape({
            container: canvas,
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'color': '#f8fafc',
                        'font-family': 'Outfit, sans-serif',
                        'font-size': '10px',
                        'font-weight': '600',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'text-wrap': 'wrap',
                        'text-max-width': '95px',
                        'width': '120px',
                        'height': '64px',
                        'shape': 'round-rectangle',
                        'background-color': '#1e293b',
                        'border-width': '1.5px',
                        'border-color': '#475569',
                        'transition-property': 'background-color, border-color, line-color, target-arrow-color',
                        'transition-duration': '0.15s'
                    }
                },
                {
                    selector: 'node.uncovered',
                    style: {
                        'background-color': '#334155',
                        'border-color': '#475569',
                        'color': '#94a3b8'
                    }
                },
                {
                    selector: 'node.covered',
                    style: {
                        'background-color': '#10b981',
                        'border-color': '#059669',
                        'color': '#ffffff'
                    }
                },
                {
                    selector: 'node.gap',
                    style: {
                        'background-color': '#ef4444',
                        'border-color': '#dc2626',
                        'color': '#ffffff'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#475569',
                        'target-arrow-color': '#475569',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.15
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': '3px',
                        'border-color': '#f59e0b'
                    }
                }
            ],
            layout: {
                name: 'breadthfirst',
                directed: true,
                spacingFactor: 1.15,
                animate: false
            }
        });

        // Node selection click handler
        window.cyMapInstance.on('tap', 'node', function (evt) {
            const node = evt.target;
            const conceptCode = node.id();

            // Highlight edges
            window.cyMapInstance.edges().style({
                'line-color': '#1e293b',
                'target-arrow-color': '#1e293b'
            });

            node.connectedEdges().style({
                'line-color': '#f59e0b',
                'target-arrow-color': '#f59e0b'
            });

            updateInspectorDetails(conceptCode);
        });

        // Deselect background click handler
        window.cyMapInstance.on('tap', function (evt) {
            if (evt.target === window.cyMapInstance) {
                window.cyMapInstance.edges().style({
                    'line-color': '#475569',
                    'target-arrow-color': '#475569'
                });
                resetInspectorPlaceholder();
            }
        });
    }, 50);
}

function resetInspectorPlaceholder() {
    const inspector = document.getElementById('graph-node-inspector');
    if (!inspector) return;
    inspector.innerHTML = `
        <div class="inspector-placeholder">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <div>Click on a concept node in the dependency graph to inspect its prerequisites, successors, associated skills, and misconceptions.</div>
        </div>
    `;
}

function updateInspectorDetails(conceptCode) {
    const data = window.lastCurriculumData;
    if (!data) return;

    const concept = data.concepts.find(c => c.code === conceptCode);
    if (!concept) return;

    const prereqs = data.dependencies.filter(d => d.to === conceptCode);
    const successors = data.dependencies.filter(d => d.from === conceptCode);
    const skills = data.skills.filter(s => s.concept === conceptCode);
    const misconceptions = data.misconceptions.filter(m => m.concept === conceptCode);

    const inspector = document.getElementById('graph-node-inspector');
    if (!inspector) return;

    let html = `
        <div class="inspector-header">
            <div class="inspector-title">${concept.name}</div>
            <div class="inspector-subtitle">Code: ${concept.code}</div>
            <div style="font-size: 0.8rem; margin-top: 4px; color: #94a3b8;">Exam Weight: ${Math.round(concept.exam_weight * 100)}%</div>
        </div>

        <div class="inspector-section">
            <div class="inspector-section-title">Prerequisites</div>
            <div class="inspector-badge-list">
    `;

    if (prereqs.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.8rem;">None</span>`;
    } else {
        prereqs.forEach(p => {
            const pName = data.concepts.find(c => c.code === p.from)?.name || p.from;
            html += `<span class="inspector-badge prereq">${pName}</span>`;
        });
    }

    html += `
            </div>
        </div>

        <div class="inspector-section">
            <div class="inspector-section-title">Successors</div>
            <div class="inspector-badge-list">
    `;

    if (successors.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.8rem;">None</span>`;
    } else {
        successors.forEach(s => {
            const sName = data.concepts.find(c => c.code === s.to)?.name || s.to;
            html += `<span class="inspector-badge successor">${sName}</span>`;
        });
    }

    html += `
            </div>
        </div>

        <div class="inspector-section">
            <div class="inspector-section-title">Skills Taught</div>
            <div class="inspector-badge-list">
    `;

    if (skills.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.8rem;">None</span>`;
    } else {
        skills.forEach(s => {
            html += `<span class="inspector-badge skill" title="${s.code}">${s.name}</span>`;
        });
    }

    html += `
            </div>
        </div>

        <div class="inspector-section">
            <div class="inspector-section-title">Misconceptions Checked</div>
            <div class="inspector-badge-list">
    `;

    if (misconceptions.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.8rem;">None</span>`;
    } else {
        misconceptions.forEach(m => {
            html += `<span class="inspector-badge misconception" title="Remediation Weight: ${m.remediation_weight || 1.0}">${m.name}</span>`;
        });
    }

    html += `
            </div>
        </div>
    `;

    inspector.innerHTML = html;
}

function renderCurriculumCoverageTab() {
    const data = window.lastCurriculumData;
    if (!data) return;

    const cov = data.coverage;
    const gaps = data.gaps;
    const centrality = data.centrality;

    const container = document.getElementById('curriculum-coverage-section');
    if (!container) return;

    let html = `
        <div style="display: flex; flex-direction: column; gap: 24px;">
    `;

    // Dependency Gaps Alert Box
    if (gaps.length > 0) {
        html += `
            <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; color: #fca5a5; font-weight: 600; font-size: 1rem;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    Prerequisite Dependency Gaps Detected!
                </div>
                <ul style="margin: 0; padding-left: 20px; color: #f8fafc; font-size: 0.9rem; line-height: 1.55;">
        `;
        gaps.forEach(g => {
            const conceptName = data.concepts.find(c => c.code === g.concept)?.name || g.concept;
            const missingName = data.concepts.find(c => c.code === g.missing_prerequisite)?.name || g.missing_prerequisite;
            html += `<li>Lesson introduces <b>${conceptName}</b> but misses prerequisite <b>${missingName}</b>.</li>`;
        });
        html += `
                </ul>
            </div>
        `;
    } else {
        html += `
            <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 8px; color: #a7f3d0; font-weight: 600; font-size: 1rem;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                All concept prerequisites are fully satisfied.
            </div>
        `;
    }

    // Grid layout for Centrality and badges
    html += `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <!-- Centrality Column -->
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px;">
                <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 1.1rem; color: #cbd5e1; font-weight: 500;">Centrality &amp; Graph Bottlenecks</h3>
                <div style="display: flex; flex-direction: column; gap: 14px;">
    `;

    centrality.forEach(c => {
        const pct = Math.round(c.centrality_weight * 100);
        const isBottleneck = c.downstream_count > 1;
        html += `
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 0.9rem;">
                    <span style="color: #f1f5f9; font-weight: 500;">${c.name}</span>
                    <span style="color: #94a3b8; font-size: 0.8rem;">
                        ${isBottleneck ? '<span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 8px; font-size: 0.75rem;">BOTTLENECK</span>' : ''}
                        Centrality: ${pct}%
                    </span>
                </div>
                <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                    <div style="width: ${pct}%; height: 100%; background: ${isBottleneck ? '#f59e0b' : '#3b82f6'}; border-radius: 3px;"></div>
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">
                    Prerequisite for ${c.downstream_count} downstream concept${c.downstream_count === 1 ? '' : 's'}.
                </div>
            </div>
        `;
    });

    html += `
                </div>
            </div>

            <!-- Coverage Column -->
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px;">
                <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 1.1rem; color: #cbd5e1; font-weight: 500;">Lesson Scope Coverage</h3>

                <div style="margin-bottom: 20px;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.05em;">Covered Skills</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    `;

    if (cov.covered_skills.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.85rem;">None</span>`;
    } else {
        cov.covered_skills.forEach(s => {
            const sName = data.skills.find(sk => sk.code === s)?.name || s;
            html += `<span style="font-size: 0.8rem; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25); padding: 4px 10px; border-radius: 12px;">${sName}</span>`;
        });
    }

    html += `
                    </div>
                </div>

                <div>
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.05em;">Covered Misconceptions</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    `;

    if (cov.covered_misconceptions.length === 0) {
        html += `<span style="color: #64748b; font-size: 0.85rem;">None</span>`;
    } else {
        cov.covered_misconceptions.forEach(m => {
            const mName = data.misconceptions.find(mc => mc.code === m)?.name || m;
            html += `<span style="font-size: 0.8rem; background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); padding: 4px 10px; border-radius: 12px;">${mName}</span>`;
        });
    }

    html += `
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;

    container.innerHTML = html;
}

function calculateConceptStatus(conceptCode, data) {
    const mastery = window.simulatedMastery[conceptCode] || 0.0;
    if (mastery >= 0.8) {
        return 'mastered';
    }

    const prereqs = data.dependencies.filter(d => d.to === conceptCode);
    if (prereqs.length === 0) {
        return 'ready';
    }

    const allPrereqsMastered = prereqs.every(p => {
        const pMastery = window.simulatedMastery[p.from] || 0.0;
        return pMastery >= 0.8;
    });

    return allPrereqsMastered ? 'ready' : 'gap';
}

function updateLearnerGraphHeatmap(data) {
    if (!window.cyLearnerInstance) return;

    data.concepts.forEach(c => {
        const status = calculateConceptStatus(c.code, data);
        const node = window.cyLearnerInstance.getElementById(c.code);
        if (node) {
            node.removeClass('mastered ready gap');
            node.addClass(status);
        }
    });
}

function renderCurriculumLearnerTab() {
    const data = window.lastCurriculumData;
    if (!data) return;

    const canvas = document.getElementById('learner-graph-canvas');
    const controls = document.getElementById('learner-mastery-controls');
    if (!canvas || !controls) return;

    if (!window.cytoscape) {
        canvas.innerHTML = `<div style="padding: 20px; color: #94a3b8; text-align: center; font-size: 0.9rem;">Cytoscape.js library not loaded. Check internet connection.</div>`;
        return;
    }

    setTimeout(() => {
        const elements = [];

        // Create Cytoscape elements with dynamic learner state classes
        data.concepts.forEach(c => {
            const status = calculateConceptStatus(c.code, data);
            elements.push({
                data: {
                    id: c.code,
                    label: `${c.name}\n(Mastery: ${Math.round((window.simulatedMastery[c.code] || 0) * 100)}%)`
                },
                classes: status
            });
        });

        // Add edges
        data.dependencies.forEach(d => {
            elements.push({
                data: { id: `${d.from}-${d.to}`, source: d.from, target: d.to }
            });
        });

        // Instantiate Cytoscape Learner Graph
        window.cyLearnerInstance = window.cytoscape({
            container: canvas,
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'color': '#f8fafc',
                        'font-family': 'Outfit, sans-serif',
                        'font-size': '10px',
                        'font-weight': '600',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'text-wrap': 'wrap',
                        'text-max-width': '95px',
                        'width': '120px',
                        'height': '64px',
                        'shape': 'round-rectangle',
                        'background-color': '#1e293b',
                        'border-width': '1.5px',
                        'border-color': '#475569',
                        'transition-property': 'background-color, border-color',
                        'transition-duration': '0.2s'
                    }
                },
                {
                    selector: 'node.gap',
                    style: {
                        'background-color': '#ef4444',
                        'border-color': '#dc2626',
                        'color': '#ffffff'
                    }
                },
                {
                    selector: 'node.ready',
                    style: {
                        'background-color': '#3b82f6',
                        'border-color': '#1d4ed8',
                        'color': '#ffffff'
                    }
                },
                {
                    selector: 'node.mastered',
                    style: {
                        'background-color': '#10b981',
                        'border-color': '#059669',
                        'color': '#ffffff'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#475569',
                        'target-arrow-color': '#475569',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.15
                    }
                }
            ],
            layout: {
                name: 'breadthfirst',
                directed: true,
                spacingFactor: 1.15,
                animate: false
            }
        });
    }, 50);

    // Build the Simulated Learner State control panel
    let ctrlHtml = `
        <div class="inspector-header">
            <div class="inspector-title">Simulated Learner State</div>
            <div class="inspector-subtitle">Adjust sliders to simulate learner mastery (Green = Mastered (≥80%), Blue = Ready, Red = Prereq Gap)</div>
        </div>
        <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px;">
    `;

    data.concepts.forEach(c => {
        const score = Math.round((window.simulatedMastery[c.code] || 0) * 100);
        ctrlHtml += `
            <div class="mastery-control-row">
                <div class="mastery-control-label" title="${c.code}">${c.name}</div>
                <div class="mastery-slider-container">
                    <input type="range" min="0" max="100" value="${score}" 
                        style="width: 80px; accent-color: var(--primary);" 
                        oninput="onMasterySliderChange('${c.code}', this.value)">
                    <span id="mastery-val-${c.code}" class="mastery-slider-value">${score}%</span>
                </div>
            </div>
        `;
    });

    ctrlHtml += `
        </div>
        <button class="btn-primary" style="margin-top: 14px; padding: 8px; font-size: 0.85rem;" onclick="resetSimulatedMastery()">Reset Mastery</button>
    `;

    controls.innerHTML = ctrlHtml;
}

window.onMasterySliderChange = function(conceptCode, value) {
    const masteryFloat = parseFloat(value) / 100.0;
    window.simulatedMastery[conceptCode] = masteryFloat;
    
    // Update numeric indicator text
    const textEl = document.getElementById(`mastery-val-${conceptCode}`);
    if (textEl) textEl.innerText = `${value}%`;

    const data = window.lastCurriculumData;
    if (!data) return;

    // Update node label inside cytoscape
    const node = window.cyLearnerInstance.getElementById(conceptCode);
    if (node) {
        const concept = data.concepts.find(c => c.code === conceptCode);
        node.data('label', `${concept.name}\n(Mastery: ${value}%)`);
    }

    // Propagate heatmap state updates
    updateLearnerGraphHeatmap(data);
};

window.resetSimulatedMastery = function() {
    const data = window.lastCurriculumData;
    if (!data) return;

    window.simulatedMastery = {};
    data.concepts.forEach(c => {
        const isCovered = data.coverage.covered_concepts.includes(c.code);
        window.simulatedMastery[c.code] = isCovered ? 0.8 : 0.0;
    });

    // Re-render
    renderCurriculumLearnerTab();
};
