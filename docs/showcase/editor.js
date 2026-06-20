/**
 * EduVis Live Editor — Main UI Controller & Script Coordinator
 */

let selectedSlideIndex = 0;
let currentSlides = [];
let renderMode = "lesson"; // "lesson" or "slide"
let isRenderInProgress = false;

// Monaco Editor instances
window.editor = null;
window.contentModel = null;
window.presentationModel = null;
let activeEditorTab = 'content';

let presentationData = null;
let activeStepIndex = 0;
let isPlaying = false;
let autoAdvanceTimeout = null;
let hasValidationErrorsOrWarnings = false;
let validationMessages = [];

let lessonCurriculumCode = 'showcase';
let lessonMetadataTitle = 'Lesson';

// Switch Monaco tabs (Content vs Presentation)
function switchEditorTab(tabName) {
    if (activeEditorTab === tabName) return;
    activeEditorTab = tabName;

    document.getElementById('tab-editor-content').classList.remove('active');
    document.getElementById('tab-editor-presentation').classList.remove('active');

    if (tabName === 'content') {
        document.getElementById('tab-editor-content').classList.add('active');
        window.editor.setModel(window.contentModel);
    } else {
        document.getElementById('tab-editor-presentation').classList.add('active');
        window.editor.setModel(window.presentationModel);
    }
}

// Initialize Monaco Editor
require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.48.0/min/vs' } });
require(['vs/editor/editor.main'], function () {
    window.contentModel = monaco.editor.createModel('# Loading content...', 'yaml');
    window.presentationModel = monaco.editor.createModel('# Loading presentation...', 'yaml');

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

    // Bootstrap Python environment in the background
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

            // Load default preset
            onPresetChange("lessons/negative-numbers-confidence-ladder.yaml");
        }
    );
});

// Load preset templates
async function onPresetChange(fileName) {
    document.getElementById('status-container').style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
    document.getElementById('status-container').style.borderColor = 'rgba(99, 102, 241, 0.2)';
    document.getElementById('status-container').style.color = 'var(--primary)';
    document.getElementById('status-text').innerText = "Loading preset...";

    try {
        const response = await fetch(`./${fileName}`);
        if (!response.ok) throw new Error("Preset file not found");
        const text = await response.text();

        selectedSlideIndex = 0;
        
        // Split content vs presentation using Python Safe YAML
        const splitJson = pySplitLessonYaml(text);
        const splitResult = JSON.parse(splitJson);
        window.contentModel.setValue(splitResult.content);
        window.presentationModel.setValue(splitResult.presentation || '');

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
            updateSlideSelectorUI();
        } else {
            renderMode = "slide";
            document.getElementById('slide-selector-section').style.display = 'none';
        }

        resetStepAndRender();

    } catch (err) {
        showError(err.message);
        isRenderInProgress = false;
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

// Visual Preview vs Raw SVG Source vs Interactive Assessment Sandbox tabs
function togglePreviewTab(tabName) {
    document.getElementById('tab-visual').classList.remove('active');
    document.getElementById('tab-xml').classList.remove('active');
    document.getElementById('tab-assessment').classList.remove('active');

    document.getElementById('svg-render-area').style.display = 'none';
    document.getElementById('xml-output-area').style.display = 'none';
    document.getElementById('assessment-area').style.display = 'none';

    // Hide float controllers on assessment view
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
