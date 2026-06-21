"""Curriculum schema validation for EduVis Core."""

from __future__ import annotations

from typing import Any


def validate(curriculum: dict) -> list[str]:
    """Validate a curriculum graph block or file.

    Returns warning/error strings.
    """
    warnings: list[str] = []

    if not isinstance(curriculum, dict):
        warnings.append("ERROR: [curriculum] 'curriculum' must be a mapping")
        return warnings

    # 1. Validate schema version
    version = curriculum.get("schema_version")
    if version is not None:
        if not isinstance(version, str):
            warnings.append(
                f"ERROR: [curriculum:version] 'schema_version' must be a string, got {type(version).__name__}"
            )
        elif version != "0.5":
            warnings.append(
                f"ERROR: [curriculum:version] unsupported schema version \"{version}\". Expected \"0.5\"."
            )

    # 2. Validate top-level keys
    allowed_keys = {"schema_version", "concepts", "skills", "misconceptions", "dependencies"}
    for key in curriculum:
        if key not in allowed_keys:
            warnings.append(
                f"ERROR: [curriculum] unexpected key '{key}' in curriculum block"
            )

    # 3. Validate lists
    _validate_concepts(curriculum.get("concepts"), warnings)
    _validate_skills(curriculum.get("skills"), warnings)
    _validate_misconceptions(curriculum.get("misconceptions"), warnings)
    _validate_dependencies(curriculum.get("dependencies"), warnings)

    return warnings


def _validate_concept_item(idx: int, c: dict, warnings: list[str]) -> None:
    allowed = {"code", "name", "description", "exam_weight"}
    # Check required fields
    for req in ("code", "name"):
        if req not in c:
            warnings.append(f"ERROR: [curriculum:concepts] concepts[{idx}] missing required '{req}' field")

    # Check key types and constraints
    for key, val in c.items():
        if key not in allowed:
            warnings.append(f"ERROR: [curriculum:concepts] concepts[{idx}] unexpected key '{key}'")
            continue

        if key in ("code", "name", "description") and not isinstance(val, str):
            warnings.append(f"ERROR: [curriculum:concepts] concepts[{idx}] '{key}' must be a string")

        if key == "exam_weight":
            if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                warnings.append(f"ERROR: [curriculum:concepts] concepts[{idx}] 'exam_weight' must be a number between 0 and 1")


def _validate_concepts(concepts: Any, warnings: list[str]) -> None:
    if concepts is None:
        return
    if not isinstance(concepts, list):
        warnings.append("ERROR: [curriculum:concepts] 'concepts' must be a list")
        return

    for idx, c in enumerate(concepts):
        if not isinstance(c, dict):
            warnings.append(f"ERROR: [curriculum:concepts] concepts[{idx}] must be a mapping")
            continue
        _validate_concept_item(idx, c, warnings)


def _validate_skill_item(idx: int, s: dict, warnings: list[str]) -> None:
    allowed = {"code", "name", "concept", "exam_weight"}
    # Check required fields
    for req in ("code", "name", "concept"):
        if req not in s:
            warnings.append(f"ERROR: [curriculum:skills] skills[{idx}] missing required '{req}' field")

    # Check key types and constraints
    for key, val in s.items():
        if key not in allowed:
            warnings.append(f"ERROR: [curriculum:skills] skills[{idx}] unexpected key '{key}'")
            continue

        if key in ("code", "name", "concept") and not isinstance(val, str):
            warnings.append(f"ERROR: [curriculum:skills] skills[{idx}] '{key}' must be a string")

        if key == "exam_weight":
            if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                warnings.append(f"ERROR: [curriculum:skills] skills[{idx}] 'exam_weight' must be a number between 0 and 1")


def _validate_skills(skills: Any, warnings: list[str]) -> None:
    if skills is None:
        return
    if not isinstance(skills, list):
        warnings.append("ERROR: [curriculum:skills] 'skills' must be a list")
        return

    for idx, s in enumerate(skills):
        if not isinstance(s, dict):
            warnings.append(f"ERROR: [curriculum:skills] skills[{idx}] must be a mapping")
            continue
        _validate_skill_item(idx, s, warnings)


def _validate_misconception_item(idx: int, m: dict, warnings: list[str]) -> None:
    allowed = {"code", "name", "concept", "remediation_weight"}
    # Check required fields
    for req in ("code", "name", "concept"):
        if req not in m:
            warnings.append(f"ERROR: [curriculum:misconceptions] misconceptions[{idx}] missing required '{req}' field")

    # Check key types and constraints
    for key, val in m.items():
        if key not in allowed:
            warnings.append(f"ERROR: [curriculum:misconceptions] misconceptions[{idx}] unexpected key '{key}'")
            continue

        if key in ("code", "name", "concept") and not isinstance(val, str):
            warnings.append(f"ERROR: [curriculum:misconceptions] misconceptions[{idx}] '{key}' must be a string")

        if key == "remediation_weight":
            if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                warnings.append(f"ERROR: [curriculum:misconceptions] misconceptions[{idx}] 'remediation_weight' must be a number between 0 and 1")


def _validate_misconceptions(misconceptions: Any, warnings: list[str]) -> None:
    if misconceptions is None:
        return
    if not isinstance(misconceptions, list):
        warnings.append("ERROR: [curriculum:misconceptions] 'misconceptions' must be a list")
        return

    for idx, m in enumerate(misconceptions):
        if not isinstance(m, dict):
            warnings.append(f"ERROR: [curriculum:misconceptions] misconceptions[{idx}] must be a mapping")
            continue
        _validate_misconception_item(idx, m, warnings)


def _validate_dependency_item(idx: int, d: dict, warnings: list[str]) -> None:
    allowed = {"from", "to", "type"}
    # Check required fields
    for req in ("from", "to"):
        if req not in d:
            warnings.append(f"ERROR: [curriculum:dependencies] dependencies[{idx}] missing required '{req}' field")

    # Check key types and constraints
    for key, val in d.items():
        if key not in allowed:
            warnings.append(f"ERROR: [curriculum:dependencies] dependencies[{idx}] unexpected key '{key}'")
            continue

        if key in ("from", "to") and not isinstance(val, str):
            warnings.append(f"ERROR: [curriculum:dependencies] dependencies[{idx}] '{key}' must be a string")

        if key == "type":
            if val not in ("prerequisite", "support"):
                warnings.append(f"ERROR: [curriculum:dependencies] dependencies[{idx}] 'type' must be 'prerequisite' or 'support'")


def _validate_dependencies(dependencies: Any, warnings: list[str]) -> None:
    if dependencies is None:
        return
    if not isinstance(dependencies, list):
        warnings.append("ERROR: [curriculum:dependencies] 'dependencies' must be a list")
        return

    for idx, d in enumerate(dependencies):
        if not isinstance(d, dict):
            warnings.append(f"ERROR: [curriculum:dependencies] dependencies[{idx}] must be a mapping")
            continue
        _validate_dependency_item(idx, d, warnings)
