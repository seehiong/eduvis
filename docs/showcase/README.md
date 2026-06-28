# EduVis Showcase

**A "hello world for pedagogy engines."** Four production-ready specs demonstrating the full EduVis feature surface — one clear use case per file, no duplication.

## What's Here

### Interactive Gallery: `index.html`

Open [index.html](index.html) in a browser to browse each showcase rendered slide-by-slide with its YAML spec linked.

---

## The Four Showcases

### 1. Full Lesson Flow — `lessons/negative-numbers-confidence-ladder-lesson.yaml`

**Pattern:** `confidence_ladder` | **Topic:** Negative Numbers

The canonical end-to-end lesson demo. Shows every phase of the pedagogical sequence and the richest set of element types.

| Phase | Elements used |
|---|---|
| hook | `fact_boxes` |
| explore | `number_line` |
| explain (conceptual model) | `number_line` |
| explain (procedure) | `text_list` |
| explain (comparison / misconception fix) | `example_panel` |
| guided_practice | `example_panel` |
| independent_practice (starter) | `multiple_choice` ×3, `short_answer` |
| independent_practice (routine) | `multiple_choice` ×2 |
| challenge | `multiple_choice` |
| recall | `multiple_choice` ×2 |

**Why it matters:** Shows how great tutors structure a sequence — not just slides, but a *teaching arc* with scaffolding, misconception handling, and spaced retrieval baked in.

---

### 2. Adaptive Remediation — `features/adaptive-remediation-branching-lesson.yaml`

**Pattern:** `direct_instruction` | **Topic:** Prime & Composite Numbers

Focused demo of the adaptive tutoring loop: misconception tracking → branching → targeted remediation.

| Element | Purpose |
|---|---|
| `multiple_choice` (True/False) | 2-option check |
| `multiple_choice` (5 options) | Extended option set |
| `callout_box` | Concept introduction anchor |
| `remediation_block` ×3 | Review → Remember → Solve loop |

**Why it matters:** Demonstrates how remediation is *declarative*, not imperative. The `remediation_for` relationship says "if this check fails, show this block" — the runtime branches automatically.

---

### 3. Visual Elements Catalog — `features/visual-elements-catalog-lesson.yaml`

**Pattern:** `direct_instruction` | **Topic:** Mixed (one of each element type)

One slide per element type not covered elsewhere. Reference file for all available visual primitives.

| # | Element | Variant |
|---|---|---|
| 1 | `bar_model` | comparison with difference |
| 2 | `solid_shape` | pyramid |
| 3 | `solid_shape` | cone |
| 4 | `solid_shape` | cylinder |
| 5 | `solid_shape` | cube |
| 6 | `solid_shape` | rectangular_prism |
| 7 | `coordinate_plane` | line + points |
| 8 | `fraction_model` | circle (3/4) |
| 9 | `factor_array` | composite verdict |
| 10 | `hint_list` | standalone (not inside remediation_block) |
| 11 | `math_grid` | arithmetic (column addition) |
| 12 | `math_grid` | ratio table |
| 13 | `geometry_shape` | external angle variant |

**Why it matters:** Every registered renderer has exactly one showcase entry — easy to copy-paste any element type into a new lesson.

---

### 4. Assessment Schemas — `features/assessment-schemas-lesson.yaml`

**Pattern:** `direct_instruction` | **Topic:** Algebra

Showcases the assessment annotation layer. These fields power telemetry, learner state, and mastery projection.

| Field | What it does |
|---|---|
| `assessment_objective` | Tags cognitive demand: `conceptual_understanding`, `procedural_fluency`, `problem_solving` |
| `misconceptions` | Maps each wrong option key → misconception code for targeted follow-up |
| `solution_steps` | Ordered worked solution surfaced after an attempt |
| `marking_scheme` | M-marks (method) and A-marks (accuracy) with `depends_on` chains |
| `evaluation_mode: algebraic` | Smart equivalence check so `7x+8` and `8+7x` both pass |

**Elements demonstrated:** `callout_box` (schema overview), `multiple_choice` (full annotation), `short_answer` ×2 (M/A chains at routine and challenge difficulty).

**Engine components these annotations feed:**
- `telemetry_event` — captures `learner_id`, `element_id`, `answer_submitted`, `is_correct`, `misconception_detected`
- `LearnerState` — updates concept/skill/misconception mastery on each event
- `TransitionEngine` — uses relationships + telemetry to select the next element
- `MasteryProjection` — projects readiness across the full concept map

---

## Rendered SVG Assets

```
assets/
├── negative-numbers/     # 14 slides — full lesson flow
├── adaptive-remediation/ # 8 slides — remediation loop
├── visual-elements/      # 13 slides — one per element type
└── assessment-schemas/   # 4 slides — assessment annotation showcase
```

Run `python scripts/build_showcase.py` from the workspace root to regenerate all SVGs.

---

## The Five Pillars

### 1. Elements — What content type?
```yaml
type: number_line      # pedagogical primitive, not a visual primitive
type: fact_boxes       # concrete memory anchor
type: multiple_choice  # check understanding
type: remediation_block  # adaptive tutoring loop
```

### 2. Actions — What does the student do?
```yaml
actions:
  conceptual:
    - compare: [-10, -2]
    - identify: misconception
    - apply: signed-number-ordering
  procedural:
    - calculate: "x"
```

### 3. Relationships — How do elements relate?
```yaml
relationships:
  anchors:         [hook_real_world]
  remediation_for: [check_composite_number]
  precedes:        [practice_starter_1]
  reinforces:      [explain_concept_negative]
```

### 4. Placement — Where does it live?
```yaml
placement:
  lesson_phase: guided_practice
  purpose: worked_example
  memory_role: example
  difficulty: starter
  layout_zone: center
  visual_weight: primary
  assessment_objective: procedural_fluency   # v0.7
```

### 5. Progression — What's the instructional flow?
```yaml
progression:
  pattern: confidence_ladder
  pedagogy:
    confidence_first: true
    explain_why: true
    no_skipped_steps: true
  phases:
    - phase: hook
    - phase: explore
    - phase: explain
      purpose: conceptual_model
    - phase: explain
      purpose: procedure
    - phase: guided_practice
    - phase: independent_practice
      difficulty: starter
    - phase: independent_practice
      difficulty: routine
    - phase: challenge
    - phase: recall
```

---

## Further Reading

- [EduVis Main README](../README.md) — Architecture and philosophy
- [JSON Schemas](../schemas/) — Formal validation specs for all v0.7 schemas
- [Exhaustive Element Catalog](reference/exhaustive-element-catalog.yaml) — All 21 element types in one file
