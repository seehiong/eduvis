"""
EduVis Core — LLM Prompt Vocabulary Generator.

Produces a complete, self-contained vocabulary block that describes the EduVis
schema to an LLM. Inject into the system prompt so the model can write valid
EduVis lesson specs without needing to infer structure from examples alone.

Usage:
    from eduvis.core.prompt import format_prompt_docs
    system_prompt = f"...\n\n{format_prompt_docs(['math'])}"
"""

from __future__ import annotations

from .registry import ElementRegistry
from .schemas.placement import (
    VALID_PHASES, VALID_MEMORY_ROLES, VALID_DIFFICULTY,
    VALID_PURPOSES, VALID_LAYOUT_ZONES, VALID_VISUAL_WEIGHTS,
)
from .schemas.actions import VALID_CONCEPTUAL, VALID_PROCEDURAL
from .schemas.relationships import VALID_TYPES as VALID_REL_TYPES
from .schemas.progression import VALID_PHASES as PROG_PHASES


def format_prompt_docs(subjects: list[str]) -> str:
    """
    Return the complete EduVis vocabulary for an LLM system prompt.

    subjects: list of subject tags to include, e.g. ["math"] or ["math", "science"].
              "*" (all subjects) is always included regardless of this argument.

    The returned string covers:
      1. Lesson skeleton  — top-level YAML structure
      2. Progression      — named patterns, pedagogy flags, phase sequence
      3. Placement        — lesson phases, memory roles, difficulty, purpose
      4. Actions          — conceptual and procedural action vocabularies
      5. Relationships    — relationship types and syntax
      6. Elements         — all element types and their field schemas
    """
    parts = [
        _lesson_skeleton(),
        _progression_docs(),
        _placement_docs(),
        _actions_docs(),
        _relationships_docs(),
        _elements_docs(subjects),
    ]
    return "\n\n".join(parts)


# ── Section builders ──────────────────────────────────────────────────────────

def _lesson_skeleton() -> str:
    return """\
## EduVis Lesson Structure

Every lesson YAML has three top-level keys: lesson, progression, content.

```yaml
lesson:
  syllabus: string        # curriculum code e.g. "SEC-math-2027"
  topic: string           # topic code e.g. "N1.6"
  title: string           # human-readable lesson title
  concepts:               # optional list of target concepts
    - string

progression:
  pattern: confidence_ladder | direct_instruction | flipped_recall
  pedagogy:
    confidence_first: true | false
    explain_why: true | false
    no_skipped_steps: true | false
  phases:
    - phase: <lesson_phase>
      purpose: <purpose>       # optional, use in explain phase
      difficulty: <difficulty> # optional, use in practice phases
      count: <integer>         # optional, number of elements in this phase

content:
  - id: string             # unique identifier within the lesson
    type: <element_type>   # see Element Types below
    concepts:              # optional list of concepts taught by this element
      - string
    placement:
      lesson_phase: <lesson_phase>
      memory_role: <memory_role>
      difficulty: <difficulty>   # optional
      purpose: <purpose>         # optional
      visual_weight: primary | supporting  # optional
      layout_zone: center | left | right | full | bottom  # optional
    actions:               # optional
      conceptual:
        - <action>: <target>
      procedural:
        - <action>
    relationships:         # optional
      <rel_type>:
        - <other_element_id>
    <element-specific fields...>
```"""


def _progression_docs() -> str:
    phases_list = " | ".join(sorted(PROG_PHASES))
    return f"""\
## Progression

### Named Patterns
  confidence_ladder   Hook -> Explore -> Explain -> Guided -> Starter Practice -> Routine Practice -> Challenge -> Recall
  direct_instruction  Hook -> Explain -> Guided -> Independent Practice -> Recall
  flipped_recall      Recall -> Hook -> Explore -> Explain -> Practice

### Pedagogy Flags
  confidence_first    starter-difficulty elements must appear before routine in content order
  explain_why         a conceptual_model element must precede any procedure element in the explain phase
  no_skipped_steps    every guided_practice element must declare at least one action

### Phase Sequence
Phases in the phases list define the intended lesson flow and the expected count of elements per phase.
Valid phase names: {phases_list}"""


def _placement_docs() -> str:
    phases = " | ".join(sorted(VALID_PHASES))
    roles = " | ".join(sorted(VALID_MEMORY_ROLES))
    difficulties = " | ".join(sorted(VALID_DIFFICULTY))
    purposes = " | ".join(sorted(VALID_PURPOSES))
    zones = " | ".join(sorted(VALID_LAYOUT_ZONES))
    weights = " | ".join(sorted(VALID_VISUAL_WEIGHTS))

    return f"""\
## Placement

Every content element MUST have a placement block with lesson_phase and memory_role.

### lesson_phase (required)
{phases}

  hook                 Concrete scenario before the concept is named
  explore              Student observes a pattern before the rule is stated
  explain              Rule or concept revealed — use purpose: conceptual_model before procedure
  guided_practice      Instructor walks through a worked example; must have at least one action
  independent_practice Student applies the concept; set difficulty accordingly
  challenge            Stretch problem beyond routine application
  reflect              Student articulates what they learned
  recall               Student retrieves without re-reading; builds long-term memory

### memory_role (required)
{roles}

  anchor               The one element the student should remember weeks later
  example              Demonstrates the concept in a specific case
  practice             Used during in-lesson application
  misconception_fix    Corrects a specific common error
  retrieval            Shown during a recall exercise
  review               Appears in a future lesson as spaced repetition

### difficulty (optional — use in independent_practice and challenge phases)
{difficulties}

  starter              Intentionally easy — builds confidence before the concept feels hard
  routine              Typical exam-style problems
  challenge            Harder realistic problems or stretch questions

### purpose (optional — use in explain phase)
{purposes}

  conceptual_model     Builds intuition before the rule is stated (always place before procedure)
  procedure            States the rule or worked algorithm explicitly
  worked_example       Shows a complete solved example
  comparison           Places two cases side-by-side
  summary              Closing recap of the lesson

### layout_zone (optional)
{zones}

### visual_weight (optional)
{weights}"""


def _actions_docs() -> str:
    conceptual = " | ".join(sorted(VALID_CONCEPTUAL))
    procedural = " | ".join(sorted(VALID_PROCEDURAL))
    return f"""\
## Actions

Actions describe what the element asks the student to do. Split into two groups.

```yaml
actions:
  conceptual:          # cognitive intent — what the student thinks or notices
    - compare: [-3, 5]                     # draw attention to a difference
    - predict: unknown                     # student supplies a missing value
    - identify: misconception              # student spots an error before it is revealed
    - retrieve: concept-name               # student recalls from memory
    - apply: concept-name                  # student applies a rule to a new case
  procedural:          # step-by-step mathematical transformations (no_skipped_steps)
    - substitute: {{from: x, to: 3}}        # replace a variable — one explicit step
    - simplify                             # reduce an expression — one explicit step
    - calculate                            # perform arithmetic — one explicit step
    - round: {{decimal_places: 2}}          # round to precision — one explicit step
```

Valid conceptual actions: {conceptual}
Valid procedural actions: {procedural}

IMPORTANT: Actions are not animation instructions. "compare" means this element
exists to make a comparison salient — the renderer decides how to show it.

IMPORTANT: When no_skipped_steps is true, every guided_practice element must
declare at least one action. Use procedural for computation steps, conceptual
for reasoning steps."""


def _relationships_docs() -> str:
    rel_types = " | ".join(sorted(VALID_REL_TYPES))
    return f"""\
## Relationships

Relationships describe how elements connect within the lesson. They enable
coherence checking and AI lesson assembly.

```yaml
relationships:
  anchors:
    - hook_temperature      # this element is the concrete anchor for the concept
  contradicts:
    - misconception_panel   # this element corrects the previous one
  precedes:
    - practice_starter_1    # this element scaffolds the next element
  reinforces:
    - explain_concept        # this element recalls an earlier anchor
  parallels:
    - abstract_version       # two elements show the same concept at different abstraction levels
```

Valid relationship types: {rel_types}

Each value is a list of element id strings. Referenced IDs must exist in the
same lesson's content list."""


def _elements_docs(subjects: list[str]) -> str:
    element_vocab = ElementRegistry.format_prompt_docs(subjects)
    subject_label = ", ".join(subjects) if subjects else "all"
    return f"""\
## Element Types (subjects: {subject_label})

Each content element requires a `type` field. The available types and their
required/optional fields are listed below.

```
{element_vocab}
```

IMPORTANT: Only use fields listed above for each element type. Do not invent fields."""
