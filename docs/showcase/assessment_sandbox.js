/**
 * EduVis Live Editor — Interactive Assessment Sandbox & Telemetry Stream
 */

let activeAssessmentElement = null;
let activeElementYaml = null;
let revealedHintsCount = 0;
let activeSandboxTab = 'sandbox'; // 'sandbox', 'telemetry', 'analytics'
let telemetryEventsList = [];

// Inject additional tab-styling dynamically
(function injectSandboxStyles() {
    if (document.getElementById('sandbox-dynamic-styles')) return;
    const style = document.createElement('style');
    style.id = 'sandbox-dynamic-styles';
    style.textContent = `
        .sandbox-tabs-header {
            display: flex;
            background: var(--bg-card);
            border-bottom: 1.5px solid var(--border);
            margin-bottom: 16px;
            padding: 2px 8px;
            border-radius: 8px 8px 0 0;
        }
        .sandbox-tab-btn {
            background: none !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            border-radius: 0 !important;
            color: var(--text-muted) !important;
            padding: 10px 16px !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            transition: all 0.2s;
        }
        .sandbox-tab-btn:hover {
            color: var(--text-main) !important;
        }
        .sandbox-tab-btn.active {
            color: var(--primary) !important;
            border-bottom-color: var(--primary) !important;
        }
        .step-working-area {
            margin-top: 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .step-working-label {
            font-size: 0.825rem;
            color: var(--accent-yellow);
            font-weight: 600;
        }
        .step-working-textarea {
            width: 100%;
            height: 100px;
            padding: 12px;
            font-family: var(--font-mono);
            background: var(--bg-editor);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-main);
            font-size: 0.875rem;
            outline: none;
            resize: vertical;
            transition: border-color 0.2s;
        }
        .step-working-textarea:focus {
            border-color: var(--primary);
        }
        .step-mark-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(255,255,255,0.02);
            border: 1.5px solid var(--border);
            border-radius: 6px;
            font-size: 0.85rem;
        }
        .step-mark-row.correct {
            border-color: rgba(16, 185, 129, 0.4);
            background: rgba(16, 185, 129, 0.04);
        }
        .step-mark-row.blocked {
            border-color: rgba(245, 158, 11, 0.4);
            background: rgba(245, 158, 11, 0.04);
        }
        .step-mark-badge {
            font-family: var(--font-mono);
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
        }
        .step-mark-badge.m {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
        }
        .step-mark-badge.a {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
        }
        .step-mark-badge.b {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
        }
        .analytics-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .analytics-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1.5px solid rgba(255,255,255,0.03);
            padding-bottom: 10px;
        }
        .analytics-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }
        .analytics-label {
            font-size: 0.875rem;
            color: var(--text-main);
            font-weight: 500;
        }
        .analytics-desc {
            font-size: 0.775rem;
            color: var(--text-muted);
        }
        .mastery-progress-wrapper {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.06);
            border-radius: 999px;
            margin-top: 6px;
            overflow: hidden;
        }
        .mastery-progress-bar {
            height: 100%;
            border-radius: 999px;
            width: 0%;
            transition: width 0.3s ease;
        }
    `;
    document.head.appendChild(style);
})();

if (!window.studentAttemptHistory) {
    window.studentAttemptHistory = {};
}

if (!window.learnerState) {
    window.learnerState = {
        concept_mastery: {
            negative_numbers: { confidence: 0.5, last_seen: 'Never' },
            prime_numbers: { confidence: 0.5, last_seen: 'Never' }
        },
        skill_mastery: {
            subtract_negative_numbers: { confidence: 0.5, last_seen: 'Never' }
        },
        active_misconceptions: {}
    };
}

function resetAssessmentSandboxState() {
    window.studentAttemptHistory = {};
    window.learnerState = {
        concept_mastery: {
            negative_numbers: { confidence: 0.5, last_seen: 'Never' },
            prime_numbers: { confidence: 0.5, last_seen: 'Never' }
        },
        skill_mastery: {
            subtract_negative_numbers: { confidence: 0.5, last_seen: 'Never' }
        },
        active_misconceptions: {}
    };
    telemetryEventsList = [];
    activeAssessmentElement = null;
    activeElementYaml = null;
    revealedHintsCount = 0;
    activeSandboxTab = 'sandbox';
    selectedOptionKey = null;
}

function updateShowcaseLearnerState(element, isCorrect, misconceptionDetected) {
    const timestamp = new Date().toLocaleTimeString();

    // 1. Misconception updates
    if (misconceptionDetected) {
        window.learnerState.active_misconceptions[misconceptionDetected] = {
            active: true,
            detected_at: timestamp
        };
    }

    const resolvedList = Object.values(element.misconceptions || {});
    if (isCorrect) {
        resolvedList.forEach(resolved => {
            if (window.learnerState.active_misconceptions[resolved]) {
                delete window.learnerState.active_misconceptions[resolved];
            }
        });
    }

    // 2. Skill confidence updates
    const skills = element.skills || [];
    skills.forEach(skill => {
        if (!window.learnerState.skill_mastery[skill]) {
            window.learnerState.skill_mastery[skill] = { confidence: 0.5 };
        }
        let current = window.learnerState.skill_mastery[skill].confidence;
        if (isCorrect) {
            current = Math.min(1.0, current + 0.15);
        } else {
            current = Math.max(0.0, current - 0.2);
        }
        window.learnerState.skill_mastery[skill].confidence = parseFloat(current.toFixed(2));
        window.learnerState.skill_mastery[skill].last_seen = timestamp;
    });

    // 3. Concept confidence updates
    const concepts = element.concepts || [];
    concepts.forEach(concept => {
        if (!window.learnerState.concept_mastery[concept]) {
            window.learnerState.concept_mastery[concept] = { confidence: 0.5 };
        }
        let current = window.learnerState.concept_mastery[concept].confidence;
        if (isCorrect) {
            current = Math.min(1.0, current + 0.1);
        } else {
            current = Math.max(0.0, current - 0.1);
        }
        window.learnerState.concept_mastery[concept].confidence = parseFloat(current.toFixed(2));
        window.learnerState.concept_mastery[concept].last_seen = timestamp;
    });
}


function renderAssessmentSandbox(element, elementYaml, curriculumCode, lessonTitle) {
    const area = document.getElementById('assessment-area');
    if (!area) return;

    if (!element || (element.type !== 'multiple_choice' && element.type !== 'short_answer')) {
        renderEmptyAssessmentState(area);
        return;
    }

    activeAssessmentElement = element;
    activeElementYaml = elementYaml;

    const placement = element.placement || {};
    const phase = placement.lesson_phase || 'unknown';
    const difficulty = placement.difficulty || 'starter';
    const evalMode = element.evaluation_mode || '';
    const hasMarking = element.marking_scheme && element.marking_scheme.length > 0;

    // Outer tab switcher shell
    let bodyContentHtml = '';

    if (activeSandboxTab === 'sandbox') {
        // Tab 1: Interactive Sandbox Workspace
        let optionsHtml = '';
        if (element.type === 'multiple_choice') {
            optionsHtml = `
                <div class="options-list" id="mcq-options-container">
                    <!-- Rendered Option Cards -->
                </div>
            `;
        } else {
            if (hasMarking) {
                optionsHtml = `
                    <div class="step-working-area">
                        <div class="step-working-label">Step-by-step working workspace (Method &amp; Accuracy Marks):</div>
                        <textarea class="step-working-textarea" id="short-answer-working-input" placeholder="Type each step of your working on a new line...&#10;e.g.&#10;(3x + 2x) + (5 - 3)&#10;5x + 2"></textarea>
                    </div>
                `;
            } else {
                optionsHtml = `
                    <div class="options-list">
                        <input type="text" id="short-answer-input" placeholder="Type your final answer (mode: ${evalMode})..." style="width: 100%; padding: 14px 18px; font-family: var(--font-sans); background: var(--bg-editor); border: 1px solid var(--border); border-radius: 8px; color: var(--text-main); font-size: 0.95rem; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='var(--primary)'" onblur="this.style.borderColor='var(--border)'" oninput="document.getElementById('mcq-feedback-panel').style.display='none'">
                    </div>
                `;
            }
        }

        let buttonsHtml = `<button class="assessment-btn-submit" onclick="submitAssessmentAnswer()">Submit Answer</button>`;
        if (element.solution_steps && element.solution_steps.length > 0 && !hasMarking) {
            buttonsHtml = `
                <div style="display: flex; gap: 12px; margin-top: 10px; width: 100%;">
                    <button class="assessment-btn-submit" onclick="submitAssessmentAnswer()" style="flex: 2; margin-top: 0;">Submit Answer</button>
                    <button class="assessment-btn-hint" id="assessment-hint-trigger" onclick="showAssessmentHint()" style="flex: 1.2;">Show Hint (1/${element.solution_steps.length})</button>
                </div>
            `;
        } else if (hasMarking) {
            buttonsHtml = `<button class="assessment-btn-submit" onclick="submitAssessmentWorking()">Check Step Working</button>`;
        }

        bodyContentHtml = `
            <div class="assessment-card" style="width: 100%;">
                <div class="assessment-badge-row">
                    <span class="assessment-badge badge-phase">${phase.replace(/_/g, ' ')}</span>
                    <span class="assessment-badge badge-difficulty">${difficulty}</span>
                    ${element.placement?.assessment_objective ? `<span class="assessment-badge" style="background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.25); color: #818cf8;">${element.placement.assessment_objective.replace(/_/g, ' ')}</span>` : ''}
                </div>
                <div class="assessment-question">${escapeHtml(element.question)}</div>
                
                ${optionsHtml}

                ${buttonsHtml}

                <!-- Feedback Alert Panel -->
                <div class="assessment-feedback-panel" id="mcq-feedback-panel">
                    <div class="feedback-title-row" id="feedback-title-container">
                        <!-- Title Injected Here -->
                    </div>
                    <div id="feedback-body-container">
                        <!-- Message Injected Here -->
                    </div>
                    <div class="solution-steps-box" id="feedback-steps-box" style="display: none;">
                        <div class="solution-steps-title">Hints &amp; Solution Steps</div>
                        <div id="feedback-steps-container"></div>
                    </div>
                </div>

                <!-- Step Marks Breakdown container -->
                <div id="step-marks-breakdown-box" style="display: none; margin-top: 16px; flex-direction: column; gap: 8px;">
                    <!-- Row per step rule -->
                </div>
            </div>
        `;
    } else if (activeSandboxTab === 'telemetry') {
        // Tab 2: Live Telemetry Event Stream console
        bodyContentHtml = `
            <div class="telemetry-console" style="width: 100%; height: 400px;">
                <div class="console-header">
                    <div class="console-title-row">
                        <span class="console-badge">JSON</span>
                        <span class="console-title">Live Telemetry Event Stream</span>
                    </div>
                    <button class="console-btn-clear" onclick="clearTelemetryLogs()">Clear</button>
                </div>
                <div class="console-body" id="telemetry-log-body" style="height: 350px; overflow-y: auto;">
                    <!-- Dynamically populated from global list -->
                </div>
            </div>
        `;
    } else {
        // Tab 3: Cognitive Skill Profile (Analytics)
        bodyContentHtml = renderAnalyticsProfileHTML();
    }

    area.innerHTML = `
        <div class="sandbox-tabs-header">
            <button class="sandbox-tab-btn ${activeSandboxTab === 'sandbox' ? 'active' : ''}" onclick="switchSandboxTab('sandbox')">Cognitive Sandbox</button>
            <button class="sandbox-tab-btn ${activeSandboxTab === 'telemetry' ? 'active' : ''}" onclick="switchSandboxTab('telemetry')">Telemetry Event Stream</button>
            <button class="sandbox-tab-btn ${activeSandboxTab === 'analytics' ? 'active' : ''}" onclick="switchSandboxTab('analytics')">Curriculum Skill Profile</button>
        </div>
        <div style="padding: 0 4px;">
            ${bodyContentHtml}
        </div>
    `;

    // Render Option Cards (MCQ only)
    if (activeSandboxTab === 'sandbox' && element.type === 'multiple_choice') {
        const optionsContainer = document.getElementById('mcq-options-container');
        const options = element.options || {};
        Object.keys(options).forEach(key => {
            const optionVal = options[key];
            const card = document.createElement('div');
            card.className = 'option-card';
            card.id = `opt-card-${key}`;
            card.onclick = () => selectMcqOption(key);
            card.innerHTML = `
                <div class="option-circle">
                    <div class="option-circle-inner"></div>
                </div>
                <span class="option-key">${key}</span>
                <span class="option-text">${escapeHtml(optionVal)}</span>
            `;
            optionsContainer.appendChild(card);
        });
    }

    // Populate telemetry logs if viewing telemetry tab
    if (activeSandboxTab === 'telemetry') {
        populateTelemetryLogsHTML();
    }

    // Bind metadata for telemetry
    window.currentTelemetryContext = {
        curriculum_code: curriculumCode || 'showcase',
        lesson_title: lessonTitle || 'Lesson'
    };
}

function switchSandboxTab(tab) {
    activeSandboxTab = tab;
    // Re-render
    const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
    if (activeAssessmentElement && activeElementYaml) {
        renderAssessmentSandbox(activeAssessmentElement, activeElementYaml, window.lessonCurriculumCode, window.lessonMetadataTitle);
    }
}

function renderAnalyticsProfileHTML() {
    const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
    let data = { total_questions: 0, objectives: {} };
    let mapping = {};
    try {
        const dataJson = pyGetLessonAnalytics(contentYaml);
        data = JSON.parse(dataJson);
        const mappingJson = pyGetElementObjectives(contentYaml);
        mapping = JSON.parse(mappingJson);
    } catch (e) {
        console.error("Failed to run analytics", e);
    }

    // Compute earned points per objective type
    const earnedPoints = {
        procedural_fluency: 0,
        conceptual_understanding: 0,
        application: 0,
        reasoning: 0,
        unspecified: 0
    };

    Object.keys(window.studentAttemptHistory).forEach(elId => {
        const obj = mapping[elId] || "unspecified";
        const score = window.studentAttemptHistory[elId] || 0.0;
        if (earnedPoints[obj] !== undefined) {
            earnedPoints[obj] += score;
        }
    });

    const getRowHtml = (label, desc, key, color) => {
        const total = data.objectives[key] || 0;
        const correct = earnedPoints[key] || 0;
        const percent = total > 0 ? Math.round((correct / total) * 100) : 0;
        
        return `
            <div class="analytics-item" style="flex-direction: column; align-items: stretch; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="analytics-label" style="font-weight: 600;">${label}</span>
                        <div class="analytics-desc" style="margin-top: 2px;">${desc}</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 0.8rem; font-family: var(--font-mono); font-weight: 600; color: ${color};">${correct}/${total} Correct (${percent}%)</span>
                    </div>
                </div>
                ${total > 0 ? `
                    <div class="mastery-progress-wrapper">
                        <div class="mastery-progress-bar" style="width: ${percent}%; background-color: ${color};"></div>
                    </div>
                ` : ''}
            </div>
        `;
    };

    // Render dynamic learner state section
    const activeMisconceptionsKeys = Object.keys(window.learnerState.active_misconceptions);
    let misconceptionsHtml = '';
    if (activeMisconceptionsKeys.length === 0) {
        misconceptionsHtml = `<span style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">No active misconceptions detected!</span>`;
    } else {
        misconceptionsHtml = `<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px;">`;
        activeMisconceptionsKeys.forEach(mKey => {
            const m = window.learnerState.active_misconceptions[mKey];
            misconceptionsHtml += `
                <span style="font-size: 0.775rem; background: rgba(239, 68, 68, 0.15); border: 1.5px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 4px 10px; border-radius: 999px; font-family: var(--font-mono); font-weight: 500;">
                    ${mKey} <span style="font-size: 0.7rem; color: var(--text-muted); margin-left: 4px;">(${m.detected_at})</span>
                </span>
            `;
        });
        misconceptionsHtml += `</div>`;
    }

    const getMasteryBarHtml = (label, conf, color) => {
        const percent = Math.round(conf * 100);
        return `
            <div class="analytics-item" style="flex-direction: column; align-items: stretch; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="analytics-label" style="font-weight: 600; font-family: var(--font-mono); font-size: 0.825rem;">${label}</span>
                    <span style="font-size: 0.8rem; font-family: var(--font-mono); font-weight: 600; color: ${color};">${percent}% Confidence</span>
                </div>
                <div class="mastery-progress-wrapper">
                    <div class="mastery-progress-bar" style="width: ${percent}%; background-color: ${color};"></div>
                </div>
            </div>
        `;
    };

    let conceptsMasteryHtml = '';
    Object.keys(window.learnerState.concept_mastery).forEach(cKey => {
        const conf = window.learnerState.concept_mastery[cKey].confidence;
        conceptsMasteryHtml += getMasteryBarHtml(cKey, conf, "#34d399");
    });

    let skillsMasteryHtml = '';
    Object.keys(window.learnerState.skill_mastery).forEach(sKey => {
        const conf = window.learnerState.skill_mastery[sKey].confidence;
        skillsMasteryHtml += getMasteryBarHtml(sKey, conf, "#818cf8");
    });

    return `
        <div style="display: flex; flex-direction: column; gap: 16px;">
            <div class="analytics-card">
                <h3 style="font-size: 1rem; font-weight: 600; color: var(--accent-yellow); margin-bottom: 8px;">Cognitive Breakdown: Curriculum Objectives</h3>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 12px;">Total Assessment Elements in Lesson: <strong>${data.total_questions}</strong></p>
                
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    ${getRowHtml("Procedural Fluency", "Executing practiced algorithms &amp; algebraic steps correctly", "procedural_fluency", "#818cf8")}
                    ${getRowHtml("Conceptual Understanding", "Grasping underlying patterns and mathematical models", "conceptual_understanding", "#34d399")}
                    ${getRowHtml("Application", "Applying methods to unfamiliar contexts or real scenarios", "application", "#fbbf24")}
                    ${getRowHtml("Reasoning", "Justifying, proving, or generalizing algebraic relationships", "reasoning", "#f87171")}
                    ${getRowHtml("Unspecified / Other", "Questions without an explicit objective tag", "unspecified", "#9ca3af")}
                </div>
            </div>

            <div class="analytics-card" style="border-color: rgba(99, 102, 241, 0.35); background: rgba(99, 102, 241, 0.02);">
                <h3 style="font-size: 1.05rem; font-weight: 600; color: #818cf8; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                    Mastery Graph Projection (Dynamic Learner State)
                </h3>
                <p style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 16px;">
                    This real-time view overlays the student's telemetry evidence onto the static Curriculum Graph to compute concept, skill, and active misconception states.
                </p>

                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div>
                        <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 6px;">Concepts Mastery:</div>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            ${conceptsMasteryHtml}
                        </div>
                    </div>

                    <div style="margin-top: 6px;">
                        <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 6px;">Skills Mastery:</div>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            ${skillsMasteryHtml}
                        </div>
                    </div>

                    <div style="margin-top: 6px; border-top: 1px solid var(--border); padding-top: 12px;">
                        <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 6px; color: #f87171;">Active Misconceptions:</div>
                        ${misconceptionsHtml}
                    </div>
                </div>
            </div>
        </div>
    `;
}


function submitAssessmentWorking() {
    const workingInput = document.getElementById('short-answer-working-input');
    if (!workingInput || !workingInput.value.trim()) {
        alert("Please enter step-by-step working first!");
        return;
    }

    const lines = workingInput.value.split('\n').map(l => l.trim()).filter(l => l);
    try {
        const resultJson = pyEvaluateStudentSteps(activeElementYaml, lines);
        const result = JSON.parse(resultJson);

        if (result.error) {
            alert("Error matching working: " + result.error);
            return;
        }

        // Show breakdown box
        const breakdownBox = document.getElementById('step-marks-breakdown-box');
        breakdownBox.innerHTML = '';
        breakdownBox.style.display = 'flex';

        let awardedScore = result.total_score;
        let maxScore = result.max_score;

        result.steps.forEach(step => {
            const row = document.createElement('div');
            let statusClass = '';
            let statusText = 'Incorrect / Not Found';
            let markText = `0/${step.weight}`;
            
            if (step.correct) {
                statusClass = 'correct';
                statusText = 'Correct step matching!';
                markText = `${step.weight}/${step.weight}`;
            } else if (step.blocked) {
                statusClass = 'blocked';
                statusText = 'Blocked by Method prerequisite (M0 -> A0)';
                markText = `0/${step.weight}`;
            }

            row.className = `step-mark-row ${statusClass}`;
            row.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="font-weight: 600;">${step.description}</div>
                    <div style="font-size: 0.775rem; color: var(--text-muted);">${statusText}</div>
                    ${step.matched_line ? `<div style="font-size: 0.775rem; font-family: var(--font-mono); color: var(--accent-yellow);">Matched: "${step.matched_line}"</div>` : ''}
                </div>
                <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                    <span class="step-mark-badge ${step.mark_type.toLowerCase()}">${step.mark_type}${step.weight}</span>
                    <strong style="font-family: var(--font-mono); color: var(--text-main);">${markText} Marks</strong>
                </div>
            `;
            breakdownBox.appendChild(row);
        });

        // Display summary feedback
        const panel = document.getElementById('mcq-feedback-panel');
        const titleContainer = document.getElementById('feedback-title-container');
        const bodyContainer = document.getElementById('feedback-body-container');

        panel.classList.remove('correct', 'incorrect');
        panel.style.display = 'flex';

        if (awardedScore === maxScore) {
            panel.classList.add('correct');
            titleContainer.innerHTML = `
                <svg class="feedback-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-green);">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Full Marks Awarded!</span>
            `;
            bodyContainer.innerHTML = `Excellent step-by-step working. Awarded <strong>${awardedScore}/${maxScore} marks</strong> under Method/Accuracy dependency rules.`;
        } else {
            panel.classList.add('incorrect');
            titleContainer.innerHTML = `
                <svg class="feedback-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-yellow);">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>Partial Marks Awarded</span>
            `;
            bodyContainer.innerHTML = `Your working scored <strong>${awardedScore}/${maxScore} marks</strong>. Review the matching steps below and check for dependencies (M marks must be correct before A marks are earned).`;
        }

        // Record score for analytics mastery calculations (awarded / max score ratio)
        window.studentAttemptHistory[activeAssessmentElement.id] = maxScore > 0 ? (awardedScore / maxScore) : 0.0;

        // Update dynamic learner state
        updateShowcaseLearnerState(activeAssessmentElement, awardedScore === maxScore, null);

        // Stream Telemetry
        logTelemetryEvent("step_attempt_submitted", {
            student_working: lines,
            marks_awarded: awardedScore,
            max_marks: maxScore,
            steps_breakdown: result.steps
        });

    } catch (e) {
        console.error("Working evaluation failed", e);
    }
}

function renderEmptyAssessmentState(container) {
    const slides = window.currentSlides || [];
    const assessmentSlides = slides.filter(s => s.type === 'multiple_choice' || s.type === 'short_answer');

    let helpText = '';
    const presetSelect = document.getElementById('preset-select');
    const presetName = presetSelect && presetSelect.selectedIndex >= 0 
        ? presetSelect.options[presetSelect.selectedIndex].text 
        : '';

    if (assessmentSlides.length > 0) {
        let formattedSlides = '';
        if (assessmentSlides.length === 1) {
            formattedSlides = `<strong>Slide ${assessmentSlides[0].index + 1}</strong>`;
        } else {
            const last = assessmentSlides[assessmentSlides.length - 1];
            const others = assessmentSlides.slice(0, -1).map(s => `<strong>Slide ${s.index + 1}</strong>`).join(', ');
            formattedSlides = `${others} or <strong>Slide ${last.index + 1}</strong>`;
        }
        const presetPart = presetName ? ` in the <em>${escapeHtml(presetName)}</em> preset` : '';
        helpText = `Try selecting ${formattedSlides}${presetPart} to test the engine!`;
    } else {
        const presetPart = presetName ? ` the <em>${escapeHtml(presetName)}</em> preset` : 'this preset';
        helpText = `No interactive assessment elements (multiple_choice or short_answer) found in ${presetPart}.<br><br>Try selecting the <strong>Adaptive Remediation & Assessment</strong> or <strong>Exhaustive Element Catalog</strong> presets to test the engine!`;
    }

    container.innerHTML = `
        <div class="assessment-empty-state">
            <svg class="assessment-empty-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path>
                <path d="m9 12 2 2 4-4"></path>
            </svg>
            <div class="assessment-empty-title">Select an Assessment Slide</div>
            <div class="assessment-empty-text">
                The Interactive Assessment Sandbox applies to <strong>multiple_choice</strong> and <strong>short_answer</strong> elements.<br><br>
                ${helpText}
            </div>
        </div>
    `;
}

let selectedOptionKey = null;

function selectMcqOption(optionKey) {
    selectedOptionKey = optionKey;
    const cards = document.querySelectorAll('.option-card');
    cards.forEach(card => card.classList.remove('selected'));

    const selectedCard = document.getElementById(`opt-card-${optionKey}`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    const panel = document.getElementById('mcq-feedback-panel');
    panel.style.display = 'none';
}

function submitAssessmentAnswer() {
    let studentAnswer = "";
    if (activeAssessmentElement.type === 'multiple_choice') {
        if (!selectedOptionKey) {
            alert('Please select an option first!');
            return;
        }
        studentAnswer = selectedOptionKey;
    } else {
        const inputEl = document.getElementById('short-answer-input');
        if (!inputEl || !inputEl.value.trim()) {
            alert('Please type an answer first!');
            return;
        }
        studentAnswer = inputEl.value.trim();
    }

    if (!activeAssessmentElement || !activeElementYaml) return;

    try {
        const resultJson = pyCheckStudentAnswer(activeElementYaml, studentAnswer);
        const result = JSON.parse(resultJson);

        if (result.error) {
            console.error(result.error);
            alert("Error running answer check: " + result.error);
            return;
        }

        displayAssessmentFeedback(result);

        // Record correctness for analytics mastery calculations
        window.studentAttemptHistory[activeAssessmentElement.id] = result.is_correct ? 1.0 : 0.0;

        // Update dynamic learner state
        updateShowcaseLearnerState(activeAssessmentElement, result.is_correct, result.misconception_detected);

        logTelemetryEvent("attempt_submitted", {
            student_answer: studentAnswer,
            is_correct: result.is_correct,
            misconception_detected: result.misconception_detected || null
        });

    } catch (err) {
        console.error("Checking failed: ", err);
    }
}

function showAssessmentHint() {
    if (!activeAssessmentElement || !activeAssessmentElement.solution_steps) return;
    const steps = activeAssessmentElement.solution_steps;
    const stepsBox = document.getElementById('feedback-steps-box');
    const stepsContainer = document.getElementById('feedback-steps-container');
    const hintBtn = document.getElementById('assessment-hint-trigger');
    const feedbackPanel = document.getElementById('mcq-feedback-panel');

    if (revealedHintsCount >= steps.length) return;

    stepsBox.style.display = 'block';
    feedbackPanel.style.display = 'flex';
    feedbackPanel.classList.add('correct');

    const stepText = steps[revealedHintsCount];
    const stepEl = document.createElement('div');
    stepEl.className = 'solution-step';
    stepEl.innerText = stepText;
    stepEl.style.animationDelay = '0s';
    stepsContainer.appendChild(stepEl);

    const currentHintIdx = revealedHintsCount;
    revealedHintsCount++;

    if (revealedHintsCount === steps.length) {
        hintBtn.innerText = "All Hints Shown";
        hintBtn.disabled = true;
    } else {
        hintBtn.innerText = `Show Hint (${revealedHintsCount + 1}/${steps.length})`;
    }

    logTelemetryEvent("hint_requested", {
        hint_index: currentHintIdx,
        total_hints: steps.length,
        hint_text: stepText
    });
}

function displayAssessmentFeedback(result) {
    const panel = document.getElementById('mcq-feedback-panel');
    const titleContainer = document.getElementById('feedback-title-container');
    const bodyContainer = document.getElementById('feedback-body-container');

    panel.classList.remove('correct', 'incorrect');

    if (result.is_correct) {
        panel.classList.add('correct');
        panel.style.display = 'flex';

        titleContainer.innerHTML = `
            <svg class="feedback-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-green);">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Correct Answer!</span>
        `;
        bodyContainer.innerHTML = "Great job! Your answer matches the expected value.";
    } else {
        panel.classList.add('incorrect');
        panel.style.display = 'flex';

        titleContainer.innerHTML = `
            <svg class="feedback-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-red);">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
            <span>Incorrect Answer</span>
        `;

        let msg = "That is not correct. Try again!";
        if (result.misconception_detected) {
            msg = `<strong>Misconception Detected:</strong> <code style="background: rgba(239, 68, 68, 0.15); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); color: #f87171;">${result.misconception_detected}</code><br><br>`;
            const optionsFeedback = activeAssessmentElement.options || {};
            const val = optionsFeedback[selectedOptionKey];
            if (val && typeof val === 'string' && val.toLowerCase().startsWith('incorrect')) {
                msg += val;
            } else {
                msg += "Review the rules on real numbers and try to trace your steps.";
            }
        }
        bodyContainer.innerHTML = msg;
    }
}

function logTelemetryEvent(eventType, eventData) {
    const eventObj = {
        event_id: "evt_" + Math.random().toString(36).substring(2, 11),
        event_type: eventType,
        timestamp: new Date().toISOString(),
        context: {
            curriculum_code: window.currentTelemetryContext.curriculum_code,
            lesson_title: window.currentTelemetryContext.lesson_title,
            element_id: activeAssessmentElement.id,
            element_type: activeAssessmentElement.type
        },
        data: eventData
    };

    telemetryEventsList.push(eventObj);

    // If viewing telemetry tab right now, update output
    if (activeSandboxTab === 'telemetry') {
        populateTelemetryLogsHTML();
    }
}

function populateTelemetryLogsHTML() {
    const consoleBody = document.getElementById('telemetry-log-body');
    if (!consoleBody) return;

    if (telemetryEventsList.length === 0) {
        consoleBody.innerHTML = `<div style="color: var(--text-muted); font-style: italic; font-size: 0.75rem;">Waiting for student interactions...</div>`;
        return;
    }

    consoleBody.innerHTML = '';
    telemetryEventsList.forEach(eventObj => {
        const logDiv = document.createElement('div');
        logDiv.className = 'telemetry-log-item';
        logDiv.innerHTML = `
            <div class="log-meta">
                <span class="log-event-type">${eventObj.event_type}</span>
                <span>${new Date(eventObj.timestamp).toLocaleTimeString()}</span>
            </div>
            <pre class="log-json">${escapeHtml(JSON.stringify(eventObj, null, 2))}</pre>
        `;
        consoleBody.appendChild(logDiv);
    });
    consoleBody.scrollTop = consoleBody.scrollHeight;
}

function clearTelemetryLogs() {
    telemetryEventsList = [];
    populateTelemetryLogsHTML();
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
