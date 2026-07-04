# EduVis: Ecosystem Positioning & Scope

This document defines how EduVis positions itself within the educational technology space, maps its relationships to other system types, and establishes its out-of-scope boundaries.

---

## Strategic Framing

EduVis is an **Educational Intermediate Representation (Educational IR)** for curriculum, lessons, assessments, learner state, and presentation. 

Instead of being a full-stack application, EduVis serves as the **open standard representation layer** (infrastructure) that sits underneath educational tools. Just as HTML describes text documents and OpenAPI describes API contracts, EduVis describes **learning experiences**. It enables AI content systems, authoring tools, and adaptive tutoring platforms to interoperate by exchanging validated, portable specifications.

---

## Positioning & Comparison

The following matrix maps how EduVis compares to and complements other categories of educational technology:

| System Category | Core Focus | EduVis Positioning |
|---|---|---|
| **Learning Management Systems (LMS)** | Student rosters, class management, grading, and course delivery. | **Not an LMS**. EduVis is a format. It does not track student accounts or host school rosters. |
| **Adaptive Learning Platforms** | Runtimes that execute dynamic student routing and host diagnostic algorithms (e.g. ALEKS, Area9). | **Engine-agnostic specification**. EduVis provides the structured content schemas (remediation blocks, prerequisite maps) that adaptive engines read to make decisions. |
| **Educational Knowledge Graphs** | Giant Triple Stores mapping entire textbooks, papers, and academic ontologies (e.g. EduKG). | **Lightweight instructional graph**. EduVis restricts itself to a minimal taxonomy (Concepts, Skills, Misconceptions) optimized for lesson rendering and validation. |
| **Knowledge Tracing Research** | Statistical inference models (BKT, DKT) estimating student mastery over time. | **Telemetry & evidence contracts**. EduVis defines standardized assessment event schemas so that any tracking model can ingest session telemetry. |
| **AI Content & Agent Frameworks** | Multi-agent generation pipelines that produce visual explanations and custom slides (e.g. EduVisAgent). | **Stable IR contract**. Instead of agents passing fragile, unstructured natural language prompts, they exchange validated EduVis schema files. |

---

## Out of Scope (Boundaries)

To preserve its value as a portable file layer, the core EduVis specification deliberately excludes:

* **Student Information Systems (SIS)**: Roster management, school scheduling, grades, and rosters.
* **Analytics Dashboards**: Teacher portals, reporting interfaces, or school analytics.
* **AI Orchestrator Execution**: Prompt configurations, agent communication loops, or LLM runtime pipelines (these reside in generator clients, not the stateless core library).
* **Adaptive Routing Runtimes**: The dynamic loops that decide when to show a slide (this is deferred to player runtimes like Nova Tutor).
