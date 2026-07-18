# EduVis Schema

**An open, curriculum-aware framework and knowledge representation for learning experiences.**

[**🚀 Try the Live EduVis Studio IDE**](https://seehiong.github.io/eduvis/)

EduVis describes the **educational meaning** of learning experiences — separating semantic pedagogical structure from raw presentation rendering. Inspired by the philosophy of Markdown, Mermaid, and Model Context Protocol (MCP), it aims to standardize how learning environments are modeled, compiled, and visualized.

EduVis consists of two complementary projects:
*   **EduVis Core**: The stable educational Intermediate Representation (IR), compiler pipeline, schema validator, and reference SVG renderer.
*   **EduVis Studio**: A browser-based educational IDE built on Pyodide/WASM that acts as the primary authoring, visualization, and debugging environment for educational content designers.

Inspired by the philosophy of separating meaning from rendering:

> Separate meaning from rendering.

---

## Getting Started

**Requirements:** Python 3.10+

### Option 1: Install from PyPI (Recommended for general use)

```bash
pip install eduvis
```

### Option 2: Clone and run locally with uv (Recommended for development)

```bash
git clone https://github.com/seehiong/eduvis
cd eduvis
uv sync
```

Then prefix commands with `uv run` (or use the globally installed `eduvis` if installed via PyPI/pip):

```bash
# Validate showcase lessons
uv run eduvis validate showcase/lessons/negative-numbers-confidence-ladder-lesson.yaml
uv run eduvis validate showcase/features/adaptive-remediation-branching-lesson.yaml
uv run eduvis validate showcase/features/visual-elements-catalog-lesson.yaml
uv run eduvis validate showcase/features/assessment-schemas-lesson.yaml

# Render all showcase assets to showcase/assets/
uv run python scripts/build_showcase.py

# Or render a single showcase lesson to a custom directory
uv run eduvis render showcase/lessons/negative-numbers-confidence-ladder-lesson.yaml -o output/negatives/

# Utility commands
uv run eduvis docs --subjects math
uv run eduvis schema -o eduvis/schemas/

# Curriculum graph inspection
uv run eduvis graph inspect showcase/reference/showcase-curriculum.yaml
uv run eduvis graph prereqs showcase/reference/showcase-curriculum.yaml rational_numbers --transitive
uv run eduvis graph dependents showcase/reference/showcase-curriculum.yaml integers
uv run eduvis graph path showcase/reference/showcase-curriculum.yaml integers real_numbers

# Mastery projection
uv run eduvis mastery project showcase/reference/showcase-curriculum.yaml showcase/reference/sample-learner-state.yaml

# Study plan generation
uv run eduvis study-plan showcase/reference/showcase-curriculum.yaml showcase/reference/sample-learner-state.yaml --mode exam_prep --hours 2

# Schema migration (auto-detects current version, or override with --from-ver)
uv run eduvis migrate showcase/lessons/ --to-ver 1.0

# Graph-driven lesson generation
uv run eduvis generate lesson showcase/reference/showcase-curriculum.yaml integers negative_numbers -o new_lesson.yaml
```


### Option 3: Install locally with pip

```bash
git clone https://github.com/seehiong/eduvis
cd eduvis
pip install -e .
```

### Run the Tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

### Code Quality and Maintainability Checks

To keep the codebase maintainable and clean, we enforce code quality and maintainability limits locally. These checks monitor:

1. **Cyclomatic Complexity**: Functions must have a McCabe complexity $\le 10$.
2. **Function Length**: Functions are restricted to a maximum of 50 statements.
3. **Nesting Depth**: Block nesting depth is restricted to at most 3 levels.
4. **Duplication Detection**: Code replication/duplication of 4 or more lines is flagged.
5. **Module Size**: Python files (modules) are limited to a maximum of 1000 lines.

To run these checks, ensure your development dependencies are synced:

```bash
uv sync --extra dev
```

Then run all quality checks with a single command:

```bash
uv run python scripts/run_checks.py
```

Alternatively, you can run the individual tools manually:

```bash
# Run Ruff for style, complexity, and function length
uv run ruff check eduvis tests scripts

# Run Pylint for nesting depth, module size, and duplication
uv run pylint eduvis tests scripts
```

> [!TIP]
> **Troubleshooting Pylint Crashes:** If Pylint crashes with an `astroid` error or reports bogus `wrong-import-position` errors on every file (especially common on Python 3.12+), it usually means `uv run` is falling back to an outdated global installation. Force an update of your local virtual environment by running `uv sync --all-extras` to fix this.


To see every registered element type rendered to SVG in one pass:

```bash
uv run eduvis render showcase/reference/exhaustive-element-catalog.yaml -o output/exhaustive_catalog/
```

This produces one SVG per element type (`test_number_line.svg`, `test_text_list.svg`, `test_math_grid.svg`, `test_solid_cube.svg`, … `test_solid_cylinder.svg`) — useful for checking renderer output after code changes.

---

## What EduVis Is

EduVis is **not** an SVG schema.

EduVis is a machine-readable instructional model.

It captures the structure of good tutoring — the same structure behind effective human instructors: no skipped steps, visual intuition before abstraction, confidence-building before challenge, and retrieval to lock it in long-term.

Crucially, it separates presentation (how to deliver), curriculum (what to learn), and student cognition (what is mastered) into orthogonal layers, allowing learning paths to adapt dynamically.

EduVis is to educational experiences what Markdown is to documents, Mermaid is to diagrams, and Model Context Protocol (MCP) is to context.

A specification can be rendered as SVG, PDF, slides, interactive lessons, or animated videos while preserving pedagogical intent.

---

## The Problem

Most diagram libraries describe visuals. EduVis describes **learning experiences**.

A number line in a textbook, a number line used to discover a rule, and a number line shown during a recall exercise are pedagogically different objects. They happen to look the same. Today's tools treat them identically.

```yaml
# What every library gives you
type: number_line
range: [-10, 10]
highlight: [-3, 5]
```

EduVis preserves the meaning that gets lost the moment most tools export to SVG:

```yaml
id: explore_number_line
type: number_line
placement:
  lesson_phase: explore
  memory_role: anchor
  difficulty: starter
actions:
  conceptual:
    - compare: [-3, 5]
range: [-10, 10]
```

But more importantly, EduVis describes where this element sits inside a proven teaching pattern — something no diagram library models at all.

---

## Specification Status & Tooling

This is not a theoretical schema. The placement model, element types, and LLM prompt vocabulary have been validated in real educational pipelines and are designed for production use.

The **EduVis Studio** is the primary IDE for educational design. EduVis Studio is not another YAML editor. It is a multi-projection educational IDE where text, graphs, diagnostics, and compiler views are synchronized representations of the same educational specification. Every projection is a synchronized view over the same educational specification; no projection owns the data.

A single educational specification is projected instantly into six interactive views, supported by a cross-cutting inspector:

```text
             Educational Specification (Source of Truth)
                                │
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
  Curriculum View        Storyboard View        Assessment View
  Learner Projection      Compiler View        Specification View
                                │
 ───────────────────────────────┼───────────────────────────────
                                ▼
         Universal Relationship Explorer (Cross-cutting)
```

The Studio runs entirely client-side via WebAssembly (Pyodide), providing real-time curriculum graph visualization, lesson progression storyboards, diagnostic engines, and learner mastery projections. For design specifications, refer to [docs/studio.md](docs/studio.md).

### Running the Studio IDE Locally

To run and test the Studio workspace on your local machine:

1.  **Prepare Python WASM Assets**:
    ```bash
    uv run python scripts/pack_studio.py
    ```
2.  **Start Development Server**:
    ```bash
    cd studio
    npm install
    npm run dev
    ```
    Open `http://localhost:5173` in your browser.

### Running the Standalone Live Editor (Static Playground)

For a quick, zero-install client-side playground, you can run the standalone static Live Editor directly from the `showcase/` directory:

1.  **Start the HTTP Server**:
    ```bash
    uv run python -m http.server 8000 --directory showcase/
    ```
2.  **Open the Editor**:
    Open `http://localhost:8000/editor.html` in your browser.

> [!NOTE]
> Unlike the React-based **EduVis Studio**, the Showcase Live Editor is a lightweight single-page tool. It runs in-browser by dynamically loading Pyodide and mounting your local Python files to sync engine and rendering logic changes on the fly.

## Documentation Reference Map

EduVis is fully documented in the [docs/](docs/) directory. Please refer to these resources for detailed specifications:

*   **[docs/philosophy.md](docs/philosophy.md)**: Core design principles, primitive guidelines, and architecture philosophy.
*   **[docs/architecture.md](docs/architecture.md)**: The four decoupled layers (Knowledge, Assessment, Learner State, Presentation) and schema classifications.
*   **[docs/compiler.md](docs/compiler.md)**: The **v1.0 compiler pipeline** execution context, Planners, Assemblers, and CLI compile stages.
*   **[docs/five_pillars.md](docs/five_pillars.md)**: Full reference specification for the **Five Pillars** (Elements, Actions, Relationships, Placement, Progression) and geometric solid shapes.
*   **[docs/engines.md](docs/engines.md)**: Detailed algorithms and mathematical formulas for Spaced Repetition (SM-2), Study Plan Priority Scoring, Remediation Trace Paths, and Greedy Paper Assembly.
*   **[docs/ecosystem.md](docs/ecosystem.md)**: Ecosystem framing, comparison matrix, and out-of-scope boundaries.
*   **[docs/llm_system_prompt.md](docs/llm_system_prompt.md)**: Structured prompt vocabulary for injecting EduVis schema rules directly into LLM prompts.
*   **[docs/studio.md](docs/studio.md)**: Design goals, multi-projection workspace, bidirectional editing, and local Pyodide/WASM compiler architecture for EduVis Studio.

---

## Project Structure

```text
eduvis/ (repository root)
├── eduvis/                  ← Python package source (core models, validator, compiler, renderers)
├── studio/                  ← EduVis Studio web application (React, TypeScript, Pyodide WASM)
├── docs/                    ← Conceptual, architectural, and studio documentation files
├── showcase/                ← Reference lesson files, feature catalogs, and learner state configurations
├── scripts/                 ← Build, packaging (pack_studio), and maintenance scripts
└── tests/                   ← Unit and integration test suite
```

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
