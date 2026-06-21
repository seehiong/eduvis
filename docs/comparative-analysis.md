# EduVis: Comparative Analysis & Strategic Positioning

This document evaluates the EduVis specification against established educational frameworks, adaptive learning applications, and academic ontologies. It defines what EduVis covers, what it deliberately does not cover, and establishes its boundaries to preserve its core value proposition: **a lightweight, human-readable, and portable educational specification layer**.

---

## Strategic Framing: What EduVis Is Not vs. What It Might Be

EduVis is **not** designed to compete directly with:
* **Another LMS / Student Database**: It does not track student rosters, grades, classes, or course enrollments.
* **Another Adaptive Learning Platform**: It does not run dynamic routing loops or host statistical engines (like ALEKS, Area9, Century, or Squirrel AI).
* **Another Tutoring App**: It is not a user-facing client application, chat widget, or player UI.
* **Another Knowledge Graph / Academic Ontology**: It is not a massive RDF/OWL graph representing textbook hierarchies or school systems (e.g., EduKG).

Competing head-on with established platforms is a years-long catching-up game. Instead, EduVis positions itself as **Open Educational Representation Layer (Educational Infrastructure)**:
* **HTML** $\to$ representing document structures
* **SVG** $\to$ representing visual vector graphics
* **OpenAPI** $\to$ representing API communication schemas
* **EduVis** $\to$ representing **learning experiences**

It separates pedagogical meaning from execution, acting as the standard, portable file layer that sits underneath generators, engines, players, and agents.

```
  Traditional Application: [Content + UX + Adaptive Logic + DB] (Tightly Coupled, Closed)
  
  EduVis Infrastructure:   [Knowledge Spec] + [Pedagogy Spec] + [Presentation Spec]
                           (Portable YAML Open Standard -> Decoupled Players / Agents)
```

### The Three-File Architecture

To avoid overlapping models and maintain strict separation of concerns, the EduVis ecosystem organizes its schemas into three distinct, decoupled file types:

1. **The Standalone Curriculum Graph (`curriculum.yaml`)**
   * **Role**: Defines the static map of the subject (e.g., all Secondary 1 Mathematics).
   * **Contents**: Abstract concepts, skills, misconceptions, and their prerequisite/support dependency relationships.
   * **Lifecycle**: Shared globally across multiple lessons. Updated only when the syllabus or taxonomy changes.

2. **The Lesson Specification (`lesson.yaml` / `content.yaml`)**
   * **Role**: Contains the core slides and the instructional narrative flow for a single lesson.
   * **Contents**: 
     * A `curriculum` block pointing to the relevant node in the Curriculum Graph.
     * A `progression` block defining chronological phases and pedagogical patterns.
     * A `content` block listing the pedagogical elements (e.g., number lines, MCQs, or equations).

3. **The Presentation Sidecar (`presentation.yaml`)**
   * **Role**: Companion file containing visual styling, reveal sequencing, and narration offsets.
   * **Contents**: Reveal steps, viewport zoom/pan operations, and audio narration timestamps mapped 1:1 to slide IDs in the Lesson Specification.
   * **Lifecycle**: Maintained separately by renderers and player engines to control UX without polluting the core lesson content or curriculum semantics.

---

## Market Comparison Profiles

### 1. ALEKS (Assessment and Learning in Knowledge Spaces)
* **What it does**: ALEKS is a web-based, artificially intelligent assessment and learning system. It is built on **Knowledge Space Theory (KST)**. It uses a series of questions to dynamically assess a student's exact "knowledge state" (the subset of all topics a student has mastered). It maps out the "knowledge structure"—a network of feasible states constrained by prerequisites—to determine what topics a student is "ready to learn."
* **What EduVis already covers**: 
  - **Prerequisite mapping**: The static curriculum graph (`requires` and `supports` fields in [curriculum.py](file:///c:/project/eduvis/eduvis/core/curriculum.py)) maps the relationships between concepts similar to KST's prerequisite structures.
  - **Mastery Graph Projection**: The upcoming v0.6 Mastery engine combines the static concept map and the dynamic learner state, mirroring ALEKS's concept of isolating what a student is ready to learn next.
* **What EduVis deliberately does not cover**:
  - **Bayesian inference engine**: EduVis does not implement the statistical probabilities or the algorithms used to select the next question during assessment.
  - **Closed Content Database**: ALEKS embeds its proprietary questions directly inside its engine. EduVis defines a public, standard, portable schema for elements and metadata.

### 2. Area9 Lyceum
* **What it does**: Area9 is an enterprise adaptive learning platform that focuses on "four-dimensional education" (knowledge, skills, character, meta-learning). It heavily emphasizes tracking learner confidence (asking students to rate their confidence before answering) to identify "blind spots"—cases of high confidence but incorrect answers (unconscious incompetence).
* **What EduVis already covers**:
  - **Confidence Tracking**: EduVis defines student confidence ratings in the `learner_state` schema.
  - **Misconception Mapping**: EduVis treats misconceptions as first-class citizens in the knowledge layer ([MisconceptionNode](file:///c:/project/eduvis/eduvis/core/curriculum.py#L68-L90) in [curriculum.py](file:///c:/project/eduvis/eduvis/core/curriculum.py)) and maps distractors to misconceptions in MCQs.
  - **Remediation Blocks**: Dedicated `remediation_block` elements and `remediation_for` relationships allow full-screen pedagogical intervention when a misconception or gap is detected.
* **What EduVis deliberately does not cover**:
  - **Adaptive Routing Runtime**: The actual orchestration engine that stops a lesson, plays a video, and queries the user for confidence is part of the player platform (e.g., Nova Tutor), not the EduVis file spec. EduVis provides the *specifications* for these branches, not the runtime execution loops.

### 3. Khan Academy
* **What it does**: Khan Academy organizes subjects into linear skill lists and mastery trees. Mastery levels (Attempted, Familiar, Proficient, Mastered) are calculated using a simple decay model based on recent challenge scores. It relies heavily on standard curriculum alignments (e.g., Common Core, state standards).
* **What EduVis already covers**:
  - **Learning Outcomes**: Simple outcome mapping at the lesson level (`learning_outcomes` in the `curriculum` block).
  - **Explicit Skills tagging**: Tagging elements with specific skills (`skills` list in content elements) rather than just broad concepts.
* **What EduVis deliberately does not cover**:
  - **Global Student Accounts & Progress Dashboards**: Khan Academy maintains massive web and mobile interfaces, gamified badges, and teacher dashboards. EduVis is a format, not a hosting provider.
  - **Misconception Taxonomy**: Khan Academy does not model common mathematical misconceptions as discrete nodes in its skills graph. It treats errors as simple correct/incorrect binaries.

### 4. Dynamic Learning Maps (DLM)
* **What it does**: DLM is a consortium that builds alternate assessments for students with significant cognitive disabilities. It models learning maps with thousands of nodes called "essential elements." It tracks learning at a micro-level (e.g., distinguishing between recognizing a shape, sorting shapes, and drawing a shape).
* **What EduVis already covers**:
  - **Micro-Progressions**: The `progression` block and `phases` list allow defining structured lesson paths.
  - **Action-Level Modeling**: The `actions` schema (`conceptual` vs. `procedural`) explicitly models what the student is doing with an element (e.g., `compare`, `predict`, `simplify`), avoiding vague text descriptors.
* **What EduVis deliberately does not cover**:
  - **Psychometric Calibration**: DLM maps are designed for standardized testing, employing Item Response Theory (IRT) and complex differential item functioning. EduVis focuses on instructional design and classroom/tutoring applicability.

### 5. Educational Knowledge Graphs (e.g., EduKG)
* **What it does**: Academic research projects that construct immense ontologies mapping textbooks, chapters, concepts, schools, teachers, and papers. They use Semantic Web technologies (RDF, OWL, SPARQL) and contain millions of triples.
* **What EduVis already covers**:
  - **Concept dependencies**: Core prerequisite and support relationships in a clean, queryable structure ([CurriculumGraph](file:///c:/project/eduvis/eduvis/core/curriculum.py#L113) APIs).
* **What EduVis deliberately does not cover**:
  - **Academic Ontology Complexity**: EduVis rejects the overhead of general RDF graphs. It enforces a strict, limited, instructional-first schema. If a property doesn't directly affect how a lesson is validated, structured, or rendered, it is omitted.

### 6. Knowledge Tracing Research (BKT, DKT, AKT)
* **What it does**: Academic models estimating a student's mastery over time. **Bayesian Knowledge Tracing (BKT)** uses Hidden Markov Models (updating parameters: initial mastery, transition, guess, slip). **Deep Knowledge Tracing (DKT)** uses Recurrent Neural Networks (LSTMs) to model mastery sequentially.
* **What EduVis already covers**:
  - **Assessment Evidence Bridge**: Schema parameters linking assessment events (e.g., scoring an MCQ that maps to objective `procedural_fluency` and misconception `M1.2`) to state updates.
* **What EduVis deliberately does not cover**:
  - **Parameter Fitting / ML Pipelines**: EduVis does not fit HMMs or train neural networks. It provides the standardized *telemetry schemas* and *evidence interfaces* so that any BKT/DKT engine can read an EduVis session log and update a student's profile.

---

## The Minimum Primitives Solution

To represent all educational experiences without scope creep, EduVis restricts itself to a minimal, closed set of primitive definitions. Additional complexity is represented as combinations of these primitives.

| Target Experience | How EduVis Represents It |
|---|---|
| **A Lesson** | A `lesson` definition, a `progression` pattern (e.g., `confidence_ladder`), and a sequence of `content` elements tagged with `concepts` and `placement` phases. |
| **An Assessment** | A sequence of `content` elements of type `multiple_choice` or `short_answer` tagged with `assessment_objective` and `misconceptions` mapping. |
| **A Revision Pack** | A subset of the `content` elements generated dynamically by filtering the `CurriculumGraph` based on the student's active misconceptions and weak `concepts` in their `learner_state`. |
| **An Exam-Prep Pack** | A progression utilizing the `compress` memory role and `routine` / `challenge` difficulty filters, sorted by the concept's `exam_weight`. |
| **A Mastery Graph** | A projection combining the static `CurriculumGraph` nodes (Concepts, Skills, Misconceptions) with the dynamic `learner_state` values. |
| **An AI Tutoring Session** | A player engine dynamically stepping through the `progression` phase, monitoring student answer telemetry via `check_answer()`, and branching to `remediation_block` slides if a check fails. |

### The Closed Primitive List
To prevent schema bloat and preserve clarity, the core primitives list is frozen. No consumer-facing abstractions—such as `slides`, `ai`, `tutor`, or `agent`—are permitted as core primitives; these are consumers of the specification, not the educational model itself.

The frozen set of 9 core primitives is:
1. **Concepts**: Nodes representing discrete units of understanding.
2. **Skills**: Observable tasks belonging to a concept.
3. **Misconceptions**: Common incorrect mental models associated with a concept.
4. **Actions**: What the student does (`conceptual` and `procedural`).
5. **Relationships**: How elements connect (`anchors`, `precedes`, `remediation_for`, etc.).
6. **Progressions**: Structured instructional patterns (`phases`, `pattern`, `pedagogy` flags).
7. **Assessment Objectives**: Categorizations of testing intent (`procedural_fluency`, `conceptual_understanding`, etc.).
8. **Memory Roles**: Placement metadata for long-term retention (`anchor`, `retrieval`, `review`, etc.).
9. **Presentation Semantics**: Visual advance mechanisms, viewports, reveals, and narration hooks.

### Core Principle: Educational Primitives First
Before introducing any new schema property or element type, contributors must apply the following rule:
* **The Primitive Test**: *Can this proposed element or feature be fully expressed as a combination of existing Concepts, Skills, Misconceptions, Actions, Relationships, Progressions, Assessment Objectives, or Memory Roles?*
* If **Yes**, the addition **MUST** be rejected as a new core primitive and instead modeled using the existing schema structures.

### The Risk of Overlapping Models
A significant architectural risk is that the **Curriculum Graph**, **Mastery Graph**, **Presentation**, **Assessment**, and **AI layer** become five partially overlapping models. To mitigate this risk, EduVis maintains strict separation and clean interfaces between its four orthogonal layers:
1. **Knowledge Layer** (Curriculum Graph): Pure taxonomy and concept dependencies.
2. **Assessment Layer**: Correctness rules, solution steps, and misconception detectors.
3. **Learner Layer** (Mastery Graph): Dynamic student profiles, confidence, and gaps.
4. **Presentation Layer**: Viewport panning, reveal timings, and narration.

---

## Research Priorities for v0.5 - v0.6

Before freezing the v0.5-v0.6 specification, we prioritize three research avenues to strengthen our abstractions without introducing implementation bloat.

### 1. Knowledge Tracing (Evidence Bridge Abstractions)
* **Objective**: Refine how assessment outcomes feed back into the learner state.
* **Scope**: Standardize the structure of an `assessment_event`. Ensure it contains:
  - `concept_code` and `skill_code` being tested.
  - `assessment_objective` classification.
  - `correctness` (boolean or float).
  - `misconception_detected` (string code, if triggered).
* **Boundary**: We will *not* implement BKT or DKT training algorithms in the package. The [eduvis.core.engine](file:///c:/project/eduvis/eduvis/core/engine.py) will focus strictly on deterministic checking ([check_answer](file:///c:/project/eduvis/eduvis/core/engine.py#L13-L61)()) and emitting standard structured event payloads.

### 2. Learning Progressions & Map Relationships
* **Objective**: Ensure the `relationships` schema aligns with modern educational research on learning progressions.
* **Scope**: Evaluate if we need to expand relationship tags in the `CurriculumGraph` (currently prerequisite and support). We may introduce:
  - `cognitive_leap`: Indicates a high-centrality transition that typically requires hands-on exploration.
  - `analogous_to`: Cross-domain relationships (e.g., comparing fraction partitioning to division).
* **Boundary**: Keep relationships authorable in simple lists. Avoid deep nested property graphs.

### 3. Standards Mapping
* **Objective**: Allow alignment with public school curriculums (e.g., Singapore Ministry of Education, US Common Core) without embedding specific framework logic into the engine.
* **Scope**: Update the `curriculum` metadata block to support an optional, standardized `standards` mapping array:
  ```yaml
  curriculum:
    code: "SG-SEC-MATH"
    topic: "N1.6"
    standards:
      - authority: "moe_singapore"
        code: "sec_s1_2027.n1.3"
      - authority: "common_core"
        code: "CCSS.MATH.CONTENT.6.NS.C.5"
  ```
* **Boundary**: EduVis will not host or distribute the standards databases. It simply provides the standard schema properties so that creators can index and query content via their local curriculum standards.

---

## Governance: Canonical Reference Curriculum

Schema quality is proven by modeling reality, not by adding theoretical features. To establish a baseline of truth, the governance track mandates the creation of a **Canonical Reference Curriculum** based on Secondary 1 Mathematics.

We will build, test, and validate one complete instructional chain:
```
  Curriculum Graph
        ↓
      Lesson
        ↓
    Assessment
        ↓
  Evidence Bridge
        ↓
  Learner State
        ↓
  Mastery Graph
        ↓
  Revision Path
```

This chain will be fully implemented using a real topic: **Negative Numbers**. By mapping this curriculum pathway end-to-end, we will test the expressive limits of the schema and identify areas for refinement before freezing specifications.

---

## Roadmap Freeze Policy

To protect the stability of the specification for downstream renderers and player engines:
* **Feature Freeze**: All upcoming versions (v0.8, v0.9, v2.0) are architecturally frozen. We will not add additional graph types, agent orchestration layers, curriculum marketplaces, or teacher analytics dashboards.
* **Validation Focus**: The development pipeline will shift resources away from **expansion through architecture** toward **validation through implementation**, ensuring that the existing core primitives are robust enough to cover Singapore Secondary Mathematics and similar real-world curriculums.
