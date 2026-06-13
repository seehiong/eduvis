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
```

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
Valid phase names: challenge | explain | explore | guided_practice | hook | independent_practice | recall | reflect

## Placement

Every content element MUST have a placement block with lesson_phase and memory_role.

### lesson_phase (required)
challenge | explain | explore | guided_practice | hook | independent_practice | recall | reflect

  hook                 Concrete scenario before the concept is named
  explore              Student observes a pattern before the rule is stated
  explain              Rule or concept revealed — use purpose: conceptual_model before procedure
  guided_practice      Instructor walks through a worked example; must have at least one action
  independent_practice Student applies the concept; set difficulty accordingly
  challenge            Stretch problem beyond routine application
  reflect              Student articulates what they learned
  recall               Student retrieves without re-reading; builds long-term memory

### memory_role (required)
anchor | example | misconception_fix | practice | retrieval | review

  anchor               The one element the student should remember weeks later
  example              Demonstrates the concept in a specific case
  practice             Used during in-lesson application
  misconception_fix    Corrects a specific common error
  retrieval            Shown during a recall exercise
  review               Appears in a future lesson as spaced repetition

### difficulty (optional — use in independent_practice and challenge phases)
challenge | routine | starter

  starter              Intentionally easy — builds confidence before the concept feels hard
  routine              Typical exam-style problems
  challenge            Harder realistic problems or stretch questions

### purpose (optional — use in explain phase)
comparison | conceptual_model | procedure | summary | worked_example

  conceptual_model     Builds intuition before the rule is stated (always place before procedure)
  procedure            States the rule or worked algorithm explicitly
  worked_example       Shows a complete solved example
  comparison           Places two cases side-by-side
  summary              Closing recap of the lesson

### layout_zone (optional)
bottom | center | full | left | right

### visual_weight (optional)
primary | supporting

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
    - substitute: {from: x, to: 3}        # replace a variable — one explicit step
    - simplify                             # reduce an expression — one explicit step
    - calculate                            # perform arithmetic — one explicit step
    - round: {decimal_places: 2}          # round to precision — one explicit step
```

Valid conceptual actions: apply | compare | identify | predict | retrieve
Valid procedural actions: calculate | round | simplify | substitute

IMPORTANT: Actions are not animation instructions. "compare" means this element
exists to make a comparison salient — the renderer decides how to show it.

IMPORTANT: When no_skipped_steps is true, every guided_practice element must
declare at least one action. Use procedural for computation steps, conceptual
for reasoning steps.

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

Valid relationship types: anchors | contradicts | parallels | precedes | reinforces | remediation_for

Each value is a list of element id strings. Referenced IDs must exist in the
same lesson's content list.

## Element Types (subjects: math)

Each content element requires a `type` field. The available types and their
required/optional fields are listed below.

```
  text_list       items: [strings]  (optional color per item)
                  items (required): array  # List of bullet strings; prefix 'no-bullet:' to suppress bullet
                  color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white  # Override bullet color for all items
                  anchor (optional): start|middle|center, default: start  # Text alignment
  fact_boxes      items: [{text, border_color}]
                  items (required, array):  # List of fact box dicts
                    - text: string  # Fact box content
                    - border_color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white  # Box border colour
  example_panel   items: [{heading, body}]  — side-by-side comparison panels
                  items (required, array):  # List of panel dicts (max 3 for readability)
                    - heading: string  # Bold panel title
                    - body: string  # Panel body; use \n for explicit line breaks
  callout_box     title, lines: [strings], border_color — highlighted callout
                  title (optional): string  # Bold callout heading
                  lines (required): array  # Body text lines
                  border_color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white, default: cyan
  summary_list    items: [strings]  — identical to text_list, use on summary/takeaway slides
                  items (required): array  # Summary bullet strings
                  PREFER summary_list on final slides to signal lesson wrap-up.
  multiple_choice question: string, options: {key: text}  — MCQ layout (2 to 5 options)
                  question (required): string  # The MCQ stem
                  options (required): object  # A mapping of option keys (e.g. A, B or A, B, C, D, E) to their text
                  answer (required): string  # The correct option key
                  student_answer (optional): string  # Optional student selection for review screens
                  correct_answer (optional): string  # Optional correct answer key for review screens
  hint_list       items: [strings], final: string  — numbered hints
                  items (required): array  # Hint steps (auto-numbered unless item starts with a digit or 'Step')
                  final (optional): string  # Confirmation method shown in a box at the bottom
  number_line     range: [min, max], highlight: [{value, label, color}]  — annotated number line
                  range (required): array  # [min, max] numeric bounds
                  highlight (optional, array):  # List of {value, label, color} highlight markers
                    - value: number  # Position on the line
                    - label (optional): string
                    - color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white
                    - type (optional): jump  # 'jump' draws a curved hop arrow
                  direction_labels (optional, object):  # {left: 'Smaller', right: 'Larger'} axis end labels
                    left (optional): string
                    right (optional): string
                  caption (optional): string  # Title above the line
  mixed_card      ribbon_type: solve|remember|review, ribbon_label: string, items: [{type: text|math_grid, ...}] — mixed card
                  ribbon_type (optional): solve|remember|review, default: solve
                  ribbon_label (optional): string
                  items (required, array):  # List of sub-elements to render within the card
                    - type: text|math_grid
                    - lines (optional): array
                    - mode (optional): string
                    - rows (optional): array
                    - headers (optional): array
                    - row_colors (optional): array
  remediation_block review: {source_question, student_answer, correct_answer}, remember: {type, ...}, solve: {type, ...} — remediation block
                  review (required, object):  # Shows the question context and answers
                    source_question: string
                    student_answer (optional): string
                    correct_answer (optional): string
                  remember (required): object  # The conceptual anchor element definition (e.g. callout_box, fact_boxes, number_line)
                  solve (required): object  # The step-by-step solution element definition (e.g. hint_list, text_list, math_grid)
  fraction_model  shape: circle|bar|grid, total_parts, shaded_parts, color, label
                  shape (optional): circle|bar|grid, default: circle  # Visual representation style
                  total_parts (required): integer  # Total number of equal parts
                  shaded_parts (required): integer  # Number of shaded (coloured) parts
                  color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white, default: green
                  label (optional): string  # Caption below the model; defaults to 'shaded/total'
  bar_model       bars: [{label, value, color}], difference: {label, color} (optional)
                  bars (required, array):  # Comparison bars — list of bar dicts
                    - label: string  # Bar label; include units here e.g. 'Friend A = $5.00'
                    - value: number  [!]MUST be a plain number — WRONG: "$5.00"  RIGHT: 5
                    - color: red|green|blue|yellow|cyan|orange|purple|grey|white
                  difference (optional, object):  # Bracket showing the gap between two bars
                    label: string
                    color: red|green|blue|yellow|cyan|orange|purple|grey|white
                  IMPORTANT: bar value MUST be a plain number, not a formatted string.
  coordinate_plane x_range, y_range, grid_step, plots: [{type, equation|coord, color}]
                  x_range (required): array  # [min, max] for the x-axis
                  y_range (required): array  # [min, max] for the y-axis
                  grid_step (optional): integer, default: 1  # Grid line interval
                  plots (optional, array):  # List of line or point plot specs
                    - type: line|point
                    - equation (optional): string  # Linear equation e.g. 'y=2x+1' (line only)
                    - coord (optional): array  # [x, y] coordinate (point only)
                    - label (optional): string
                    - color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white
  geometry_shape  vertices: [[x,y],...], labels, side_labels, angles — polygon with annotations
                  vertices (required): array  # List of [x, y] coordinate pairs defining the polygon
                  labels (optional): array  # Vertex label strings or {text, position, offset, anchor} dicts (one per vertex)
                  side_labels (optional, array):  # [{edge: 'AB', label: '5 cm'}] — label for each named edge
                    - edge: string  # Two-letter vertex pair e.g. 'AB'
                    - label: string  # Text shown at the midpoint of the edge
                  angles (optional, array):  # [{vertex: 'A', arc: true, label: '90°'}] — angle annotations
                    - vertex: string  # Vertex label where the angle sits
                    - sides (optional): array  # Optional list of two vertex labels specifying custom bounding sides for the angle (useful for external angles)
                    - arc (optional): any  # Draw arc if true (defaults to square for 90° angles); use 'square' to force square right-angle indicator
                    - label (optional): string  # Angle measure label e.g. '90°'
                  edges (optional): array  # Optional list of edge connections between vertex labels (e.g. ['AB', 'BC'] or [['A', 'B']]). If specified, renders separate lines instead of a single closed polygon.
  factor_array    number: N — draws N as a dot rectangle (concrete->pictorial for factors/primes)
                  number (required): integer  # The whole number to represent as a dot array
                  rows (optional): integer  # Override row count; omit to auto-pick most-square factor pair
                  cols (optional): integer  # Override column count; must be paired with rows
                  caption (optional): string  # Label below array; defaults to 'N = rows × cols'
                  color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white, default: green
                  verdict (optional): boolean, default: False  # If true, adds 'Prime / Composite / neither' label
                  PREFER factor_array over example_panel whenever a slide teaches factors or primes.
                  verdict: true adds an automatic Prime / Composite / neither label.
  math_grid       rows: [[cells],...], headers: [strings] — column arithmetic or ratio grid
                  mode (optional): arithmetic|ratio, default: arithmetic  # 'arithmetic' (default) for column place-value grids with operators; 'ratio' for ratio tables showing A : B (: C …) per row with colon separators
                  rows (required): array  # List of rows; each row is a list of cell values. In arithmetic mode, the string 'line' draws a separator. To render an operator (e.g. +, -), place it as the first cell of the row (e.g. ['+', '2', '0']).
                  headers (optional): array  # Optional column header labels
                  row_colors (optional): array  # Per-row color names (same length as data rows)
                  show_grid (optional): boolean, default: True  # If true (default), draws grid boxes around digit cells in arithmetic mode. If false, hides the boxes but keeps alignment.
                  In arithmetic mode, place the operator (+, -, ×, ÷) as the first cell of the operator row (e.g. ['+', '2', '0']) so that it renders next to the digits without a border box.
  fraction_equation terms: [strings|objects] — horizontal math equation featuring vertical fractions
                  terms (required): array  # List of terms in the equation. Each term can be a string (e.g. '1/5', '+', '3/5', '=', '4/5', '2 1/5') or an object with properties: val, color, bold, placeholder
  solid_shape     shape: cube|rectangular_prism|triangular_prism|pyramid|cone|cylinder, dimensions, color, label
                  shape (optional): cube|rectangular_prism|triangular_prism|pyramid|cone|cylinder, default: cube  # 3D shape type
                  dimensions (optional): array, default: [3, 3, 3]  # [width, height, depth] — if 1 value given, used for all; if 2 given, third defaults to second
                  color (optional): red|green|blue|yellow|cyan|orange|purple|grey|white, default: blue
                  label (optional): string  # Measurement label below the shape (e.g. '5 cm' or '5×3×2 cm³')
                  show_dimensions (optional): boolean, default: False  # If true, renders dimension measurements on the shape (radius, height, etc.)
                  All shapes use isometric projection for consistent 3D perspective.
                  Dimensions are auto-scaled to fit the content zone.
                  For a cube, pass dimensions: [side] or dimensions: [5].
                  For a rectangular prism, pass dimensions: [width, height, depth].
                  show_dimensions: true renders radius/height labels for cones and cylinders, useful for volume/surface area lessons.
```

IMPORTANT: Only use fields listed above for each element type. Do not invent fields.