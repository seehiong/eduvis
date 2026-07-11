# EduVis: The Five Pillars of Educational Content Specification

This document provides the reference specification for the **Five Pillars** of the EduVis educational content schema: **Elements**, **Actions**, **Relationships**, **Placement**, and **Progression**.

---

## 1. Elements

Elements represent **educational primitives**, not drawing primitives. A `number_line` or `fraction_model` is defined by its pedagogical role and parameters rather than raw SVG coordinates.

```yaml
id: temperature_comparison
type: number_line
placement:
  lesson_phase: explore
  memory_role: example
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

---

## 2. Actions

Actions represent what the element asks the student to do—the educational intent of the interaction.

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

### Conceptual (Cognitive Verbs)

| Action | What it means |
| :--- | :--- |
| `compare` | Draw attention to two elements in relation. |
| `predict` | Student must supply a value before it is revealed. |
| `identify` | Student spots the error or pattern before explanation. |
| `retrieve` | Student recalls from memory without re-reading. |
| `apply` | Student applies a rule to a new case. |

### Procedural (Mathematical Transformations)

| Action | What it means |
| :--- | :--- |
| `substitute` | Replace a variable or expression (one explicit step). |
| `simplify` | Reduce an expression (one explicit step). |
| `calculate` | Perform arithmetic (one explicit step). |
| `round` | Round to a specified precision (one explicit step). |

> [!NOTE]
> Actions are **not** animation instructions. `compare` does not mean "animate an arrow between two values." It means "this element exists to make a comparison salient." The presentation layer decides how.
>
> Procedural actions enforce the **no-skipped-steps** principle: every transformation is named, so an AI generator cannot collapse two steps into one and a renderer can show working line-by-line.

---

## 3. Relationships

Relationships define how elements connect to other elements within a lesson. This enables lesson-level coherence checking and AI lesson assembly.

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
| :--- | :--- |
| `anchors` | This element establishes the concrete memory anchor for a concept. |
| `contradicts` | This element corrects or challenges a previous element. |
| `precedes` | This element scaffolds the element that follows. |
| `reinforces` | This element recalls an earlier anchor to strengthen it. |
| `parallels` | Two elements show the same concept at different abstraction levels. |
| `remediation_for` | This element is shown when a student fails a linked element — scaffolds a retry. |

---

## 4. Placement

Placement defines where the element lives in the lesson layout, layout flow, and in long-term memory.

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

### Lesson Phases

| Phase | What it means |
| :--- | :--- |
| `hook` | Concrete scenario before the concept is named. |
| `explore` | Student observes a pattern before the rule is stated. |
| `explain` | Rule or concept is revealed — `conceptual_model` purpose before `procedure`. |
| `guided_practice` | Instructor walks through a worked example with the student following each step. |
| `independent_practice` | Student applies the concept without guidance; difficulty set by `difficulty` field. |
| `challenge` | Stretch problem that extends beyond routine application. |
| `reflect` | Student articulates what they learned. |
| `recall` | Student retrieves without re-reading — builds long-term memory. |

### Memory Roles

| Role | What it means |
| :--- | :--- |
| `anchor` | The one element the student should remember weeks later. |
| `example` | Demonstrates the concept in a specific case. |
| `practice` | Used during in-lesson application. |
| `misconception_fix` | Corrects a specific common error. |
| `retrieval` | Shown during a recall exercise. |
| `review` | Appears in a future lesson as a spaced repetition cue. |

---

## 5. Progression

Progression operates at the **lesson level**, defining the overall instructional flow of the lesson. Together with placement, it encodes the teaching pattern.

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

### Named Patterns

| Pattern | What it means |
| :--- | :--- |
| `confidence_ladder` | Hook $\rightarrow$ Explore $\rightarrow$ Explain $\rightarrow$ Guided $\rightarrow$ Starter Practice $\rightarrow$ Routine Practice $\rightarrow$ Challenge $\rightarrow$ Recall. |
| `direct_instruction` | Hook $\rightarrow$ Explain $\rightarrow$ Guided $\rightarrow$ Independent Practice $\rightarrow$ Recall. Shorter procedural sequence. |
| `flipped_recall` | Recall $\rightarrow$ Hook $\rightarrow$ Explore $\rightarrow$ Explain $\rightarrow$ Practice. Opens with retrieval to activate prior knowledge. |

---

## 6. 3D Geometry: Solid Shapes Spec

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
*   `cube` — regular cube (use single dimension: `[side]`)
*   `rectangular_prism` — box with custom width, height, depth (`[w, h, d]`)
*   `triangular_prism` — prism with triangular cross-section
*   `pyramid` — square pyramid with apex
*   `cone` — circular cone with apex (`[diameter, height]`)
*   `cylinder` — circular cylinder (`[diameter, height]`)

---

## 7. Element Schema Reference Matrix

### Generic elements (All Subjects)

| Element | Synopsis |
| :--- | :--- |
| `text_list` | `items: [strings]` |
| `fact_boxes` | `items: [{text, color}]` |
| `example_panel` | `items: [{heading, body}]` |
| `callout_box` | `title, lines, color` |
| `summary_list` | `items: [strings]` — use on closing elements |
| `multiple_choice` | `question, options: {A, B, C, D}` |
| `short_answer` | `question, answer, evaluation_mode` |
| `remediation_block` | `review: {source_question}, remember: {type, ...}, solve: {type, ...}` |
| `hint_list` | `items: [strings], final: string` |
| `number_line` | `range, highlight, direction_labels, caption` |
| `mixed_card` | `ribbon_type: solve\|remember\|review, ribbon_label, items: [{type, ...}]` |

### Mathematics Specific

| Element | Synopsis |
| :--- | :--- |
| `fraction_model` | `shape: circle\|bar\|grid, total_parts, shaded_parts` |
| `bar_model` | `bars: [{label, value, color}], difference` |
| `coordinate_plane` | `x_range, y_range, plots: [{type, equation, color}]` |
| `geometry_shape` | `vertices, labels, side_labels, angles` |
| `factor_array` | `number: N` — dot grid for factors and primes |
| `math_grid` | `rows: [[cells]], headers` — column arithmetic |
| `fraction_equation` | `terms: [strings\|objects]` — vertical fractions equation layout |
| `solid_shape` | `shape: cube\|prism\|pyramid\|cone\|cylinder, dimensions, color, label` |
