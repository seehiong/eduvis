# EduVis Showcase

**A "hello world for pedagogy engines."** Three complete, production-ready lesson specs that demonstrate the five pillars of EduVis in action.

## What's Here

### Interactive Gallery: `index.html`

Open [index.html](index.html) in a browser to see:
- **What EduVis solves** (30-second pitch)
- **The five pillars** visual summary
- **Two complete lessons** rendered slide-by-slide with YAML specs linked
- **Misconception + remediation pattern** showing adaptive tutoring

### Three Lesson Showcase Specs

All validated and rendered to SVG.

#### 1. **Negative Numbers** (`lesson-negative-numbers.yaml`)
- **Syllabus:** showcase
- **Pattern:** `confidence_ladder` (the go-to for most topics)
- **14 elements:** hook → explore → explain (why + how) → guided practice → starter problems → routine problems → challenge → recall
- **Key feature:** Addresses a specific misconception (students confusing digit magnitude with negative number ordering) explicitly before independent practice

**Why this lesson matters:** It shows the full pedagogical structure. Not just slides, but a *teaching sequence* that follows how effective tutors actually teach.

#### 2. **Adaptive Remediation** (`demo-adaptive-remediation.yaml`)
- **Syllabus:** showcase
- **Pattern:** `direct_instruction` (focused flow)
- **6 elements:** Setup → guided example → CHECK (student gets it wrong) → HINT (remediation) → explanation + visual anchor
- **Key feature:** Uses the `remediation_for` relationship to encode intelligent tutoring system (ITS) branching

**Why this lesson matters:** Shows how adaptive tutoring is *declarative*, not imperative. The spec says "if student fails CHECK, show HINT" without explicit if/then logic. The runtime reads the relationship and branches.

#### 3. **Geometry Triangles** (`lesson-geometry-triangles.yaml`)
- **Syllabus:** showcase
- **Pattern:** `confidence_ladder`
- **12 elements:** hook → explore (geometry triangle) → explain (why + how) → guided practice → starter problems → routine problems → challenge → recall
- **Key feature:** Renders geometric polygons with annotations (vertices, side labels, and angle measures) using `geometry_shape`

**Why this lesson matters:** Demonstrates the placement and alignment of complex vector shapes inside a pedagogical progression ladder.

## Rendered SVG Outputs

The showcase lessons are rendered to individual SVGs (one per element):

```
assets/
├── negative-numbers/       # 14 slides from the negative numbers lesson
└── adaptive-remediation/   # 6 slides from the remediation demo
```


Open any `.html` and browse the rendered gallery. Each slide shows:
- The EduVis element type (`number_line`, `fact_boxes`, `example_panel`, etc.)
- The pedagogical intent (element's ID and placement: phase, purpose, memory role)
- The rendered SVG

## The Five Pillars in These Specs

### 1. **Elements** — What content type?
```yaml
- type: number_line      # pedagogical primitive, not visual primitive
- type: fact_boxes       # concrete anchor
- type: multiple_choice  # check understanding
- type: hint_list        # remediation scaffold
```

### 2. **Actions** — What does the student do?
```yaml
actions:
  conceptual:
    - compare: [-10, -2]           # notice a difference
    - identify: misconception      # spot the error before it's revealed
    - apply: signed-number-ordering # apply the rule to new case
  procedural:
    - substitute: {from: x, to: 3}  # step-by-step transformation
```

### 3. **Relationships** — How do elements relate?
```yaml
relationships:
  anchors:              # this element establishes the memory anchor
    - hook_real_world
  remediation_for:      # if student fails this CHECK, show this HINT
    - check_misconception
  precedes:             # this scaffolds the next element
    - practice_starter_1
```

### 4. **Placement** — Where does it live?
```yaml
placement:
  lesson_phase: guided_practice     # when in the lesson
  purpose: worked_example           # what role does it play
  memory_role: example              # long-term memory: anchor, example, practice, etc.
  difficulty: starter               # in practice phases: starter, routine, challenge
  layout_zone: center               # on screen: center, left, right, full, bottom
  visual_weight: primary            # visual hierarchy: primary, supporting
```

### 5. **Progression** — What's the instructional flow?
```yaml
progression:
  pattern: confidence_ladder        # the named teaching sequence
  pedagogy:
    confidence_first: true          # easy before hard
    explain_why: true               # conceptual_model before procedure
    no_skipped_steps: true          # every transformation is explicit
  phases:
    - phase: hook                   # concrete scenario
    - phase: explore                # student observes pattern
    - phase: explain                # rule is revealed
      purpose: conceptual_model
    - phase: explain
      purpose: procedure
    - phase: guided_practice        # instructor walks through
    - phase: independent_practice   # student applies
      difficulty: starter           # easy first
    - phase: independent_practice
      difficulty: routine           # typical exam-style
    - phase: challenge              # stretch beyond routine
    - phase: recall                 # retrieval without re-reading
```

## The Gap EduVis Fills

### Without EduVis (today):
> *"Draw three diagrams about negative numbers."*

AI lesson generators produce slides. They don't know that:
- The first slide should anchor memory
- The second should let students discover the pattern
- The third should scaffold before practice
- Some misconceptions need explicit identification
- Retrieval without re-reading builds long-term memory

### With EduVis:
> *"I need: one anchor in the explore phase, a conceptual_model before the procedure in the explain phase, one guided_practice worked example, three starter practice problems, five routine problems, one challenge, and two retrieval items — following confidence_ladder with explain_why and no_skipped_steps."*

The generator now assembles a **learning experience**, not just graphics. The sequence that makes great human tutors effective becomes explicit, machine-readable, and consistently reproducible.

## Using These Specs

### For AI Lesson Generators
Inject the vocabulary into your LLM system prompt:

```python
from eduvis.core import format_prompt_docs

system_prompt = f"""
You are an instructional designer writing EduVis lesson specs.
Follow the schema exactly — only use elements, phases, and actions listed below.

{format_prompt_docs(["math"])}
"""
```

The output is curriculum-aware: you get the exact field names, valid values, and a brief explanation of each pillar.

### For Renderers
Parse any spec and render to your target format:

```python
import yaml
from eduvis.core import validate_lesson

with open("lesson-negative-numbers.yaml") as f:
    lesson = yaml.safe_load(f)

warnings = validate_lesson(lesson)
if not warnings:
    # Render to SVG, React, Flutter, PDF, video, etc.
    # The spec is the source of truth.
    render_to_your_format(lesson)
```

### For Researchers
Study how great lessons are structured. The specs capture:
- How expert tutors scaffold confidence
- Which misconceptions are worth explicit attention
- How remediation is encoded
- How memory is reinforced through spaced retrieval

## Roadmap

- **v0.1** (now): Core schema, SVG renderer, Secondary Mathematics
- **v0.2** (now): Relationships between elements within a lesson, lesson-level coherence validation
- **v0.3** (now): Presentation spec (reveal sequencing, narration timing, zoom/pan, viewport commands)

## Further Reading

- [EduVis Main README](../README.md) — Full architecture and philosophy
- [JSON Schemas](../schemas/) — Formal validation specs
- [LLM Vocabulary Reference](../docs/llm_system_prompt.md) — Generated prompt docs

---

**Status:** Early design. Reference implementation under development for Singapore Secondary Mathematics.

Contributions and feedback welcome.
