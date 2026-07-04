# EduVis: Design Philosophy & Principles

This document outlines the core educational and technical design principles behind the EduVis specification. These principles guide schema development, validator checks, and the overall system architecture.

---

## Core Design Principles

To build a resilient and scalable standard for educational content, EduVis adheres to the following core principles:

1. **Separate Pedagogy from Execution**
   The educational meaning (e.g. why an element exists, what cognitive skill it assesses, where it fits in a retrieval progression) must be decoupled from the target rendering medium (e.g. SVG, interactive React components, PDFs, or slides).
   
2. **Separate Static Specifications from Runtime State**
   Static specifications represent the content, topics, and structures as authored (e.g., `curriculum.yaml`, `lesson.yaml`). Session-transient data, such as student mastery, confidence, and logs (e.g., `learner_state.json`), must live in separate dynamic models and sidecars.

3. **Prefer Composition Over New Primitives**
   To avoid schema bloat, new or complex learning experiences should be modeled by composing existing primitives rather than introducing ad-hoc schemas or new primitive definitions.

4. **Keep Schemas Human-Readable and Authorable**
   Specifications are designed to be easily read, written, and maintained by teachers, instructional designers, and content generators in simple YAML format.

5. **Validate Educational Structure Before Rendering**
   A curriculum or lesson's pedagogical integrity (e.g., progression sequence order, misconception loops, concept bottlenecks) must be statically checked and validated before content is compiled or delivered.

6. **Enable Multi-System Orchestration via Shared IR**
   Positioning EduVis as a Pedagogical Intermediate Representation (IR) allows diverse authoring tools, AI generators, and learning platforms to interoperably compile and consume the standard specifications.

---

## Educational Primitives First

EduVis restricts itself to a minimal, closed set of primitive definitions to model all educational content. Any new feature proposal must pass the **Primitive Test** before being accepted into the schema.

### The Primitive Test
> *Can this proposed element or feature be fully expressed as a combination of existing Concepts, Skills, Misconceptions, Actions, Relationships, Progressions, Assessment Objectives, or Memory Roles?*
> 
> If **Yes**, the addition **MUST** be rejected as a new core primitive and instead modeled using the existing structures.

### The Frozen Core Primitives
The core schema is built entirely from these 9 primitives:

1. **Concepts**: Nodes representing discrete units of understanding.
2. **Skills**: Observable learning outcomes belonging to a concept.
3. **Misconceptions**: Common incorrect mental models associated with a concept.
4. **Actions**: What the student does (`conceptual` and `procedural` verbs).
5. **Relationships**: How elements connect (`anchors`, `precedes`, `remediation_for`, etc.).
6. **Progressions**: Structured instructional patterns (`phases`, `pattern`, `pedagogy` flags).
7. **Assessment Objectives**: Categorizations of testing intent (`procedural_fluency`, `conceptual_understanding`, etc.).
8. **Memory Roles**: Placement metadata for long-term retention (`anchor`, `retrieval`, `review`, etc.).
9. **Presentation Semantics**: Viewport panning, reveal timings, and narration hooks.
