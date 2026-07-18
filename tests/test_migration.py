import pytest
from eduvis.core.migrate import engine

def test_migration_v07_to_v08():
    yaml_content = """schema_version: "0.7"
slides:
  - elements:
      - type: short_answer
        marking_scheme:
          - step: 0
            depends_on: 1
          - step: "2"
            depends_on: "3"
"""
    migrated = engine.run(yaml_content, "0.7", "0.8")

    assert 'schema_version: "0.8"' in migrated
    assert "step: '0'" in migrated
    assert "depends_on: '1'" in migrated
    assert 'step: "2"' in migrated

def test_migration_skips_unrelated_versions():
    yaml_content = """schema_version: "0.9"\n"""
    migrated = engine.run(yaml_content, "0.8", "0.9")
    assert 'schema_version: "0.9"' in migrated

def test_migration_v08_to_v09():
    yaml_content = """schema_version: "0.8"
slides:
  - elements:
      - type: short_answer
        question: test question
"""
    migrated = engine.run(yaml_content, "0.8", "0.9")
    assert 'schema_version: "0.9"' in migrated
    assert 'question: test question' in migrated

def test_migration_non_dict_input():
    assert engine.run("", "0.8", "0.9") == ""
    assert engine.run("[]", "0.8", "0.9") == "[]"

def test_migration_keeps_valid_multiline_quotes():
    yaml_content = """schema_version: "0.8"
slides:
  - elements:
      - type: short_answer
        body: '1. First line.

          2. Second line: with a colon.'
"""
    migrated = engine.run(yaml_content, "0.8", "0.9")
    assert 'schema_version: "0.9"' in migrated
    assert "Second line: with a colon" in migrated

def test_migration_allows_duplicate_keys():
    yaml_content = """schema_version: "0.8"
slides:
  - placement:
      lesson_phase: explain
      memory_role: anchor
      memory_role: example
"""
    migrated = engine.run(yaml_content, "0.8", "0.9")
    assert 'schema_version: "0.9"' in migrated
    assert 'memory_role: anchor' in migrated



def test_migration_direct_multistep_chaining():
    yaml_content = """schema_version: "0.7"
slides:
  - elements:
      - type: short_answer
        marking_scheme:
          - step: 0
            depends_on: 1
"""
    migrated = engine.run(yaml_content, "0.7", "1.0")
    assert 'schema_version: "1.0"' in migrated
    assert "step: '0'" in migrated
    assert "depends_on: '1'" in migrated


def test_migration_content_v07_to_v08():
    yaml_content = """schema_version: "0.7"
content:
  - type: short_answer
    marking_scheme:
      - step: 0
        depends_on: 1
      - step: "2"
        depends_on: "3"
"""
    migrated = engine.run(yaml_content, "0.7", "0.8")

    assert 'schema_version: "0.8"' in migrated
    assert "step: '0'" in migrated
    assert "depends_on: '1'" in migrated
    assert 'step: "2"' in migrated


def test_migration_v09_to_v10():
    yaml_content = """schema_version: "0.9"
slides:
  - elements:
      - type: short_answer
        question: test question
"""
    migrated = engine.run(yaml_content, "0.9", "1.0")
    assert 'schema_version: "1.0"' in migrated
    assert 'question: test question' in migrated


def test_migration_auto_detect_success():
    # Test that leaving from_version as None automatically detects 0.7 and migrates to 1.0
    yaml_content = """schema_version: "0.7"
slides:
  - elements:
      - type: short_answer
        marking_scheme:
          - step: 0
            depends_on: 1
"""
    migrated = engine.run(yaml_content, None, "1.0")
    assert 'schema_version: "1.0"' in migrated
    assert "step: '0'" in migrated
    assert "depends_on: '1'" in migrated


def test_migration_auto_detect_no_version():
    yaml_content = """slides: []"""
    with pytest.raises(ValueError, match="schema_version key is missing in YAML content"):
        engine.run(yaml_content, None, "1.0")


def test_migration_unsupported_version():
    yaml_content = """schema_version: "0.5" """
    with pytest.raises(ValueError, match="Unsupported migration path"):
        engine.run(yaml_content, None, "1.0")


def test_migration_downgrade_error():
    yaml_content = """schema_version: "0.9" """
    with pytest.raises(ValueError, match="Downgrade from 0.9 to 0.8 is not supported"):
        engine.run(yaml_content, None, "0.8")


def test_migration_auto_detect_non_dict_error():
    with pytest.raises(ValueError, match="YAML root is not a dictionary"):
        engine.run("[]", None, "1.0")
