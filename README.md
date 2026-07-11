# EduVis Schema

**An open, curriculum-aware framework and knowledge representation for learning experiences.**

EduVis describes the **educational meaning** of learning experiences — modeling curriculum graphs, lesson progression, student actions, assessment evidence, learner state, and presentation layers. Renderers and player engines translate that meaning into interactive lessons, SVG, React, Flutter, PDF, or animated video.

Inspired by the philosophy behind Markdown, Mermaid, and Model Context Protocol (MCP):

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

# Schema migration
uv run eduvis migrate showcase/lessons/ --from-ver 0.8 --to-ver 0.9

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

## Documentation Reference Map

EduVis is fully documented in the [docs/](docs/) directory. Please refer to these resources for detailed specifications:

*   **[docs/philosophy.md](docs/philosophy.md)**: Core design principles, primitive guidelines, and architecture philosophy.
*   **[docs/architecture.md](docs/architecture.md)**: The four decoupled layers (Knowledge, Assessment, Learner State, Presentation) and schema classifications.
*   **[docs/compiler.md](docs/compiler.md)**: The **v1.0 compiler pipeline** execution context, Planners, Assemblers, and CLI compile stages.
*   **[docs/five_pillars.md](docs/five_pillars.md)**: Full reference specification for the **Five Pillars** (Elements, Actions, Relationships, Placement, Progression) and geometric solid shapes.
*   **[docs/engines.md](docs/engines.md)**: Detailed algorithms and mathematical formulas for Spaced Repetition (SM-2), Study Plan Priority Scoring, Remediation Trace Paths, and Greedy Paper Assembly.
*   **[docs/ecosystem.md](docs/ecosystem.md)**: Ecosystem framing, comparison matrix, and out-of-scope boundaries.
*   **[docs/llm_system_prompt.md](docs/llm_system_prompt.md)**: Structured prompt vocabulary for injecting EduVis schema rules directly into LLM prompts.

---

## Project Status

* **Current Stable**: `v1.0.0`
* **Current Focus**: Downstream player and renderer integration, performance optimization.
* **Long-term Vision**: Canonical Pedagogical Intermediate Representation (IR) standard.

---

## Project Structure

```text
eduvis/ (repository root)
├── pyproject.toml            ← package metadata and dependencies
├── uv.lock                   ← pinned dependency versions
├── LICENSE                   ← Apache 2.0 License
├── README.md                 ← this documentation file
├── .gitignore                ← untracked files to ignore
│
├── eduvis/                   ← Python package source code
│   ├── __init__.py           ← package entrypoint & exported APIs
│   ├── __main__.py           ← entrypoint for running directly as a script
│   ├── cli.py                ← Click CLI commands implementation
│   │
│   ├── compiler/             ← EduVis-Compiler: context, stages, and compiler orchestrator
│   │   ├── __init__.py
│   │   ├── pipeline.py       ← CompilationContext & CompilerPipeline orchestrator
│   │   ├── qa_engine.py      ← compiler validation gatekeeper (QA engine)
│   │   ├── curriculum_planner.py ← compiles syllabus -> curriculum graph YAML
│   │   ├── lesson_planner.py     ← compiles concept path -> lesson YAML
│   │   ├── assessment_assembler.py ← blueprints and assembles test papers
│   │   └── presentation_compiler.py ← compiles presentation sidecars inline
│   │
│   ├── core/                 ← EduVis-Core: schema, validation, prompt vocabulary
│   │   ├── registry.py       ← ElementRegistry (specifications list + prompt docs)
│   │   ├── validator.py      ← five-pillar lesson validator
│   │   ├── prompt.py         ← format_prompt_docs() for LLM prompts
│   │   ├── curriculum.py     ← CurriculumGraph, dependency traversal, coverage analytics
│   │   ├── learner_state.py  ← LearnerState — concept/skill/misconception mastery
│   │   ├── transition_engine.py ← apply_telemetry_event() — stateless SM evidence bridge
│   │   ├── mastery_projection.py ← MasteryGraphView — curriculum graph + learner state
│   │   ├── blueprint_engine.py  ← generate_blueprint / validate_paper_coverage / assemble_paper
│   │   ├── revision_engine.py   ← get_top_concepts / get_top_misconceptions / generate_study_plan
│   │   ├── remediation_engine.py ← trace_prerequisite_failure_root / select_next_element / generate_hint
│   │   ├── spaced_repetition.py ← SM-2 scheduler: update_review_schedule / get_due_elements
│   │   ├── elements/
│   │   │   ├── generic.py    ← generic element field definitions
│   │   │   └── math.py       ← mathematics element field definitions
│   │   └── schemas/
│   │       ├── placement.py  ← schema definitions for placement (phases, roles)
│   │       ├── actions.py    ← schema definitions for actions
│   │       ├── relationships.py ← schema definitions for relationships
│   │       └── progression.py ← schema definitions for progression patterns
│   │
│   ├── renderers/
│   │   └── svg/              ← Python reference renderer (SVG output)
│   │       ├── spec_renderer.py  ← SVGSpecRenderer — YAML spec to SVG
│   │       ├── primitives.py     ← canvas constants and drawing helpers
│   │       ├── renderers_base.py ← generic element renderers
│   │       └── renderers_math/   ← mathematics element renderers
│   │
│   └── schemas/              ← pre-generated JSON Schema files packaged with the library (also for IDE validation)
│       ├── lesson.schema.json
│       ├── placement.schema.json
│       ├── actions.schema.json
│       ├── relationships.schema.json
│       ├── progression.schema.json
│       ├── learner_state.schema.json
│       ├── telemetry_event.schema.json
│       ├── assessment_paper.schema.json
│       └── paper_blueprint.schema.json
│
├── docs/                     ← Documentation files
│   ├── philosophy.md         ← core principles and primitive test rules
│   ├── architecture.md       ← orthogonal layers and schema definitions
│   ├── compiler.md           ← pipeline compiler architecture and stages reference
│   ├── five_pillars.md       ← reference specifications for the 5 pillars
│   ├── engines.md            ← algorithm reference (SM-2, Study Plan priority, remediation)
│   ├── ecosystem.md          ← scope framing and edtech comparison matrix
│   └── llm_system_prompt.md  ← generated vocabulary reference for LLMs
│
├── showcase/                 ← Live editor and showcase files
│   ├── lessons/               ← complete teaching flows (one pattern per file)
│   │   └── negative-numbers-confidence-ladder-lesson.yaml
│   ├── features/              ← one feature family per file
│   │   ├── adaptive-remediation-branching-lesson.yaml
│   │   ├── visual-elements-catalog-lesson.yaml
│   │   └── assessment-schemas-lesson.yaml
│   └── reference/             ← reference catalogs
│       ├── exhaustive-element-catalog.yaml
│       └── mixed-content-card.yaml
│
└── tests/                    ← Test suite
    ├── test_validate.py      ← validator smoke tests
    ├── test_schema_export.py ← JSON Schema export smoke tests
    └── test_compiler_pipeline.py ← compiler pipeline and stages unit tests
```


---

## Long-Term Vision

```text
Learning Intent
       ↓
EduVis-Core  (educational meaning — stable, renderer-agnostic)
  Elements · Actions · Relationships · Placement · Progression
       ↓
EduVis-Presentation  (timing, animation — renderer-specific, layered on top)
       ↓
Any target: SVG · React · Flutter · PDF · YouTube · Interactive platform
```

Just as Markdown became the standard for text, EduVis aims to become the standard for educational content — where **progression, placement, and actions are as important as the element itself**.

---

## Status

Early design. Reference implementation live in Nova Tutor (Singapore Secondary Mathematics).

Contributions and feedback welcome.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
