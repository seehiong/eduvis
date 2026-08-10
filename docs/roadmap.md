# EduVis Roadmap & Ecosystem Strategy (v1.2 - v1.5)

This document captures the strategic design choices, core principles, priorities, and architectural roadmap for the EduVis project.

> **EduVis is a stable educational intermediate representation (IR) for learning experiences, surrounded by an evolving ecosystem of compilers, analytics engines, Studio tooling, plugins, and AI agents.**

---

## 1. Core Principles

*   **Stability Before Features**: Backward compatibility is a first-class goal. Existing educational specifications should continue to compile across v1.x whenever possible. New capabilities should be additive rather than disruptive.
*   **Separation of Concerns**: The Core should describe educational meaning, not execution. Planning, analytics, rendering, visualization, and authoring belong to compilers, engines, Studio, or plugins rather than the schema itself.
*   **Core as Intermediate Representation**: EduVis Core serves as the canonical educational intermediate representation (IR) between authoring, AI generation, analysis, and rendering. The schema should remain independent of any specific editor, renderer, or execution environment.

---

## 2. Preservation Policy: Guarding the Core

EduVis Core is intended to evolve conservatively. New schema primitives should only be introduced when an authentic educational scenario cannot be represented using the existing five pillars. Improvements should preferentially be implemented in compilers, analytics engines, renderers, Studio projections, or plugins rather than expanding the intermediate representation itself. **The Core should remain small, expressive, and stable, allowing the surrounding ecosystem to innovate independently.**

---

## 3. Strategic Priorities

### Ⅰ. Studio Enhancements (★★★★★)
Focus **80% of design and execution efforts** on making the Studio a Pedagogical IDE, rather than just a visualization dashboard.
*   **Bidirectional Visual Editing**: The cornerstone of the IDE. Editing visual nodes (e.g. graph edges or storyboard cards) must preserve formatting and round-trip directly into AST updates in the YAML specification.
*   **Curriculum Analytics & Simulation**: Elevate the IDE into a *design simulator*. Allow designers to simulate student cohorts (e.g. 100 students) traversing curriculum pathways to calculate cognitive distribution and compare course layouts.

### Ⅱ. Learner State Evolution & Interfaces (★★★★☆)
Decouple statistical calculations from data schemas.
*   **`LearnerModel` Interface**: Define a clean, stable interface for learner state updates.
*   **Reference Implementations**: Provide diverse reference implementations (e.g., Simple mastery, forgetting-curve models, Bayesian Knowledge Tracing (BKT), Item Response Theory (IRT), Deep Knowledge Tracing (DKT), and future learner modeling approaches) that implement the interface without altering the underlying data schemas.

### Ⅲ. Presentation Primitives & Boundaries (★★★☆☆)
Establish strict boundaries between Core meaning and Visual rendering.
*   **Graphics Framework Avoidance**: Do not pollute the core specification with low-level layout primitives (like bezier, rect, polygon).
*   **High-Level Pedagogical Primitives**: Keep core schemas locked to conceptual primitives (`bar_model`, `number_line`, `coordinate_plane`). Let renderers handle layout compilation.

### Ⅳ. Studio Extensibility & API/SDKs
Define clear extension registries to avoid bloating the core codebase:
*   **Projection API & SDK**: Provide a `Projection Registry` plugin model so developers can register custom views (Mind Maps, Bloom's Taxonomy, Parent/Teacher Dashboards) as simple `Specification` ➜ `View` mappings.
*   **Compiler Plugins (IR Compilation)**: Refactor compiler commands to emit an explicit Intermediate Representation (e.g., `lesson.ir.json`), similar to LLVM or TypeScript:
    $$\text{Specification} \longrightarrow \text{Planner} \longrightarrow \text{Intermediate Representation (IR)} \longrightarrow \text{Renderer} \longrightarrow \text{Output}$$
    Compiler plugins operate on the compiled IR rather than directly mutating source specifications.

### Ⅴ. Agentic Generation Substrate ("LLM Proposes, EduVis Compiles")
Treat EduVis as an educational compiler and agent toolchain rather than relying on unconstrained LLM text generation.
*   **Intermediate Representation (`GenerationIntent`)**: LLMs generate structured Pydantic intents; EduVis deterministic engines execute prerequisite checking, graph traversal, and paper assembly.
*   **Adversarial Validation & Retry Loop**: Use EduVis schema and pedagogical validators as deterministic compilation gates, returning precise error tracebacks to the agent for candidate revision.
*   **Decoupled Architecture**: Maintain `EduVis Core` as an LLM-agnostic educational IR. Introduce `EduVis Agent` as a standalone orchestration service (LangGraph, Pydantic, FastAPI) leveraging local model inference (e.g., Ollama / Qwen3.5).

---

## 4. Version Roadmap

### v1.2 — Interactive Studio & Deployed Ecosystem (Released July 2026)
*   [x] Bidirectional visual editing & AST-preserving YAML serialization
*   [x] Universal inspector panel & multi-projection IDE
*   [x] Stateless compilation pipelines (Lesson Planner, Assessment Assembler)
*   [x] Learner mastery projection & remediation trace engines

### v1.3 — Agentic Generation & Educational Compiler
*   [ ] `EduVis Agent` orchestration service (LangGraph + Pydantic IR bridge)
*   [ ] Agentic Practice Paper Generation (Greedy paper assembler + LLM item synthesis)
*   [ ] Educational Generation Graph with adversarial EduVis validation loop
*   [ ] Homelab Model Ladder integration (Qwen3.5 4B/9B/27B via Ollama)
*   [ ] Studio "Teacher's Room" UI (step-by-step plan execution & Human-in-the-loop approval)

### v1.4 — Analytics, Cohorts & Extensibility
*   [ ] Learner cohort simulation engine & forgetting curve decay
*   [ ] Projection plugin API & SDK
*   [ ] Compiler plugin hooks & exported IR (`lesson.ir.json`)
*   [ ] Curriculum packaging & module distribution

---

## 5. Long-Term Ecosystem Vision

EduVis consists of independent but complementary layers:

```text
        EduVis Core           ← Stable, descriptive educational IR (schema, validators, graph)
             │
             ▼
  Execution & Compiler Layer  ← Deterministic planning, paper assembly, mastery projection
             │
             ▼
        EduVis Agent          ← LangGraph orchestration, GenerationIntent IR, LLM tools
             │
             ▼
       Local Inference        ← Homelab LLM inference (Ollama, Qwen3.5 Model Ladder)
             │
             ▼
        EduVis Studio         ← Pedagogical IDE, Teacher's Room, multi-projection workspace
```

*   **Core** provides the stable, descriptive educational IR.
*   **Execution & Compiler Layer** performs planning, scheduling, validation, prioritization, and layout compilation.
*   **EduVis Agent** manages stateful generation workflows, structured LLM intent parsing, and feedback retry loops.
*   **Local Inference** executes privacy-first model generation across the model ladder.
*   **Studio** provides the projection workspace, diagnostics, and human-in-the-loop authoring.

---

## 6. Versioning Philosophy

The v1.x series focuses on stabilizing the educational intermediate representation while expanding the surrounding ecosystem. Most innovation should occur outside the Core—within Studio, compiler engines, agent toolchains, analytics, plugins, renderers, and AI tooling. Changes to the Core schema are expected to be infrequent and driven only by demonstrated pedagogical requirements.
