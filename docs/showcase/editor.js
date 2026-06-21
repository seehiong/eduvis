/**
 * EduVis Live Editor — Main UI Controller & Script Coordinator
 */

let selectedSlideIndex = 0;
window.currentSlides = [];
let renderMode = "lesson"; // "lesson" or "slide"
let isRenderInProgress = false;

// Monaco Editor instances
window.editor = null;
window.contentModel = null;
window.presentationModel = null;
window.curriculumModel = null;
let activeEditorTab = 'content';

let presentationData = null;
let activeStepIndex = 0;
let isPlaying = false;
let autoAdvanceTimeout = null;
let hasValidationErrorsOrWarnings = false;
let validationMessages = [];

window.lessonCurriculumCode = 'showcase';
window.lessonMetadataTitle = 'Lesson';

// Switch Monaco tabs (Content vs Presentation vs Curriculum)
function switchEditorTab(tabName) {
    if (activeEditorTab === tabName) return;
    activeEditorTab = tabName;

    document.getElementById('tab-editor-content').classList.remove('active');
    document.getElementById('tab-editor-presentation').classList.remove('active');
    document.getElementById('tab-editor-curriculum').classList.remove('active');

    if (tabName === 'content') {
        document.getElementById('tab-editor-content').classList.add('active');
        window.editor.setModel(window.contentModel);
    } else if (tabName === 'presentation') {
        document.getElementById('tab-editor-presentation').classList.add('active');
        window.editor.setModel(window.presentationModel);
    } else if (tabName === 'curriculum') {
        document.getElementById('tab-editor-curriculum').classList.add('active');
        window.editor.setModel(window.curriculumModel);
    }
}

// Bootstrap Python environment first to avoid race conditions with Monaco's AMD loader
initPythonEnvironment(
    (text, subtext) => {
        document.getElementById('loading-text').innerText = text;
        document.getElementById('loading-subtext').innerText = subtext;
    },
    () => {
        // Hide loading overlay
        document.getElementById('loading-overlay').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('loading-overlay').style.display = 'none';
        }, 500);

        // Initialize Monaco Editor after Pyodide is fully ready and AMD loader is restored
        initializeMonacoAndLoadDefault();
    }
);

function initializeMonacoAndLoadDefault() {
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.48.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
        window.contentModel = monaco.editor.createModel('# Loading content...', 'yaml');
        window.presentationModel = monaco.editor.createModel('# Loading presentation...', 'yaml');
        window.curriculumModel = monaco.editor.createModel('# Loading curriculum...', 'yaml');

        window.editor = monaco.editor.create(document.getElementById('editor-container'), {
            model: window.contentModel,
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 13,
            fontFamily: 'var(--font-mono)',
            minimap: { enabled: false },
            lineNumbers: "on",
            scrollbar: {
                vertical: 'visible',
                horizontal: 'visible'
            }
        });

        // Auto-compile when Monaco model contents change (debounced)
        let timeout = null;
        const onModelChange = () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                parseStructureAndRender();
            }, 800);
        };

        window.contentModel.onDidChangeContent(onModelChange);
        window.presentationModel.onDidChangeContent(onModelChange);
        window.curriculumModel.onDidChangeContent(onModelChange);

        // Load default preset
        onPresetChange("lessons/negative-numbers-confidence-ladder-lesson.yaml");
    });
}

// Load preset templates
// Visually disable or enable tabs depending on whether we are in Standalone Curriculum mode
function updateTabVisibilities() {
    const isCustom = (document.getElementById('preset-select').value === 'custom');
    
    // Left Editor Tabs
    const tabContent = document.getElementById('tab-editor-content');
    const tabPresentation = document.getElementById('tab-editor-presentation');
    const tabCurriculum = document.getElementById('tab-editor-curriculum');
    
    // Right Preview Tabs
    const tabVisual = document.getElementById('tab-visual');
    const tabXml = document.getElementById('tab-xml');
    const tabAssessment = document.getElementById('tab-assessment');
    const tabAnalytics = document.getElementById('tab-curriculum');
    
    // Default: all enabled
    let enableContent = true;
    let enablePresentation = true;
    let enableCurriculum = false; // By default, lessons don't show curriculum tab on the left
    
    let enableVisual = true;
    let enableXml = true;
    let enableAssessment = true;
    let enableAnalytics = false; // By default, lessons don't show curriculum analytics on the right
    
    if (isCustom) {
        // Custom sandbox: everything enabled
        enableContent = true;
        enablePresentation = true;
        enableCurriculum = true;
        
        enableVisual = true;
        enableXml = true;
        enableAssessment = true;
        enableAnalytics = true;
    } else if (renderMode === "curriculum") {
        // Standalone curriculum preset loaded
        enableContent = false;
        enablePresentation = false;
        enableCurriculum = true;
        
        enableVisual = false;
        enableXml = false;
        enableAssessment = false;
        enableAnalytics = true;
    } else {
        // Lesson or slide mode
        enableContent = true;
        
        // Presentation editor is only enabled if the lesson preset actually contains presentation data
        const presVal = window.presentationModel ? window.presentationModel.getValue().trim() : '';
        enablePresentation = (presVal !== "");
        
        enableCurriculum = false;
        
        enableVisual = true;
        enableXml = true;
        
        if (renderMode === "lesson") {
            const slide = window.currentSlides && window.currentSlides[selectedSlideIndex];
            enableAssessment = slide ? (slide.type === 'multiple_choice' || slide.type === 'short_answer') : false;
        } else {
            // raw slide mode
            const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
            enableAssessment = contentYaml.includes("type: multiple_choice") || contentYaml.includes("type: short_answer");
        }
        
        enableAnalytics = false;
    }
    
    // Apply Left Editor Visibilities
    applyTabState(tabContent, enableContent);
    applyTabState(tabPresentation, enablePresentation);
    applyTabState(tabCurriculum, enableCurriculum);
    
    // Apply Right Preview Visibilities
    applyTabState(tabVisual, enableVisual);
    applyTabState(tabXml, enableXml);
    applyTabState(tabAssessment, enableAssessment);
    applyTabState(tabAnalytics, enableAnalytics);
    
    // Ensure that if the currently active tab gets disabled, we switch to a valid enabled tab!
    // Left side:
    if (activeEditorTab === 'content' && !enableContent) {
        switchEditorTab(enableCurriculum ? 'curriculum' : 'presentation');
    } else if (activeEditorTab === 'presentation' && !enablePresentation) {
        switchEditorTab(enableContent ? 'content' : 'curriculum');
    } else if (activeEditorTab === 'curriculum' && !enableCurriculum) {
        switchEditorTab(enableContent ? 'content' : 'presentation');
    }
    
    // Right side:
    const isVisualActive = tabVisual.classList.contains('active');
    const isXmlActive = tabXml.classList.contains('active');
    const isAssessmentActive = tabAssessment.classList.contains('active');
    const isAnalyticsActive = tabAnalytics.classList.contains('active');
    
    if (isVisualActive && !enableVisual) {
        togglePreviewTab(enableAnalytics ? 'curriculum' : 'xml');
    } else if (isXmlActive && !enableXml) {
        togglePreviewTab(enableVisual ? 'visual' : (enableAnalytics ? 'curriculum' : 'assessment'));
    } else if (isAssessmentActive && !enableAssessment) {
        togglePreviewTab(enableVisual ? 'visual' : 'xml');
    } else if (isAnalyticsActive && !enableAnalytics) {
        togglePreviewTab(enableVisual ? 'visual' : 'xml');
    }
}

function applyTabState(tabElement, isEnabled) {
    if (isEnabled) {
        tabElement.classList.remove('disabled');
        tabElement.disabled = false;
    } else {
        tabElement.classList.add('disabled');
        tabElement.disabled = true;
    }
}

// Load preset templates
async function onPresetChange(fileName) {
    if (typeof resetAssessmentSandboxState === 'function') {
        resetAssessmentSandboxState();
    }
    document.getElementById('status-container').style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
    document.getElementById('status-container').style.borderColor = 'rgba(99, 102, 241, 0.2)';
    document.getElementById('status-container').style.color = 'var(--primary)';
    document.getElementById('status-text').innerText = "Loading preset...";

    try {
        selectedSlideIndex = 0;

        // Handle Custom Blank Sandbox Option
        if (fileName === 'custom') {
            const customContent = `# yaml-language-server: $schema=https://raw.githubusercontent.com/seehiong/eduvis/main/schemas/lesson.schema.json
schema_version: "0.5"

curriculum:
  code: custom-curriculum
  topic: custom-topic

lesson:
  title: "My Custom Lesson"
  concepts:
    - custom_concept

progression:
  pattern: direct_instruction
  phases:
    - phase: explain
      purpose: conceptual_model

content:
  - id: slide_1
    type: fact_boxes
    concepts:
      - custom_concept
    placement:
      lesson_phase: explain
      purpose: conceptual_model
      layout_zone: center
      memory_role: anchor
    items:
      - text: "Welcome to your custom EduVis sandbox!"
        border_color: indigo
`;

            const customPres = `# yaml-language-server: $schema=https://raw.githubusercontent.com/seehiong/eduvis/main/schemas/presentation.schema.json
schema_version: "0.5"

slides:
  - id: slide_1
    advance: manual
`;

            const customCurr = `# yaml-language-server: $schema=https://raw.githubusercontent.com/seehiong/eduvis/main/schemas/curriculum.schema.json
schema_version: "0.5"

concepts:
  - code: custom_concept
    name: Custom Concept
    description: A custom concept definition
    exam_weight: 1.0

skills: []
misconceptions: []
dependencies: []
`;
            window.contentModel.setValue(customContent);
            window.presentationModel.setValue(customPres);
            window.curriculumModel.setValue(customCurr);

            switchEditorTab('content');
            togglePreviewTab('visual');

            isRenderInProgress = false;
            parseStructureAndRender();
            return;
        }

        const response = await fetch(`./${fileName}?cb=` + new Date().getTime());
        if (!response.ok) throw new Error("Preset file not found");
        const text = await response.text();

        // If it is a standalone curriculum preset
        if (fileName.endsWith('-curriculum.yaml') || fileName.endsWith('curriculum.yaml')) {
            window.curriculumModel.setValue(text);
            window.contentModel.setValue('');
            window.presentationModel.setValue('');
            
            // Switch tabs
            switchEditorTab('curriculum');
            togglePreviewTab('curriculum');
            
            isRenderInProgress = false;
            parseStructureAndRender();
            return;
        }

        // Determine sidecar presentation path using suffix matching
        let presFileName = fileName;
        let hasPresentation = false;
        if (fileName.endsWith('-lesson.yaml')) {
            presFileName = fileName.replace('-lesson.yaml', '-presentation.yaml');
            hasPresentation = true;
        } else if (fileName.endsWith('-content.yaml')) {
            presFileName = fileName.replace('-content.yaml', '-presentation.yaml');
            hasPresentation = true;
        }

        let presentationText = '';
        if (hasPresentation) {
            try {
                const presResponse = await fetch(`./${presFileName}?cb=` + new Date().getTime());
                if (presResponse.ok) {
                    presentationText = await presResponse.text();
                }
            } catch (presErr) {
                console.warn("No presentation sidecar found for: " + fileName, presErr);
            }
        }

        window.contentModel.setValue(text);
        window.presentationModel.setValue(presentationText);

        // Fetch curriculum file dynamically
        let currFileName = 'reference/showcase-curriculum.yaml';
        if (fileName.includes('singapore') || fileName.includes('SEC-math')) {
            currFileName = 'reference/singapore-sec1-curriculum.yaml';
        }
        
        try {
            const currRes = await fetch(`./${currFileName}?cb=` + new Date().getTime());
            if (currRes.ok) {
                const currText = await currRes.text();
                window.curriculumModel.setValue(currText);
            }
        } catch (currErr) {
            console.warn("Could not load curriculum preset: " + currFileName);
        }

        switchEditorTab('content');
        parseStructureAndRender();
    } catch (err) {
        showError("Failed to fetch preset: " + err.message);
    }
}

// Parse metadata & validate
function parseStructureAndRender() {
    if (!window.pyodideInstance || isRenderInProgress) return;
    isRenderInProgress = true;

    const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
    const presentationYaml = window.presentationModel ? window.presentationModel.getValue() : '';
    const curriculumYaml = window.curriculumModel ? window.curriculumModel.getValue() : '';

    // Standalone Curriculum Validation
    if (!contentYaml.trim() && curriculumYaml.trim()) {
        renderMode = "curriculum";
        document.getElementById('slide-selector-section').style.display = 'none';
        updateTabVisibilities();

        try {
            const resultJson = pyValidateCurriculum(curriculumYaml);
            const result = JSON.parse(resultJson);

            if (result.error) {
                showError(result.error);
                isRenderInProgress = false;
                return;
            }

            if (result.warnings && result.warnings.length > 0) {
                hasValidationErrorsOrWarnings = true;
                validationMessages = result.warnings;
                showValidationMessages(result.warnings);
            } else {
                hasValidationErrorsOrWarnings = false;
                validationMessages = [];
                hideError();
            }

            // Render analytics dashboard
            renderCurriculumDashboard();
        } catch (err) {
            showError(err.message);
        }
        isRenderInProgress = false;
        return;
    }

    try {
        const resultJson = pyParseLessonStructure(contentYaml, presentationYaml);
        const result = JSON.parse(resultJson);

        if (result.error) {
            showError(result.error);
            isRenderInProgress = false;
            return;
        }

        if (result.warnings && result.warnings.length > 0) {
            hasValidationErrorsOrWarnings = true;
            validationMessages = result.warnings;
            showValidationMessages(result.warnings);
        } else {
            hasValidationErrorsOrWarnings = false;
            validationMessages = [];
            hideError();
        }

        presentationData = result.presentation;
        lessonMetadataTitle = result.title || 'Lesson';
        lessonCurriculumCode = (result.curriculum && result.curriculum.code) || 'showcase';

        if (result.type === "lesson") {
            renderMode = "lesson";
            currentSlides = result.slides;

            document.getElementById('slide-selector-section').style.display = 'flex';
            if (selectedSlideIndex >= currentSlides.length) {
                selectedSlideIndex = 0;
            }
            updateTabVisibilities();
            updateSlideSelectorUI();
        } else {
            renderMode = "slide";
            document.getElementById('slide-selector-section').style.display = 'none';
            updateTabVisibilities();
        }

        resetStepAndRender();

    } catch (err) {
        showError(err.message);
        isRenderInProgress = false;
        updateTabVisibilities();
    }
}

// Renders the slide tab buttons
function updateSlideSelectorUI() {
    const container = document.getElementById('slide-tabs-container');
    container.innerHTML = '';

    document.getElementById('slide-count-indicator').innerText =
        `${selectedSlideIndex + 1} of ${currentSlides.length}`;

    currentSlides.forEach((slide) => {
        const tab = document.createElement('div');
        tab.className = 'slide-tab';
        if (slide.index === selectedSlideIndex) {
            tab.classList.add('active');
        }

        tab.innerText = `${slide.index + 1}. ${slide.id}`;
        tab.title = slide.title;
        tab.onclick = () => {
            selectedSlideIndex = slide.index;
            updateSlideSelectorUI();
            resetStepAndRender();
        };
        container.appendChild(tab);
    });
}

function resetStepAndRender(keepPlaying = false) {
    activeStepIndex = 0;
    if (!keepPlaying) {
        isPlaying = false;
        document.getElementById('btn-play-pause').innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
    }
    clearTimeout(autoAdvanceTimeout);
    performRender();
}

// Executes Python render & updates Assessment Sandbox
function performRender() {
    updateTabVisibilities();
    const contentYaml = window.contentModel ? window.contentModel.getValue() : '';
    const presentationYaml = window.presentationModel ? window.presentationModel.getValue() : '';
    const groupSelect = document.getElementById('group-select').value;
    const slide = currentSlides[selectedSlideIndex];

    if (renderMode === "lesson" && currentSlides.length === 0) {
        showError("No slides in lesson content block.");
        isRenderInProgress = false;
        return;
    }

    const slideId = slide ? slide.id : "";
    const slidePres = presentationData && presentationData.slides ?
        presentationData.slides.find(s => s.id === slideId) : null;

    const reveals = slidePres && slidePres.reveals ? slidePres.reveals : [];

    let maxStepIndex = 0;
    reveals.forEach(rev => {
        if (rev.steps) {
            rev.steps.forEach(st => {
                if (st.index > maxStepIndex) maxStepIndex = st.index;
            });
        }
    });

    const controller = document.getElementById('presentation-controller');
    if (renderMode === "lesson" && slidePres && (reveals.length > 0 || (slidePres.advance === 'auto' && slidePres.duration !== undefined))) {
        controller.style.display = 'flex';
    } else {
        controller.style.display = 'none';
        document.getElementById('narration-subtitle').style.display = 'none';
        const renderArea = document.getElementById('svg-render-area');
        renderArea.style.transformOrigin = "50% 50%";
        renderArea.style.transform = "scale(1)";
    }

    let svgOutput = "";

    document.getElementById('status-container').style.backgroundColor = 'rgba(245, 158, 11, 0.1)';
    document.getElementById('status-container').style.borderColor = 'rgba(245, 158, 11, 0.2)';
    document.getElementById('status-container').style.color = '#f59e0b';
    document.getElementById('status-text').innerText = "Compiling SVG...";

    try {
        if (renderMode === "lesson") {
            if (slidePres && reveals.length > 0) {
                svgOutput = pyRenderSlideFromLesson(contentYaml, presentationYaml, selectedSlideIndex, groupSelect, activeStepIndex);
            } else {
                svgOutput = pyRenderSlideFromLesson(contentYaml, presentationYaml, selectedSlideIndex, groupSelect, null);
            }
        } else {
            svgOutput = pyRenderRawSlide(contentYaml, groupSelect);
        }

        document.getElementById('svg-render-area').innerHTML = svgOutput;
        document.getElementById('xml-output-area').value = svgOutput;

        if (hasValidationErrorsOrWarnings) {
            showValidationMessages(validationMessages);
        } else {
            hideError();
        }

        // Live update of Interactive Assessment Sandbox Tab
        if (renderMode === "lesson") {
            try {
                const elementJson = pyGetElementJson(contentYaml, selectedSlideIndex);
                const element = JSON.parse(elementJson);
                const elementYaml = pyGetElementYaml(contentYaml, selectedSlideIndex);
                renderAssessmentSandbox(element, elementYaml, lessonCurriculumCode, lessonMetadataTitle);
            } catch (elemErr) {
                console.error("Failed to parse element for assessment: ", elemErr);
            }
        }

        // Auto-advance & zoom viewport logic
        if (renderMode === "lesson" && slidePres) {
            const hasSteps = reveals.length > 0;
            document.getElementById('step-indicator').innerText = hasSteps ? `Step ${activeStepIndex + 1} of ${maxStepIndex + 1}` : `Slide ${selectedSlideIndex + 1} of ${currentSlides.length}`;
            const progressPercent = hasSteps && maxStepIndex > 0 ? (activeStepIndex / maxStepIndex) * 100 : 100;
            document.getElementById('timeline-progress-bar').style.width = `${progressPercent}%`;

            let stepCaption = "";
            let stepDuration = null;
            let viewportData = null;

            if (hasSteps) {
                reveals.forEach(rev => {
                    if (rev.steps) {
                        const stepObj = rev.steps.find(st => st.index === activeStepIndex);
                        if (stepObj) {
                            if (stepObj.caption) stepCaption = stepObj.caption;
                            if (stepObj.auto_advance_after !== undefined) stepDuration = stepObj.auto_advance_after;
                            if (stepObj.viewport) viewportData = stepObj.viewport;
                        }
                    }
                });
            }

            if (stepDuration === null && slidePres.advance === 'auto' && slidePres.duration !== undefined) {
                stepDuration = slidePres.duration;
            }

            const subtitleEl = document.getElementById('narration-subtitle');
            if (stepCaption) {
                subtitleEl.innerText = stepCaption;
                subtitleEl.style.display = 'block';
            } else {
                subtitleEl.style.display = 'none';
            }

            const renderArea = document.getElementById('svg-render-area');
            if (viewportData) {
                const zoom = viewportData.zoom !== undefined ? viewportData.zoom : 1;
                const center = viewportData.center || [400, 300];
                renderArea.style.transformOrigin = `${center[0]}px ${center[1]}px`;
                renderArea.style.transform = `scale(${zoom})`;
            } else {
                renderArea.style.transformOrigin = "50% 50%";
                renderArea.style.transform = "scale(1)";
            }

            clearTimeout(autoAdvanceTimeout);
            if (isPlaying && stepDuration !== null) {
                autoAdvanceTimeout = setTimeout(() => {
                    if (hasSteps && activeStepIndex < maxStepIndex) {
                        activeStepIndex++;
                        performRender();
                    } else {
                        if (selectedSlideIndex < currentSlides.length - 1) {
                            selectedSlideIndex++;
                            updateSlideSelectorUI();
                            resetStepAndRender(true);
                        } else {
                            isPlaying = false;
                            document.getElementById('btn-play-pause').innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
                        }
                    }
                }, stepDuration * 1000);
            }
        }

    } catch (err) {
        showError("Render Error:\n" + err.message);
    } finally {
        isRenderInProgress = false;
    }
}

// Playback Trigger Step controls
function prevStep() {
    if (activeStepIndex > 0) {
        activeStepIndex--;
        isPlaying = false;
        document.getElementById('btn-play-pause').innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
        clearTimeout(autoAdvanceTimeout);
        performRender();
    }
}

function nextStep() {
    const slide = currentSlides[selectedSlideIndex];
    if (!slide) return;
    const slideId = slide.id;
    const slidePres = presentationData && presentationData.slides ?
        presentationData.slides.find(s => s.id === slideId) : null;
    const reveals = slidePres && slidePres.reveals ? slidePres.reveals : [];

    let maxStepIndex = 0;
    reveals.forEach(rev => {
        if (rev.steps) {
            rev.steps.forEach(st => {
                if (st.index > maxStepIndex) maxStepIndex = st.index;
            });
        }
    });

    if (activeStepIndex < maxStepIndex) {
        activeStepIndex++;
        isPlaying = false;
        document.getElementById('btn-play-pause').innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
        clearTimeout(autoAdvanceTimeout);
        performRender();
    }
}

function togglePlayPause() {
    isPlaying = !isPlaying;
    const btn = document.getElementById('btn-play-pause');
    if (isPlaying) {
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`;
        performRender();
    } else {
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
        clearTimeout(autoAdvanceTimeout);
    }
}

function triggerRender() {
    parseStructureAndRender();
}

// Visual Preview vs Raw SVG Source vs Interactive Assessment Sandbox vs Curriculum Analytics tabs
function togglePreviewTab(tabName) {
    if (renderMode === "curriculum" && tabName !== 'curriculum' && tabName !== 'xml') {
        alert("Visual Preview and Interactive Assessment are not available in Standalone Curriculum mode. Select a lesson preset to view slides.");
        return;
    }

    document.getElementById('tab-visual').classList.remove('active');
    document.getElementById('tab-xml').classList.remove('active');
    document.getElementById('tab-assessment').classList.remove('active');
    document.getElementById('tab-curriculum').classList.remove('active');

    document.getElementById('svg-render-area').style.display = 'none';
    document.getElementById('xml-output-area').style.display = 'none';
    document.getElementById('assessment-area').style.display = 'none';
    document.getElementById('curriculum-area').style.display = 'none';

    // Hide float controllers on assessment/curriculum view
    const subtitle = document.getElementById('narration-subtitle');
    const controller = document.getElementById('presentation-controller');

    if (tabName === 'visual') {
        document.getElementById('tab-visual').classList.add('active');
        document.getElementById('svg-render-area').style.display = 'flex';
        // restore controller visibility if valid
        parseStructureAndRender();
    } else if (tabName === 'xml') {
        document.getElementById('tab-xml').classList.add('active');
        document.getElementById('xml-output-area').style.display = 'block';
        subtitle.style.display = 'none';
        controller.style.display = 'none';
    } else if (tabName === 'assessment') {
        document.getElementById('tab-assessment').classList.add('active');
        document.getElementById('assessment-area').style.display = 'flex';
        subtitle.style.display = 'none';
        controller.style.display = 'none';
    } else if (tabName === 'curriculum') {
        document.getElementById('tab-curriculum').classList.add('active');
        document.getElementById('curriculum-area').style.display = 'flex';
        subtitle.style.display = 'none';
        controller.style.display = 'none';
        renderCurriculumDashboard();
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

        const cov = data.coverage;
        const gaps = data.gaps;
        const centrality = data.centrality;

        // 1. Generate Mermaid flow definition
        let mCode = 'flowchart TD\n';
        mCode += '  classDef covered fill:#10b981,stroke:#059669,stroke-width:2px,color:#ffffff;\n';
        mCode += '  classDef uncovered fill:#334155,stroke:#475569,stroke-width:1px,color:#94a3b8;\n';
        mCode += '  classDef gap fill:#ef4444,stroke:#dc2626,stroke-width:2px,color:#ffffff;\n';

        // Define nodes
        data.concepts.forEach(c => {
            const isCovered = cov.covered_concepts.includes(c.code);
            const hasGap = gaps.some(g => g.concept === c.code);

            let styleClass = 'uncovered';
            let labelSuffix = '';
            if (hasGap) {
                styleClass = 'gap';
                labelSuffix = ' (Prereq Gap!)';
            } else if (isCovered) {
                styleClass = 'covered';
                labelSuffix = ' (Covered)';
            }

            const cleanName = c.name.replace(/&/g, 'and');
            mCode += `  ${c.code}["<b>${cleanName}</b><br/>Exam Weight: ${Math.round(c.exam_weight * 100)}%${labelSuffix}"]\n`;
            mCode += `  class ${c.code} ${styleClass};\n`;
        });

        // Define links
        data.dependencies.forEach(d => {
            mCode += `  ${d.from} --> ${d.to}\n`;
        });

        // 2. Build HTML Dashboard Layout
        let html = `
            <div style="display: flex; flex-direction: column; gap: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px;">
                    <h2 style="margin: 0; font-size: 1.5rem; font-family: var(--font-sans); font-weight: 600; color: #f8fafc;">Curriculum &amp; Knowledge Analytics</h2>
                    <span style="font-size: 0.85rem; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">v0.5 Knowledge Engine</span>
                </div>
        `;

        // Prerequisite Gaps Alert
        if (gaps.length > 0) {
            html += `
                <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; color: #fca5a5; font-weight: 600; font-size: 1rem;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        Dependency Gaps Detected!
                    </div>
                    <ul style="margin: 0; padding-left: 20px; color: #f8fafc; font-size: 0.9rem; line-height: 1.5;">
            `;
            gaps.forEach(g => {
                const conceptName = data.concepts.find(c => c.code === g.concept)?.name || g.concept;
                const missingName = data.concepts.find(c => c.code === g.missing_prerequisite)?.name || g.missing_prerequisite;
                html += `<li>Lesson teaches <b>${conceptName}</b> but misses prerequisite <b>${missingName}</b>.</li>`;
            });
            html += `
                    </ul>
                </div>
            `;
        }

        // Graph Visualization container
        html += `
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px);">
                <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 1.1rem; color: #cbd5e1; font-weight: 500;">Prerequisite Dependency Map</h3>
                <div id="mermaid-graph" class="mermaid" style="display: flex; justify-content: center; background: #0b0f19; padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); overflow-x: auto;">
                    ${mCode}
                </div>
            </div>
        `;

        // Two-column bottom layout
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">

                <!-- Centrality & Bottlenecks -->
                <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px;">
                    <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 1.1rem; color: #cbd5e1; font-weight: 500;">Concept Centrality &amp; Bottlenecks</h3>
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

                <!-- Taxonomy Coverage Table -->
                <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px;">
                    <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 1.1rem; color: #cbd5e1; font-weight: 500;">Lesson Scope &amp; Coverage</h3>

                    <div style="margin-bottom: 16px;">
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

        // 3. Render Mermaid diagram asynchronously
        console.log("Mermaid flowchart code:\n", mCode);
        const graphDiv = document.getElementById('mermaid-graph');
        mermaid.run({
            nodes: [graphDiv]
        }).catch(err => {
            console.warn("Mermaid graph parsing/rendering yielded a syntax error or conflict:", err);
        });

    } catch (err) {
        container.innerHTML = `<div style="color: #ef4444; padding: 20px; border: 1px solid #ef4444; border-radius: 8px; background: rgba(239, 68, 68, 0.1);">WASM Execution Error: ${err.message}</div>`;
    }
}

// Error & Validation messages handlers
function showError(msg) {
    const banner = document.getElementById('error-banner');
    banner.innerText = msg;
    banner.style.backgroundColor = 'rgba(239, 68, 68, 0.95)';
    banner.style.borderTop = '1px solid var(--accent-red)';
    banner.style.display = 'block';

    document.getElementById('status-container').style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
    document.getElementById('status-container').style.borderColor = 'rgba(239, 68, 68, 0.2)';
    document.getElementById('status-container').style.color = 'var(--accent-red)';
    document.getElementById('status-text').innerText = "Compile Error";
}

function showValidationMessages(messages) {
    const banner = document.getElementById('error-banner');
    const hasErrors = messages.some(msg => msg.startsWith("ERROR:"));

    banner.innerHTML = messages.map(msg => {
        if (msg.startsWith("ERROR:")) {
            return `<div style="color: #fca5a5; font-weight: 600; margin-bottom: 4px;">● ${msg}</div>`;
        } else {
            return `<div style="color: #fde047; margin-bottom: 4px;">▲ ${msg}</div>`;
        }
    }).join("");

    banner.style.display = 'block';

    if (hasErrors) {
        banner.style.backgroundColor = 'rgba(127, 29, 29, 0.95)';
        banner.style.borderTop = '1px solid #ef4444';

        document.getElementById('status-container').style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
        document.getElementById('status-container').style.borderColor = 'rgba(239, 68, 68, 0.2)';
        document.getElementById('status-container').style.color = 'var(--accent-red)';
        document.getElementById('status-text').innerText = "Validation Error";
    } else {
        banner.style.backgroundColor = 'rgba(120, 85, 0, 0.95)';
        banner.style.borderTop = '1px solid #f59e0b';

        document.getElementById('status-container').style.backgroundColor = 'rgba(245, 158, 11, 0.1)';
        document.getElementById('status-container').style.borderColor = 'rgba(245, 158, 11, 0.2)';
        document.getElementById('status-container').style.color = '#f59e0b';
        document.getElementById('status-text').innerText = "Validation Warnings";
    }
}

function hideError() {
    document.getElementById('error-banner').style.display = 'none';
    document.getElementById('status-container').style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
    document.getElementById('status-container').style.borderColor = 'rgba(16, 185, 129, 0.2)';
    document.getElementById('status-container').style.color = 'var(--accent-green)';
    document.getElementById('status-text').innerText = "Connected";
}

// Download SVG file
function downloadSvg() {
    const svgMarkup = document.getElementById('xml-output-area').value;
    if (!svgMarkup) return;

    let fileName = "slide.svg";
    if (renderMode === "lesson" && currentSlides[selectedSlideIndex]) {
        fileName = `${currentSlides[selectedSlideIndex].id}.svg`;
    }

    const blob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Copy SVG XML code
function copyRawSvg() {
    const svgMarkup = document.getElementById('xml-output-area').value;
    if (!svgMarkup) return;

    navigator.clipboard.writeText(svgMarkup).then(() => {
        alert("SVG source copied to clipboard!");
    }).catch(err => {
        console.error("Copy failed: ", err);
    });
}
