# RFC Template: [Schema Feature Name]

* **RFC ID**: [e.g., RFC-0001]
* **Author(s)**: [Your Name / Email]
* **Date**: [YYYY-MM-DD]
* **Status**: Draft | Proposed | Approved | Rejected | Superseded
* **Target Version**: [e.g., v0.6.0]

---

## 1. Summary
A brief 1-2 sentence description of the proposed schema change or feature.

## 2. Motivation
Why is this change necessary? What problem does it solve for lesson authors, AI generators, or renderers? What are the limitations of the current schema?

## 3. Proposed Design
Detailed specification of the changes.

* **New/Modified Fields**:
  List exact field names, types, constraints, and descriptions.
* **JSON Schema Snippet**:
  ```json
  // Show draft properties here
  ```
* **YAML Example**:
  Provide a concrete snippet showing the new field in context:
  ```yaml
  content:
    - id: sample_element
      type: number_line
      # new field here
  ```

## 4. Stability Level
What stability tier is proposed for this feature initially?
* [ ] Experimental
* [ ] Stable (requires justification for bypassing Experimental stage)

## 5. Backward Compatibility & Migration
* Does this change break existing lessons?
* If yes, what is the temporary aliasing strategy (deprecation warnings) to prevent breaks in the current minor release?
* How will the future `eduvis migrate` tool transform old documents to this new design?

## 6. Alternatives Considered
What other designs were considered, and why were they rejected?

## 7. Open Questions
Are there any unresolved design aspects or things that need further community discussion?
