"""Smoke tests for the EduVis lesson validator."""

from eduvis.core import validate_lesson


def _lesson(**overrides):
    doc = {
      "schema_version": "0.5",
      "curriculum": {"code": "test", "topic": "T1"},
      "lesson": {"title": "Test Lesson"},
      "progression": {
          "pattern": "direct_instruction",
          "pedagogy": {},
          "phases": [{"phase": "explain"}],
      },
      "content": [
          {
              "id": "slide_1",
              "type": "text_list",
              "placement": {"lesson_phase": "explain", "memory_role": "example"},
              "items": ["Point one", "Point two"],
          }
      ],
    }
    doc.update(overrides)
    return doc


def test_valid_lesson_no_warnings():
    assert not validate_lesson(_lesson())


def test_curriculum_knowledge_model():
    # Valid model should produce no warnings
    doc = _lesson()
    doc["curriculum"] = {
        "code": "SEC-math-2027",
        "topic": "N1.6",
        "concept": "solving_linear_equations",
        "requires": ["algebraic_expressions"],
        "supports": ["simultaneous_equations"],
        "learning_outcomes": ["isolate_variable"],
        "assessment_targets": ["procedural_fluency"],
        "remediated_by": ["equation_balancing"],
    }
    assert not validate_lesson(doc)

    # Invalid concept self-requires
    doc = _lesson()
    doc["curriculum"] = {
        "code": "test",
        "topic": "T1",
        "concept": "solving_linear_equations",
        "requires": ["solving_linear_equations"],
    }
    warnings = validate_lesson(doc)
    assert any("cannot require itself" in w for w in warnings)

    # Overlapping requires and supports
    doc = _lesson()
    doc["curriculum"] = {
        "code": "test",
        "topic": "T1",
        "concept": "solving_linear_equations",
        "requires": ["algebraic_expressions"],
        "supports": ["algebraic_expressions"],
    }
    warnings = validate_lesson(doc)
    assert any("concepts cannot be in both 'requires' and 'supports'" in w for w in warnings)


def test_missing_lesson_block():
    doc = _lesson()
    del doc["lesson"]
    warnings = validate_lesson(doc)
    assert any("lesson" in w for w in warnings)


def test_missing_progression_block():
    doc = _lesson()
    del doc["progression"]
    warnings = validate_lesson(doc)
    assert any("progression" in w for w in warnings)


def test_missing_content_block():
    doc = _lesson()
    del doc["content"]
    warnings = validate_lesson(doc)
    assert any("content" in w for w in warnings)


def test_invalid_lesson_phase():
    doc = _lesson()
    doc["content"][0]["placement"]["lesson_phase"] = "not_a_phase"
    warnings = validate_lesson(doc)
    assert any("lesson_phase" in w for w in warnings)


def test_invalid_memory_role():
    doc = _lesson()
    doc["content"][0]["placement"]["memory_role"] = "bad_role"
    warnings = validate_lesson(doc)
    assert any("memory_role" in w for w in warnings)


def test_invalid_progression_pattern():
    doc = _lesson()
    doc["progression"]["pattern"] = "bad_pattern"
    warnings = validate_lesson(doc)
    assert any("pattern" in w for w in warnings)


def test_duplicate_element_ids():
    doc = _lesson()
    doc["content"].append(dict(doc["content"][0]))
    warnings = validate_lesson(doc)
    assert any("duplicate" in w for w in warnings)


def test_missing_element_id():
    doc = _lesson()
    del doc["content"][0]["id"]
    warnings = validate_lesson(doc)
    assert any("id" in w for w in warnings)


def test_missing_element_placement():
    doc = _lesson()
    del doc["content"][0]["placement"]
    warnings = validate_lesson(doc)
    assert any("placement" in w for w in warnings)


def test_confidence_first_pedagogy():
    """confidence_first: routine before starter should warn."""
    doc = _lesson()
    doc["progression"]["pattern"] = "confidence_ladder"
    doc["progression"]["pedagogy"] = {"confidence_first": True}
    doc["content"] = [
        {
            "id": "routine_1",
            "type": "text_list",
            "placement": {
                "lesson_phase": "independent_practice",
                "memory_role": "practice",
                "difficulty": "routine",
            },
            "items": ["Q1"],
        },
        {
            "id": "starter_1",
            "type": "text_list",
            "placement": {
                "lesson_phase": "independent_practice",
                "memory_role": "practice",
                "difficulty": "starter",
            },
            "items": ["Q2"],
        },
    ]
    warnings = validate_lesson(doc)
    assert any("confidence_first" in w for w in warnings)


def test_valid_curriculum_block():
    doc = _lesson()
    warnings = validate_lesson(doc)
    assert not any("curriculum" in w for w in warnings)


def test_legacy_curriculum_warning():
    doc = _lesson()
    del doc["curriculum"]
    doc["lesson"]["syllabus"] = "test"
    doc["lesson"]["topic"] = "T1"
    warnings = validate_lesson(doc)
    assert any("legacy 'lesson.syllabus' and 'lesson.topic' are deprecated" in w for w in warnings)


def test_missing_curriculum_error():
    doc = _lesson()
    del doc["curriculum"]
    warnings = validate_lesson(doc)
    assert any("ERROR: [curriculum] missing required top-level 'curriculum' block" in w for w in warnings)


def test_phase_sequence_out_of_order():
    doc = _lesson()
    doc["progression"] = {
        "pattern": "direct_instruction",
        "phases": [{"phase": "explain"}, {"phase": "guided_practice"}]
    }
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "guided_practice", "memory_role": "example"},
            "items": ["Q1"]
        },
        {
            "id": "slide_2",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "items": ["Q2"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("ERROR: [progression:sequence] element 'slide_2' has phase 'explain' which appears out of order" in w for w in warnings)


def test_progression_coverage_undeclared_phase():
    doc = _lesson()
    doc["progression"] = {
        "pattern": "direct_instruction",
        "phases": [{"phase": "explain"}]
    }
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "guided_practice", "memory_role": "example"},
            "items": ["Q1"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("ERROR: [progression:sequence] element 'slide_1' has phase 'guided_practice' which is not declared" in w for w in warnings)


def test_progression_coverage_unused_phase():
    doc = _lesson()
    doc["progression"] = {
        "pattern": "direct_instruction",
        "phases": [{"phase": "explain"}, {"phase": "guided_practice"}]
    }
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "items": ["Q1"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("WARN: [progression:coverage] phase 'guided_practice' is declared in the progression but not used" in w for w in warnings)


def test_remediation_target_future():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "hint_1",
            "type": "hint_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "relationships": {"remediation_for": ["question_1"]},
            "items": ["Step 1"]
        },
        {
            "id": "question_1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q?",
            "options": {"A": "1", "B": "2"},
            "answer": "A"
        }
    ]
    warnings = validate_lesson(doc)
    assert any("ERROR: [relationships:remediation_for] element 'hint_1' is a remediation for 'question_1' which appears after it" in w for w in warnings)


def test_remediation_target_invalid_type():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "items": ["Anchor"]
        },
        {
            "id": "hint_1",
            "type": "hint_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "relationships": {"remediation_for": ["slide_1"]},
            "items": ["Step 1"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("ERROR: [relationships:remediation_for] element 'hint_1' is a remediation but targets element 'slide_1' of type 'text_list'" in w for w in warnings)


def test_anchor_density_warning():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "anchor"},
            "items": ["A1"]
        },
        {
            "id": "slide_2",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "anchor"},
            "items": ["A2"]
        },
        {
            "id": "slide_3",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "anchor"},
            "items": ["A3"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("WARN: [pedagogy:anchor] lesson contains 3 anchor elements" in w for w in warnings)


def test_concept_connectivity_check():
    doc = _lesson()
    doc["lesson"]["concepts"] = ["concept_a", "concept_b"]
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "concepts": ["concept_a"],
            "items": ["C1"]
        },
        {
            "id": "slide_2",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "concepts": ["concept_b"],
            "items": ["C2"]
        }
    ]
    warnings = validate_lesson(doc)
    assert any("WARN: [coherence:concept] Multiple concept groups detected with no relationships connecting them" in w for w in warnings)


def test_element_registry_element_names():
    from eduvis.core.registry import ElementRegistry
    names_math = ElementRegistry.element_names(["math"])
    assert "geometry_shape" in names_math
    assert "text_list" in names_math

    names_empty = ElementRegistry.element_names([])
    assert "text_list" in names_empty
    assert "geometry_shape" not in names_empty


# ── Presentation SVG fields ───────────────────────────────────────────────────


def _lesson_with_presentation(slides_override):
    """Helper: lesson with an inline presentation block using given slides list."""
    doc = _lesson()
    doc["presentation"] = {"slides": slides_override}
    return doc


def test_presentation_svg_neither_field_is_valid():
    """A slide with no svg_ref or svg_inline is perfectly valid."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "advance": "auto"},
    ])
    warnings = validate_lesson(doc)
    assert not any("svg" in w.lower() for w in warnings)


def test_presentation_svg_ref_only_is_valid():
    """A slide with only svg_ref (non-empty string) is valid."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "svg_ref": "output/negatives/slide_1.svg"},
    ])
    warnings = validate_lesson(doc)
    assert not any("svg" in w.lower() for w in warnings)


def test_presentation_svg_inline_only_is_valid():
    """A slide with only svg_inline (valid SVG string) is valid."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "svg_inline": "<svg xmlns='http://www.w3.org/2000/svg'></svg>"},
    ])
    warnings = validate_lesson(doc)
    assert not any("svg" in w.lower() for w in warnings)


def test_presentation_svg_both_emits_warn_not_error():
    """When both svg_ref and svg_inline are set, a WARN is emitted (not an ERROR)."""
    doc = _lesson_with_presentation([
        {
            "id": "slide_1",
            "svg_ref": "output/slide_1.svg",
            "svg_inline": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        },
    ])
    warnings = validate_lesson(doc)
    svg_warnings = [w for w in warnings if "svg" in w.lower()]
    assert len(svg_warnings) == 1
    assert "WARN" in svg_warnings[0]
    assert "svg_inline" in svg_warnings[0]
    assert "takes precedence" in svg_warnings[0]
    # Must NOT be an ERROR
    assert not any(w.startswith("ERROR") and "svg" in w.lower() for w in warnings)


def test_presentation_svg_ref_empty_string_is_error():
    """An empty svg_ref string is an ERROR."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "svg_ref": ""},
    ])
    warnings = validate_lesson(doc)
    assert any("ERROR" in w and "svg_ref" in w for w in warnings)


def test_presentation_svg_inline_empty_string_is_error():
    """An empty svg_inline string is an ERROR."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "svg_inline": ""},
    ])
    warnings = validate_lesson(doc)
    assert any("ERROR" in w and "svg_inline" in w for w in warnings)


def test_presentation_svg_inline_not_starting_with_svg_tag_is_warn():
    """svg_inline that doesn't start with '<svg' emits a WARN (not ERROR)."""
    doc = _lesson_with_presentation([
        {"id": "slide_1", "svg_inline": "<!-- comment --><svg></svg>"},
    ])
    warnings = validate_lesson(doc)
    svg_warns = [w for w in warnings if "svg_inline" in w and "WARN" in w]
    assert len(svg_warns) == 1
    assert "does not appear to start with" in svg_warns[0]


def test_mcq_answer_not_in_options():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "question_1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q?",
            "options": {"A": "1", "B": "2"},
            "answer": "C"
        }
    ]
    warnings = validate_lesson(doc)
    assert any("correct answer 'C' is not a key in options dictionary" in w for w in warnings)


def test_mcq_misconceptions_not_in_options():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "question_1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q?",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "misconceptions": {"C": "misconception-code"}
        }
    ]
    warnings = validate_lesson(doc)
    assert any("maps misconception for option 'C' which is not a key in options dictionary" in w for w in warnings)


def test_remediation_block_source_question_checks():
    doc = _lesson()
    doc["content"] = [
        {
            "id": "rem_1",
            "type": "remediation_block",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "review": {
                "source_question": "nonexistent"
            },
            "remember": {
                "type": "callout_box",
                "lines": ["Remember this"]
            },
            "solve": {
                "type": "text_list",
                "items": ["Solve it"]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("references source_question 'nonexistent' which does not exist in the lesson content" in w for w in warnings)

    doc = _lesson()
    doc["content"] = [
        {
            "id": "rem_1",
            "type": "remediation_block",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "review": {
                "source_question": "question_1"
            },
            "remember": {
                "type": "callout_box",
                "lines": ["Remember this"]
            },
            "solve": {
                "type": "text_list",
                "items": ["Solve it"]
            }
        },
        {
            "id": "question_1",
            "type": "multiple_choice",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "question": "Q?",
            "options": {"A": "1", "B": "2"},
            "answer": "A"
        }
    ]
    warnings = validate_lesson(doc)
    assert any("references source_question 'question_1' which appears after it in the lesson" in w for w in warnings)

    doc = _lesson()
    doc["content"] = [
        {
            "id": "slide_1",
            "type": "text_list",
            "placement": {"lesson_phase": "explain", "memory_role": "example"},
            "items": ["Point one"]
        },
        {
            "id": "rem_1",
            "type": "remediation_block",
            "placement": {"lesson_phase": "explain", "memory_role": "practice"},
            "review": {
                "source_question": "slide_1"
            },
            "remember": {
                "type": "callout_box",
                "lines": ["Remember this"]
            },
            "solve": {
                "type": "text_list",
                "items": ["Solve it"]
            }
        }
    ]
    warnings = validate_lesson(doc)
    assert any("references source_question 'slide_1' of type 'text_list'; source_question must be an assessment element" in w for w in warnings)


def test_schema_version_validation():
    # 1. Missing version should raise a WARN
    doc = _lesson()
    del doc["schema_version"]
    warnings = validate_lesson(doc)
    assert any("WARN: [lesson:version] missing 'schema_version' field" in w for w in warnings)

    # 2. Incompatible version should raise an ERROR
    doc = _lesson()
    doc["schema_version"] = "0.4"
    warnings = validate_lesson(doc)
    assert any("ERROR: [lesson:version] unsupported schema version \"0.4\"" in w for w in warnings)

    # 3. Invalid version type should raise an ERROR
    doc = _lesson()
    doc["schema_version"] = 0.5
    warnings = validate_lesson(doc)
    assert any("ERROR: [lesson:version] 'schema_version' must be a string" in w for w in warnings)

    # 4. Valid version "0.5" should pass cleanly
    doc = _lesson()
    doc["schema_version"] = "0.5"
    warnings = validate_lesson(doc)
    assert not any("version" in w for w in warnings)
