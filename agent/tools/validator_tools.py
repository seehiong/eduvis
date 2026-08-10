"""
Deterministic EduVis schema & pedagogy validation tools.
"""

from typing import Dict, Any, List
import yaml
from eduvis.core import validate_lesson, validate_curriculum, validate_learner_state


def validate_generated_spec(yaml_text: str, spec_type: str = "auto") -> Dict[str, Any]:
    """
    Runs EduVis Core schema and pedagogical validation against a generated spec string.
    Returns error list and validity boolean for agent feedback loop.
    """
    errors: List[str] = []
    try:
        data = yaml.safe_load(yaml_text)
        if not isinstance(data, dict):
            return {
                "is_valid": False,
                "errors": ["Generated spec is not a valid YAML dictionary."],
                "error_count": 1
            }

        if spec_type == "curriculum" or (spec_type == "auto" and "concepts" in data and "content" not in data):
            validation_errors = validate_curriculum(data)
        elif spec_type == "learner_state" or (spec_type == "auto" and "mastery" in data):
            validation_errors = validate_learner_state(data)
        else:
            validation_errors = validate_lesson(data)

        if validation_errors:
            errors.extend(validation_errors)

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "error_count": len(errors)
        }
    except Exception as err:
        return {
            "is_valid": False,
            "errors": [f"YAML parsing error: {str(err)}"],
            "error_count": 1
        }
