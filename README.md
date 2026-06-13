# EduVis Schema

**An open, curriculum-aware schema for educational content.**

EduVis describes the **educational meaning** of learning experiences — what elements are, what they do, how they relate, where they belong, and how the lesson flows. Renderers translate that meaning into SVG, Canvas, React, Flutter, PDF, or animated video.

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
uv run eduvis validate docs/showcase/lesson-negative-numbers.yaml
uv run eduvis validate docs/showcase/lesson-geometry-triangles.yaml
uv run eduvis validate docs/showcase/demo-adaptive-remediation.yaml

# Render showcase lessons to SVGs
uv run eduvis render docs/showcase/lesson-negative-numbers.yaml -o output/negatives/
uv run eduvis render docs/showcase/lesson-geometry-triangles.yaml -o output/geometry/
uv run eduvis render docs/showcase/demo-adaptive-remediation.yaml -o output/remediation/

# Utility commands
uv run eduvis docs --subjects math
uv run eduvis schema -o schemas/
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

To see every registered element type rendered to SVG in one pass:

```bash
uv run eduvis render docs/examples/renderer_test.yaml -o output/renderer_test/
```

This produces one SVG per element type (`test_number_line.svg`, `test_text_list.svg`, `test_math_grid.svg`, `test_solid_cube.svg`, … `test_solid_cylinder.svg`) — useful for checking renderer output after code changes.

---

## What EduVis Is

EduVis is **not** an SVG schema.

EduVis is a machine-readable instructional model.

It captures the structure of good tutoring — the same structure behind effective human instructors: no skipped steps, visual intuition before abstraction, confidence-building before challenge, and retrieval to lock it in long-term.

EduVis is to educational experiences what Markdown is to documents and Mermaid is to diagrams.

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
type: number_line
placement:
  lesson_phase: explore
  memory_role: anchor
  difficulty: starter
actions:
  - compare: [-3, 5]
range: [-10, 10]
```

But more importantly, EduVis describes where this element sits inside a proven teaching pattern — something no diagram library models at all.

---

## Specification Status

This is not a theoretical schema. The placement model, element types, and LLM prompt vocabulary have been validated in real educational pipelines and are designed for production use.

See the [interactive showcase](docs/showcase/) for working examples of complete lessons rendered to SVG.

---

## Two-Layer Architecture

EduVis is deliberately split into two companion specifications.

```
EduVis-Core
  ↓
EduVis-Presentation
```

### EduVis-Core

The educational meaning layer. Renderer-agnostic, stable, and the rare part.

Covers five concerns:

| Concern | What it answers |
|---|---|
| **Elements** | What content type is this? |
| **Actions** | What does this element ask the student to do? |
| **Relationships** | How does this element relate to others in the lesson? |
| **Placement** | Where does it live in the lesson and in memory? |
| **Progression** | What is the instructional flow of the whole lesson? |

### EduVis-Presentation *(companion spec, future)*

The animation and timing layer. Renderer-specific, layered on top of Core.

Covers: zoom, pan, pause, reveal sequencing, highlight animation, narration timing.

**Why the split matters:** mixing these too early produces a video animation engine, not an educational standard. The educational semantics are the rare and valuable part. Animation is comparatively easy to layer on later.

A Core spec can be rendered to a static PDF today and to a YouTube-style animated lesson tomorrow — without changing a single field.

---

## EduVis-Core

### Elements

The content types. Educational primitives, not drawing primitives.

```yaml
type: number_line
range: [-10, 10]
highlight:
  - value: -3
    label: "-3°C"
    color: blue
  - value: 3
    label: "3°C"
    color: red
direction_labels:
  left: Colder
  right: Warmer
```

`number_line`, `fact_boxes`, `multiple_choice`, `hint_list` — these are pedagogical roles, not visual shapes. See [Element Reference](#element-reference) for the full vocabulary.

---

### Actions

What the element asks the student to do — the educational intent of the interaction.

```yaml
actions:
  conceptual:
    - compare: [-3, 5]          # notice a difference between two values
    - predict: unknown          # student fills in a missing value
    - identify: misconception   # student spots the error before it is revealed
    - retrieve: rule            # student recalls without looking back
    - apply: signed-number-ordering  # student applies a rule to a new case
  procedural:
    - substitute: { from: x, to: 3 }   # step-by-step transformation
    - simplify                  # reduce an expression
    - calculate                 # perform arithmetic
    - round: { decimal_places: 2 }
```

Actions are split into two categories:

**Conceptual** — what the student does cognitively:

| Action | What it means |
|---|---|
| `compare` | Draw attention to two elements in relation |
| `predict` | Student must supply a value before it is revealed |
| `identify` | Student spots the error or pattern before explanation |
| `retrieve` | Student recalls from memory without re-reading |
| `apply` | Student applies a rule to a new case |

**Procedural** — step-by-step mathematical transformations (the no-skipped-steps principle):

| Action | What it means |
|---|---|
| `substitute` | Replace a variable or expression — one explicit step |
| `simplify` | Reduce an expression — one explicit step |
| `calculate` | Perform arithmetic — one explicit step |
| `round` | Round to a specified precision — one explicit step |

Actions are **not** animation instructions. `compare` does not mean "animate an arrow between two values." It means "this element exists to make a comparison salient." The presentation layer decides how.

Procedural actions enforce `no_skipped_steps`: every transformation is named, so an AI generator cannot collapse two steps into one and a renderer can show working line by line.

---

### Relationships

How elements relate to other elements within a lesson. Enables lesson-level coherence checking and AI lesson assembly.

```yaml
relationships:
  anchors:
    - fraction_model          # this element is the concrete anchor for the concept
  contradicts:
    - misconception_example   # this element corrects the previous one
  precedes:
    - practice_question       # this element scaffolds the next element
  reinforces:
    - hook_scenario           # this element brings back the opening memory
```

| Relationship | What it means |
|---|---|
| `anchors` | This element establishes the concrete memory anchor for a concept |
| `contradicts` | This element corrects or challenges a previous element |
| `precedes` | This element scaffolds the element that follows |
| `reinforces` | This element recalls an earlier anchor to strengthen it |
| `parallels` | Two elements show the same concept at different abstraction levels |
| `remediation_for` | This element is shown when a student fails a linked element — scaffolds a retry |

**Adaptive tutoring pattern** — the `remediation_for` relationship encodes the CHECK → HINT branching loop used in intelligent tutoring systems without requiring a separate adaptive-paths pillar:

```yaml
- id: check_prime_identification
  type: multiple_choice
  placement:
    lesson_phase: independent_practice
    memory_role: practice
    difficulty: starter
  question: Which of these is a prime number?
  options: {A: "1", B: "2", C: "4", D: "6"}

- id: hint_prime_identification
  type: hint_list
  placement:
    lesson_phase: guided_practice
    memory_role: example
    purpose: worked_example
  relationships:
    remediation_for:
      - check_prime_identification
  items:
    - "List the factors of each option"
    - "A prime has exactly two factors: 1 and itself"
  final: "Choose the number with exactly two factors"
```

The runtime reads `remediation_for` and branches: show `check_prime_identification` first; if the student answers incorrectly, show `hint_prime_identification` and retry. The progression block still declares `guided_practice` before `independent_practice` — preserving pedagogical intent regardless of document order.

---

### Placement

Where the element lives in the lesson and in long-term memory. Three independent layers.

```yaml
placement:
  # Layer 1 — Layout: where on the screen
  layout_zone: center         # center | left | right | full | bottom
  visual_weight: primary      # primary | supporting

  # Layer 2 — Pedagogical: where in the lesson
  lesson_phase: explain       # hook | explore | explain | guided_practice | independent_practice | challenge | reflect | recall
  purpose: conceptual_model   # conceptual_model | worked_example | comparison | procedure | summary
  difficulty: routine         # starter | routine | challenge  (meaningful in practice phases)

  # Layer 3 — Memory: what role in retention
  memory_role: anchor         # anchor | example | practice | misconception_fix | retrieval | review
```

**Lesson phases:**

| Phase | What it means |
|---|---|
| `hook` | Concrete scenario before the concept is named |
| `explore` | Student observes a pattern before the rule is stated |
| `explain` | Rule or concept is revealed — `conceptual_model` purpose before `procedure` |
| `guided_practice` | Instructor walks through a worked example with the student following each step |
| `independent_practice` | Student applies the concept without guidance; difficulty set by `difficulty` field |
| `challenge` | Stretch problem that extends beyond routine application |
| `reflect` | Student articulates what they learned |
| `recall` | Student retrieves without re-reading — builds long-term memory |

**Difficulty levels** (used in `independent_practice` and `challenge` phases):

| Level | What it means |
|---|---|
| `starter` | Intentionally easy — builds confidence before the concept feels hard |
| `routine` | Typical exam-style problems — the core of independent practice |
| `challenge` | Harder realistic problems or stretch questions |

**Memory roles:**

| Role | What it means |
|---|---|
| `anchor` | The one element the student should remember weeks later |
| `example` | Demonstrates the concept in a specific case |
| `practice` | Used during in-lesson application |
| `misconception_fix` | Corrects a specific common error |
| `retrieval` | Shown during a recall exercise |
| `review` | Appears in a future lesson as a spaced repetition cue |

---

### Progression

The instructional flow of the whole lesson. This is the pillar that makes EduVis more than a diagram library.

Progression operates at the **lesson level**. Placement operates at the **element level**. Together they encode the teaching pattern — not just the individual elements, but the sequence that makes learning stick.

```yaml
progression:
  pattern: confidence_ladder      # the named teaching pattern
  pedagogy:
    confidence_first: true        # begin with starter problems before routine ones
    explain_why: true             # conceptual_model purpose before procedure
    no_skipped_steps: true        # every transformation is an explicit action
  phases:
    - phase: hook
    - phase: explore
    - phase: explain
      purpose: conceptual_model
    - phase: explain
      purpose: procedure
    - phase: guided_practice
      count: 1
    - phase: independent_practice
      difficulty: starter
      count: 3
    - phase: independent_practice
      difficulty: routine
      count: 5
    - phase: challenge
      count: 1
    - phase: recall
      count: 2
```

**Named patterns:**

| Pattern | What it means |
|---|---|
| `confidence_ladder` | Hook → Explore → Explain → Guided → Starter Practice → Routine Practice → Challenge → Recall. No steps skipped, confidence built before complexity introduced. |
| `direct_instruction` | Hook → Explain → Guided → Independent Practice → Recall. Shorter sequence for procedural topics where exploration is less useful. |
| `flipped_recall` | Recall → Hook → Explore → Explain → Practice. Opens with retrieval to activate prior knowledge before new content. |

**Pedagogy flags:**

| Flag | What it means |
|---|---|
| `confidence_first` | `starter` difficulty problems appear before `routine` ones |
| `explain_why` | A `conceptual_model` element precedes the `procedure` element |
| `no_skipped_steps` | Every mathematical transformation is an explicit action |

---

## Example

A single element from the Negative Numbers lesson — `explore` phase, number line, showing two temperatures for comparison:

```yaml
- id: explore_number_line
  type: number_line
  placement:
    lesson_phase: explore
    memory_role: anchor
    difficulty: starter
  actions:
    conceptual:
      - compare: [-12, 32]
  relationships:
    anchors:
      - hook_temperature
  range: [-15, 35]
  highlight:
    - value: -12
      label: "Antarctica"
      color: blue
    - value: 32
      label: "Singapore"
      color: red
```

This element sits inside a `confidence_ladder` lesson that progresses through hook → explore → explain → guided practice → starter problems → routine problems → challenge → recall.

See [docs/showcase/lesson-negative-numbers.yaml](docs/showcase/lesson-negative-numbers.yaml) for the full lesson spec.

---

## Why the Five Pillars Matter

The insight from studying effective human tutors: the diagrams are about 20% of the value. The other 80% is the sequence.

Without EduVis, an AI lesson generator asks:

> *Draw three diagrams about negative numbers.*

With EduVis, it asks:

> *I need one `anchor` element in the `explore` phase, a `conceptual_model` before the `procedure` in the `explain` phase, one `guided_practice` worked example, three `starter` practice problems to build confidence, five `routine` problems, one `challenge`, and two `retrieval` items — following `confidence_ladder` with `explain_why` and `no_skipped_steps`.*

The generator is no longer assembling graphics. It is assembling a **learning experience** — one that follows the same structure that makes great human tutors effective.

The instructional patterns that live inside the heads of great tutors become explicit, machine-readable, and consistently reproducible. That is the gap no SVG library, diagram tool, or LLM prompt currently fills.

---

## Using with LLMs

EduVis exposes its full five-pillar vocabulary as a runtime-generated system prompt block — the same pattern MCP uses to announce tool schemas to a model.

Inject it before asking an LLM to write lesson specs:

```python
from eduvis.core import format_prompt_docs

system_prompt = f"""
You are an instructional designer writing EduVis lesson specs.
Follow the schema exactly — only use elements, phases, and actions listed below.

{format_prompt_docs(["math"])}
"""
```

Or generate it from the CLI:

```bash
python -m eduvis docs --subjects math
python -m eduvis docs --subjects math --output vocab.txt
```

The vocabulary covers all five pillars in one block: lesson skeleton, progression patterns, placement model, actions vocabulary, relationship types, and element field schemas — everything an LLM needs to produce a valid spec without guessing at field names.

**Sample output** — the block below is generated from `python -m eduvis docs --subjects math` at the current release. It is illustrative, not exhaustive; the actual output updates automatically as elements are added.

<details>
<summary>View sample LLM vocabulary (v0.1, math)</summary>

> Full reference: [docs/llm_system_prompt.md](docs/llm_system_prompt.md)

```
## EduVis Lesson Structure

Every lesson YAML has three top-level keys: lesson, progression, content.

lesson:
  syllabus: string        # curriculum code e.g. "SEC-math-2027"
  topic: string           # topic code e.g. "N1.6"
  title: string           # human-readable lesson title

progression:
  pattern: confidence_ladder | direct_instruction | flipped_recall
  pedagogy:
    confidence_first: true | false
    explain_why: true | false
    no_skipped_steps: true | false

content:
  - id: string
    type: <element_type>
    placement:
      lesson_phase: hook | explore | explain | guided_practice |
                    independent_practice | challenge | reflect | recall
      memory_role:  anchor | example | practice | misconception_fix |
                    retrieval | review
      difficulty:   starter | routine | challenge   # optional
      purpose:      conceptual_model | procedure | worked_example |
                    comparison | summary             # optional
    actions:                                        # optional
      conceptual:
        - compare: [-3, 5]
        - predict: unknown
      procedural:
        - substitute: {from: x, to: 3}
        - simplify
    relationships:                                  # optional
      anchors:         [hook_temperature]
      precedes:        [practice_starter_1]
      remediation_for: [check_element_id]
    <element-specific fields...>

## Element types (math, v0.1)
  number_line      range, highlight, direction_labels, caption
  fraction_model   shape: circle|bar|grid, total_parts, shaded_parts
  bar_model        bars: [{label, value, color}], difference
  coordinate_plane x_range, y_range, plots: [{type, equation, color}]
  geometry_shape   vertices, labels, side_labels, angles
  solid_shape      shape: cube|cone|cylinder|pyramid, dimensions, color
  factor_array     number: N
  math_grid        rows: [[cells]], headers
  text_list        items: [strings]
  fact_boxes       items: [{text, border_color}]
  example_panel    items: [{heading, body}]
  callout_box      title, lines, border_color
  summary_list     items: [strings]
  multiple_choice  question, options: {A, B, C, D}
  hint_list        items: [strings], final: string
```

</details>

---

## 3D Geometry: Solid Shapes

The `solid_shape` element renders 3D solids using isometric projection—perfect for teaching volume, surface area, and spatial reasoning.

```yaml
type: solid_shape
shape: cylinder                    # cube, rectangular_prism, pyramid, cone, cylinder, etc.
dimensions: [3, 5]                # [width, height] for cone/cylinder; [w, h, d] for prism
color: blue
label: "Volume = πr²h"            # optional label below shape
show_dimensions: true             # optional: overlay radius/height measurements on shape
```

**Supported shapes:**
- `cube` — regular cube (use single dimension: `[side]`)
- `rectangular_prism` — box with custom width, height, depth (`[w, h, d]`)
- `triangular_prism` — prism with triangular cross-section
- `pyramid` — square pyramid with apex
- `cone` — circular cone with apex (`[diameter, height]`)
- `cylinder` — circular cylinder (`[diameter, height]`)

**Features:**
- **Isometric projection** — automatic 3D perspective from 2D coordinates
- **Auto-scaling** — all shapes fit the content zone, dimensions stay proportional
- **Dimension labels** — use `show_dimensions: true` to overlay radius/height measurements (yellow text)
- **Custom labels** — `label` field renders below the shape for captions or formulas

**Cylinder improvements:**
- Darker bottom, lighter top to emphasize 3D depth
- All 16 vertical edges visible
- Bold top edge outline

See `docs/examples/renderer_test.yaml` for live examples: `test_solid_cube.svg`, `test_solid_cone.svg`, `test_solid_cylinder.svg`, etc.

---

## Python API Usage

You can easily integrate `eduvis` validation and prompt generation into your custom Python scripts and LangChain pipelines.

### Programmatic Validation
Validate lesson specs dynamically:
```python
import yaml
from eduvis.core import validate_lesson

# Load your generated lesson YAML
with open("lesson.yaml", "r") as f:
    lesson_data = yaml.safe_load(f)

# Run the five-pillar validator
warnings = validate_lesson(lesson_data)
if not warnings:
    print("Lesson is valid!")
else:
    print(f"Validation warnings: {warnings}")
```

### Programmatic LLM Vocabulary (LangChain Integration)
Retrieve the vocabulary string to inject directly into your LangChain prompt templates:
```python
from langchain_core.prompts import ChatPromptTemplate
from eduvis.core import format_prompt_docs

# Generate curriculum-specific vocab docs (e.g., for Mathematics)
eduvis_vocab = format_prompt_docs(["math"])

# Inject into LangChain Prompt Templates
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an instructional designer. Use the following EduVis schema rules:\n\n{vocab}"),
    ("human", "Generate a lesson spec for: {topic}")
])

chain = prompt | llm
# result = chain.invoke({"vocab": eduvis_vocab, "topic": "adding fractions"})
```

---

## Element Reference

**Current focus: Mathematics.**

Science and Humanities element types and renderers are planned for a future release.

> [docs/examples/renderer_test.yaml](docs/examples/renderer_test.yaml) contains one working slide per element type. Run it with `eduvis render` to get a visual catalog of every renderer.

### Generic — all subjects

| Element | Synopsis |
|---|---|
| `text_list` | `items: [strings]` |
| `fact_boxes` | `items: [{text, color}]` |
| `example_panel` | `items: [{heading, body}]` |
| `callout_box` | `title, lines, color` |
| `summary_list` | `items: [strings]` — use on closing elements |
| `multiple_choice` | `question, options: {A, B, C, D}` |
| `hint_list` | `items: [strings], final: string` |
| `number_line` | `range, highlight, direction_labels, caption` |

### Mathematics

| Element | Synopsis |
|---|---|
| `fraction_model` | `shape: circle\|bar\|grid, total_parts, shaded_parts` |
| `bar_model` | `bars: [{label, value, color}], difference` |
| `coordinate_plane` | `x_range, y_range, plots: [{type, equation, color}]` |
| `geometry_shape` | `vertices, labels, side_labels, angles` |
| `factor_array` | `number: N` — dot grid for factors and primes |
| `math_grid` | `rows: [[cells]], headers` — column arithmetic |

---

## Roadmap

### v0.1 — Core schema and SVG renderer
- Formal JSON Schema for all element types
- Placement model: all three layers, including `difficulty`
- Actions vocabulary: initial set including step-by-step transformation actions
- Progression model: named patterns and pedagogy flags
- Built-in SVG reference renderer
- Secondary Mathematics examples

### v0.2 — Relationships and curriculum metadata
- Relationships between elements within a lesson
- Curriculum tagging (`syllabus`, `topic`)
- Lesson-level coherence validation against the declared progression pattern

### v0.3 — EduVis-Presentation *(companion spec)*
- Reveal sequencing
- Narration timing hooks
- Highlight and zoom annotations
- Designed to layer cleanly over Core — no Core schema changes required

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
│   ├── core/                 ← EduVis-Core: schema, validation, prompt vocabulary
│   │   ├── registry.py       ← ElementRegistry (specifications list + prompt docs)
│   │   ├── validator.py      ← five-pillar lesson validator
│   │   ├── prompt.py         ← format_prompt_docs() for LLM prompts
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
│   └── schemas/              ← pre-generated JSON Schema files packaged with the library
│       ├── placement.schema.json
│       ├── actions.schema.json
│       ├── relationships.schema.json
│       ├── progression.schema.json
│       └── lesson.schema.json
│
├── docs/                     ← Documentation and showcase files
│   ├── llm_system_prompt.md  ← generated vocabulary reference for LLMs
│   ├── examples/
│   │   ├── mixed_card_demo.yaml   ← mixed card layout demo (decimal subtraction)
│   │   └── renderer_test.yaml     ← one slide per element type (visual catalog)
│   └── showcase/
│       ├── lesson-negative-numbers.yaml   ← canonical negative numbers spec
│       ├── lesson-geometry-triangles.yaml ← geometry shape triangles lesson spec
│       └── demo-adaptive-remediation.yaml ← adaptive remediation flow spec

│
├── schemas/                  ← pre-generated JSON Schema files at the repository root
│   ├── placement.schema.json
│   ├── actions.schema.json
│   ├── relationships.schema.json
│   ├── progression.schema.json
│   └── lesson.schema.json
│
└── tests/                    ← Test suite
    ├── test_validate.py      ← validator smoke tests
    └── test_schema_export.py ← JSON Schema export smoke tests
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
