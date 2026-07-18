# EduVis Studio: Design, Projections, and Client-Side WASM Architecture

EduVis Studio (or EduVis Workspace) is the Integrated Development Environment (IDE) designed for educational content creators, curriculum planners, and software developers. 

**EduVis Studio is not another YAML editor. It is a multi-projection educational IDE where text, graphs, diagnostics, and compiler views are synchronized representations of the same educational specification. Every projection is a synchronized view over the same educational specification; no projection owns the data.**

It marks a strategic evolution from a simple **Live Editor** (which solved the v0.x problem of *"Can I edit YAML and see the SVG?"*) to a **Pedagogical IDE** (solving the v1.x problem of *"Can I design, inspect, validate, compile, and reason about an educational system?"*).

---

## 1. The Paradigm Shift: Projections

EduVis separates educational meaning from presentation rendering. Therefore, the editor is not the product itself—it is simply one panel inside a larger workspace centered on **projections**. A projection is a distinct visual view generated dynamically from the underlying educational specifications.

```text
               Educational Specification (Source of Truth)
                                │
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
  Graph View               Storyboard View         Assessment View
 (Curriculum)                (Lesson)                (Blueprint)
```

EduVis Studio supports six primary projections:

### 1. Specification View
A clean text editor pane (using a code editor component) displaying the raw specification files (YAML formats: `curriculum.yaml`, `lesson.yaml`, `learner_state.yaml`). This is the absolute source of truth.

### 2. Curriculum View
An interactive graph visualization (built using an interactive graph canvas) mapping the static educational hierarchy:
*   **Concepts** form the central vertical spine of the graph.
*   **Skills** branch out to the left (representing cognitive objectives).
*   **Misconceptions** branch out to the right (representing common student pitfalls).

### 3. Storyboard View
A storyboard projection illustrating the pedagogical progression of a lesson. Instead of a linear list of slides, slides are grouped by their lesson phases:
$$\text{Hook} \longrightarrow \text{Explore} \longrightarrow \text{Explain} \longrightarrow \text{Practice} \longrightarrow \text{Retrieve}$$
*   Shows a visual overview of the "pedagogical rhythm" of the slide deck.

### 4. Assessment View
An analytics projection displaying the properties of compiled test papers using the Blueprint Engine (`eduvis/core/blueprint_engine.py`):
*   **Concept/Skill Coverage**: Visual indicators showing which parts of the curriculum are under-tested or over-tested.
*   **Item Difficulty Curve**: A chart graphing the cognitive climb from starter to advanced questions.
*   **Misconception Coverage**: Verification of whether wrong answer options map back to the declared curriculum misconceptions.

### 5. Learner Projection
A simulator tool that loads a `learner_state.yaml` and overlays it directly onto the curriculum graph canvas, coloring nodes based on cognitive mastery status.

### 6. Compiler Pipeline View
An inspectable timeline of the compilation pipeline:
$$\text{Syllabus} \longrightarrow \text{Curriculum Planner} \longrightarrow \text{Lesson Planner} \longrightarrow \text{Assessment Assembler} \longrightarrow \text{Presentation Sidecar}$$
Authors can select any stage in the compiling sequence to view the generated intermediate representations (IR) or debugging logs.

---

## 2. Cross-cutting Inspectors: Universal Relationship Explorer

Instead of sitting as a standalone view, the **Universal Relationship Explorer** operates as a cross-cutting inspector panel that can be invoked from any active projection (Curriculum View, Storyboard View, Assessment View, or Learner Projection). 

Clicking any element (concept, skill, or misconception) anywhere in the IDE opens this inspector to show "everything connected" to that node:
*   **Upstream**: Prerequisite concepts and required incoming skill dependencies.
*   **Downstream**: Target concept dependents and outcomes.
*   **Linked Lessons**: Any lesson units that introduce, explain, or evaluate the element.
*   **Linked Assessments**: Direct evaluation questions checking mastery of this element.
*   **Linked Misconceptions**: All diagnostic error codes linked to this concept.
*   **Learner Mastery Status**: The active, visual comprehension telemetry for that node.

---

## 3. Core IDE Capabilities (v1.x Scope)

The primary build targets for the initial Studio releases focus on foundational workspace tasks:

### A. Multi-Projection Rendering
Ensuring that changes typed in the Specification View immediately trigger hot-reloading updates in the Curriculum, Storyboard, and Learner projections.

### B. Pedagogical Diagnostics (The Problems Pane)
A bottom panel compiler diagnostic console. Unlike typical code compilers that check syntax, this validator reports instructional design warnings:

| Severity | Diagnostic Message | Source Engine |
| :--- | :--- | :--- |
| **Error** | Prerequisite `integers` has not been taught before introducing `negative_numbers`. | `remediation_engine` |
| **Warning** | Misconception `concept_fraction_addition` lacks diagnostic assessment coverage. | `blueprint_engine` |
| **Warning** | Cognitive overload: Lesson has `explain` phase with visual weight exceeding limits. | `validator` |
| **Info** | Retrieval spacing: Concept `decimals` is due for active recall session. | `spaced_repetition` |

### C. Offline Portability & Local File Editing
Support for native local file editing with offline support, allowing users to save edits directly to their local desktop system or load files from their hard drive without a network connection.

---

## 4. Planned Capabilities & Long-Term Features

These features represent the strategic roadmap for the IDE to enhance compiler orchestration and design feedback:

### A. Projection Synchronization
A deeply integrated UX behavior where all views move together:
*   Clicking a concept node in the Curriculum View automatically scrolls and focuses the corresponding definition lines in the Specification View.
*   Simultaneously, the Universal Relationship Explorer updates to map dependencies, the Assessment View highlights affected questions, and the Problems pane refreshes its focused warnings list.

### B. Bidirectional Visual Authoring & AST Sync
Allowing users to author visually or textually interchangeably:
*   **Visual-to-Code**: Drawing a prerequisite arrow from *Integers* to *Fractions* in the Graph View automatically updates the dependencies list in the source file.
*   **Inspector-to-Code**: Changing an `exam_weight` slider in the node inspector dynamically alters the educational specification.
*   **AST Preservation**: To prevent visual edits from destroying human-authored spacing, layout, and comments in the educational specification files, the Studio uses **AST-preserving round-tripping** (e.g., parsing the source string, mutating specific values, and writing back comments intact).

### C. Time Travel Debugging
Because compilers, planners, and trace engines in the Remediation Engine (`eduvis/core/remediation_engine.py`) are algorithmic sequences, this feature allows:
*   **Step-by-Step Replays**: Dragging a slider to trace the execution history of planners (e.g., how the Lesson Planner decided to insert a remediation slide).
*   **State Simulation**: Dynamically toggling student mastery parameters or stepping through student response timelines to visually watch mastery curves change.
*   **State Diffing**: Visualizing difference states between compiling runs.

---

## 5. Technical Architecture: Client-Side WASM

EduVis Studio is built as a browser-first, single-page application (SPA) designed to run entirely locally in the client browser using **Pyodide (WebAssembly)**. This guarantees data privacy, local offline portability, and zero hosting/backend maintenance costs.

```text
     ┌────────────────────────────────────────────────────────┐
     │                   Browser Front-End                    │
     │     Workspace UI · Projection Engine · Source Editor   │
     └───────────────────────────┬────────────────────────────┘
                                 │ Web Worker PostMessage
                                 ▼
     ┌────────────────────────────────────────────────────────┐
     │               Web Worker Sandbox (WASM)                │
     │                                                        │
     │      Pyodide (Python Runtime environment)              │
     │                        │                               │
     │                        ├─► Python Standard Library     │
     │                        ├─► Optional Dependencies       │
     │                        └─► EduVis Core (zipped)        │
     └────────────────────────────────────────────────────────┘
```

### A. Web Worker Multi-threading
Pyodide is loaded inside a background **Web Worker**. This isolates the Python runtime execution from the user interface thread:
*   When a user types or interacts with the GUI, the front-end sends the source string to the Web Worker.
*   The Worker parses, validates, and renders the SVGs using the local python package, and returns the diagnostics.
*   This prevents the visual workspace from freezing.

### B. Package Startup Optimization
To optimize load times down to sub-second launches, the Studio implements:
1.  **Lazy Dependency Loading**: Heavy libraries are not imported on initial load. They are dynamically fetched and imported *only* when a mathematical slide containing equations/formula elements is loaded.
2.  **Package Bundling**: The core Python library is zipped during the build step using the packaging script (`scripts/pack_studio.py`) and loaded as a single binary stream.

### C. PWA and Offline Support
EduVis Studio is designed to function as an installable Progressive Web App (PWA):
*   A **Service Worker** caches the Pyodide WebAssembly runtime files, jsDelivr package assets, and the `eduvis.zip` bundle.
*   Users can launch the IDE completely offline.
*   Native local file editing with offline support ensures user workspace state is persisted securely without any server uploads.

---

## 6. Long-Term Strategy & Repository Roadmap

The relationship between EduVis Core and EduVis Studio is modeled after robust infrastructure ecosystems like **LLVM/Clang** or **TypeScript/VS Code**:

*   **EduVis Core (The Compiler / IR)**: Acts as the canonical representation standard, containing the compiler schemas, parsers, and validation runtimes. It evolves conservatively throughout the v1.x series, with backward compatibility as a primary design goal.
*   **EduVis Studio (The IDE)**: Acts as the visual interface layer, running client-side WASM. Almost all future innovation moves into the Studio (projections, UI, bidirectional editing, diagnostics, visual debugging, plugins, and collaborative visual authoring).

### Strategic Dependency Direction
The dependency graph between the two layers is strictly unidirectional:
$$\text{EduVis Studio} \longrightarrow \text{EduVis Core}$$
EduVis Core has zero knowledge of the visual editor, its UI framework, or its client-side state. It operates purely as a stateless compiler and IR standard library, guaranteeing that the educational specification can always be parsed, validated, and run in headless environments (like CLIs, AI agents, or backend services) without any IDE overhead.

### Repository Federation
While starting in a single monorepo for seamless co-development, the Studio is architecturally separated from the Core engine:
1.  **Core** (`eduvis/`) remains a lightweight, portable Python library distributed via PyPI.
2.  **Studio** (`studio/`) runs as a React/TypeScript web app.
3.  If the Studio grows independently, it may be separated into its own repository (`eduvis-studio/`), referencing the core package just like VS Code references its language servers. This allows independent releases, desktop packaging (Electron/Tauri wrappers), and clean separation of developer concerns.
