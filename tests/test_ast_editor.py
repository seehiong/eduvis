from eduvis.core.ast_editor import (
    add_dependency_in_place,
    remove_dependency_in_place,
    update_node_in_place,
    reorder_slides_in_place,
    update_slide_phase_in_place,
    update_slide_in_place,
)

def test_add_dependency_in_place():
    yaml_text = """# Curriculum comment
schema_version: "1.0"
concepts:
  - code: "concept_a"
    name: "Concept A"
# Dependencies comment
dependencies: []
"""
    result = add_dependency_in_place(yaml_text, "concept_a", "concept_b")
    assert "# Curriculum comment" in result
    assert "# Dependencies comment" in result
    assert "from: concept_a" in result
    assert "to: concept_b" in result
    assert "rel_type: prerequisite" in result


def test_remove_dependency_in_place():
    yaml_text = """schema_version: "1.0"
dependencies:
  - from: "concept_a"
    to: "concept_b"
    rel_type: "prerequisite"
  - from: "concept_c"
    to: "concept_d"
    rel_type: "prerequisite"
"""
    result = remove_dependency_in_place(yaml_text, "concept_a", "concept_b")
    assert "concept_c" in result
    assert "concept_a" not in result


def test_update_node_in_place():
    yaml_text = """schema_version: "1.0"
concepts:
  - code: "concept_a"
    name: "Old Name"
    exam_weight: 0.5 # keep weight
"""
    result = update_node_in_place(
        yaml_text,
        "concept",
        "concept_a",
        {"name": "New Name", "exam_weight": "0.75", "description": "New description"},
    )
    assert "New Name" in result
    assert "exam_weight: 0.75" in result
    assert "# keep weight" in result
    assert "description: New description" in result


def test_reorder_slides_in_place():
    yaml_text = """schema_version: "1.0"
content:
  - id: slide_1 # slide 1
    type: fact_boxes
  - id: slide_2 # slide 2
    type: multiple_choice
"""
    result = reorder_slides_in_place(yaml_text, ["slide_2", "slide_1"])
    assert "slide_2" in result
    assert "# slide 1" in result

    # slide_2 should now come before slide_1
    idx_1 = result.index("id: slide_1")
    idx_2 = result.index("id: slide_2")
    assert idx_2 < idx_1


def test_update_slide_phase_in_place():
    yaml_text = """schema_version: "1.0"
content:
  - id: slide_1
    type: fact_boxes
    placement:
      lesson_phase: hook
"""
    result = update_slide_phase_in_place(yaml_text, "slide_1", "explain")
    assert "lesson_phase: explain" in result
    assert "lesson_phase: hook" not in result


def test_update_slide_in_place():
    yaml_text = """schema_version: "1.0"
content:
  - id: slide_1 # slide 1
    type: fact_boxes
    placement:
      lesson_phase: hook
"""
    result = update_slide_in_place(yaml_text, "slide_1", {
        "id": "slide_new",
        "placement.lesson_phase": "explain",
        "placement.visual_weight": "secondary",
        "range": [1, 20],
        "question": "Q?",
    })
    assert "id: slide_new" in result
    assert "lesson_phase: explain" in result
    assert "visual_weight: secondary" in result
    assert "range:\n  - 1\n  - 20" in result or "range: [1, 20]" in result
    assert "question: Q?" in result
    assert "# slide 1" in result
