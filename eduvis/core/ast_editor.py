"""EduVis Core — AST-Preserving YAML Editor.

Uses ruamel.yaml to perform formatting-preserving, round-trip edits
on curriculum and lesson specification YAMLs.
"""

import ruamel.yaml


def _load_yaml(yaml_text: str):
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.allow_duplicate_keys = True
    try:
        data = yaml.load(yaml_text)
    except Exception as e:
        raise ValueError(f"Failed to parse YAML content: {e}") from e
    return yaml, data


def _dump_yaml(yaml, data) -> str:
    from io import StringIO
    buf = StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()


def add_dependency_in_place(yaml_text: str, from_code: str, to_code: str) -> str:
    """Appends a prerequisite dependency between two concepts to the dependencies list."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    if "dependencies" not in data or data["dependencies"] is None:
        data["dependencies"] = ruamel.yaml.comments.CommentedSeq()

    dependencies = data["dependencies"]
    if not isinstance(dependencies, list):
        raise ValueError("'dependencies' key must be a list")

    # Check if this prerequisite relationship already exists
    exists = False
    for item in dependencies:
        if (
            isinstance(item, dict)
            and item.get("from") == from_code
            and item.get("to") == to_code
            and item.get("rel_type") == "prerequisite"
        ):
            exists = True
            break

    if not exists:
        new_dep = ruamel.yaml.comments.CommentedMap()
        new_dep["from"] = from_code
        new_dep["to"] = to_code
        new_dep["rel_type"] = "prerequisite"
        dependencies.append(new_dep)

    return _dump_yaml(yaml, data)


def remove_dependency_in_place(yaml_text: str, from_code: str, to_code: str) -> str:
    """Removes a prerequisite dependency between two concepts from the dependencies list."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    if "dependencies" in data and isinstance(data["dependencies"], list):
        dependencies = data["dependencies"]
        to_remove = []
        for item in dependencies:
            if (
                isinstance(item, dict)
                and item.get("from") == from_code
                and item.get("to") == to_code
                and item.get("rel_type") == "prerequisite"
            ):
                to_remove.append(item)

        for item in to_remove:
            dependencies.remove(item)

    return _dump_yaml(yaml, data)


def update_node_in_place(yaml_text: str, node_type: str, code: str, updates: dict) -> str:
    """Finds a concept, skill, or misconception by code and merges field updates."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    plural_map = {
        "concept": "concepts",
        "skill": "skills",
        "misconception": "misconceptions",
    }
    list_key = plural_map.get(node_type)
    if not list_key:
        raise ValueError(f"Invalid node_type '{node_type}'")

    if list_key not in data or not isinstance(data[list_key], list):
        raise ValueError(f"List key '{list_key}' is missing or not a list in YAML content")

    found = False
    for item in data[list_key]:
        if isinstance(item, dict) and item.get("code") == code:
            found = True
            for k, v in updates.items():
                if k in ("exam_weight", "remediation_weight") and v is not None:
                    try:
                        item[k] = float(v)
                    except (ValueError, TypeError):
                        item[k] = v
                else:
                    item[k] = v
            break

    if not found:
        raise ValueError(f"Node of type '{node_type}' with code '{code}' not found")

    return _dump_yaml(yaml, data)


def reorder_slides_in_place(yaml_text: str, ordered_slide_ids: list[str]) -> str:
    """Reorders the slides/elements in the lesson content block in-place."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    if "content" not in data or not isinstance(data["content"], list):
        raise ValueError("'content' list is missing or invalid in lesson YAML")

    content_list = data["content"]
    item_map = {}
    for item in content_list:
        if isinstance(item, dict) and "id" in item:
            item_map[str(item["id"])] = item

    new_order = []
    for sid in ordered_slide_ids:
        if sid in item_map:
            new_order.append(item_map[sid])

    # Append any elements that were not matched or don't have ids
    for item in content_list:
        if item not in new_order:
            new_order.append(item)

    # Mutate in-place to preserve comments on the list itself
    content_list.clear()
    for item in new_order:
        content_list.append(item)

    return _dump_yaml(yaml, data)


def update_slide_phase_in_place(yaml_text: str, slide_id: str, new_phase: str) -> str:
    """Updates the lesson_phase of a slide inside the content block in-place."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    if "content" not in data or not isinstance(data["content"], list):
        raise ValueError("'content' list is missing or invalid in lesson YAML")

    found = False
    for item in data["content"]:
        if isinstance(item, dict) and str(item.get("id")) == slide_id:
            found = True
            if "placement" not in item or item["placement"] is None:
                item["placement"] = ruamel.yaml.comments.CommentedMap()
            item["placement"]["lesson_phase"] = new_phase
            break

    if not found:
        raise ValueError(f"Slide with id '{slide_id}' not found in lesson content")

    return _dump_yaml(yaml, data)


def _apply_slide_updates(item: dict, updates: dict) -> None:
    for k, v in updates.items():
        if k.startswith("placement."):
            sub_key = k.split(".")[1]
            if "placement" not in item or item["placement"] is None:
                item["placement"] = ruamel.yaml.comments.CommentedMap()
            item["placement"][sub_key] = v
        elif k == "range":
            if isinstance(v, list) and len(v) == 2:
                item["range"] = [int(v[0]), int(v[1])]
        else:
            item[k] = v


def update_slide_in_place(yaml_text: str, slide_id: str, updates: dict) -> str:
    """Finds a slide by ID in the content list and merges field updates, preserving comments."""
    yaml, data = _load_yaml(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    if "content" not in data or not isinstance(data["content"], list):
        raise ValueError("'content' list is missing or invalid in lesson YAML")

    found = False
    for item in data["content"]:
        if isinstance(item, dict) and str(item.get("id")) == slide_id:
            found = True
            _apply_slide_updates(item, updates)
            break

    if not found:
        raise ValueError(f"Slide with id '{slide_id}' not found in lesson content")

    return _dump_yaml(yaml, data)
