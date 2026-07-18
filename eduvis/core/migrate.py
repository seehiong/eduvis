import re
import sys
import ruamel.yaml


_TEXT_KEYS = frozenset({
    'caption', 'body', 'text', 'final', 'question', 'heading',
    'label', 'description', 'note', 'hint', 'answer_explanation',
})


def _key_indent(indent_str: str) -> int:
    stripped = indent_str.lstrip()
    # strip leading "- " if this is a list-item key
    if stripped.startswith('- '):
        stripped = stripped[2:]
    return len(indent_str) - len(indent_str.lstrip()) + (2 if indent_str.lstrip().startswith('- ') else 0)


def _gather_continuations(lines: list[str], start: int, key_col: int) -> tuple[list[str], int]:
    parts = []
    j = start
    while j < len(lines):
        nxt = lines[j]
        if not nxt.strip():
            break
        nxt_col = len(nxt) - len(nxt.lstrip())
        if nxt_col <= key_col:
            break
        # A line that looks like a YAML key is a sibling — stop only if it is
        # at or below the key's own indentation level (not deeper continuations).
        if re.match(r'^\s+[\w][\w_]*\s*:', nxt) and not nxt.strip().startswith('-'):
            if nxt_col <= key_col:
                break
        parts.append(nxt.strip().strip('"'))
        j += 1
    return parts, j


def _check_fully_closed(lines: list[str], start_idx: int, key_col: int, quote_char: str) -> tuple[bool, int]:
    # Find the end index of the scalar
    j = start_idx + 1
    while j < len(lines):
        nxt = lines[j]
        if nxt.strip():
            nxt_col = len(nxt) - len(nxt.lstrip())
            if nxt_col <= key_col:
                break
        j += 1

    # Check if it is fully closed
    is_closed = False
    last_non_empty = j - 1
    while last_non_empty >= start_idx and not lines[last_non_empty].strip():
        last_non_empty -= 1
    if last_non_empty >= start_idx:
        last_line = lines[last_non_empty].rstrip()
        if last_line.endswith(quote_char):
            if not (len(last_line) >= 2 and last_line[-2] == '\\'):
                is_closed = True
    return is_closed, j


def _process_keyed_field(lines: list[str], i: int, m: re.Match) -> tuple[list[str], int] | None:
    indent_str = m.group(1)
    key_col = _key_indent(indent_str)
    raw_val = m.group(2)
    raw_val_stripped = raw_val.strip()

    # Skip block scalars (e.g. key: | or key: >)
    if raw_val_stripped.startswith('|') or raw_val_stripped.startswith('>'):
        return None

    # Detect fully closed quoted strings (single or double quotes)
    starts_with_quote = len(raw_val_stripped) > 0 and raw_val_stripped[0] in ('"', "'")
    if starts_with_quote:
        quote_char = raw_val_stripped[0]
        is_closed, j = _check_fully_closed(lines, i, key_col, quote_char)
        if is_closed:
            return lines[i:j], j

    # Half-quoted: starts with " but no closing " on same line
    half_quoted = bool(re.match(r'^"[^"]*$', raw_val))
    # Fully-closed quote that may have orphaned continuations
    full_closed = bool(re.match(r'^".*"$', raw_val)) and not half_quoted
    val = raw_val.strip().strip('"')
    parts = [val]
    j = i + 1

    if full_closed:
        # Check for orphaned continuation lines at deeper indentation
        cont, j2 = _gather_continuations(lines, j, key_col)
        if cont:
            parts.extend(cont)
            j = j2
    else:
        cont, j = _gather_continuations(lines, j, key_col)
        parts.extend(cont)

    combined = ' '.join(p for p in parts if p)
    needs_quote = ': ' in combined or len(parts) > 1 or half_quoted or full_closed
    if needs_quote:
        combined = combined.replace('\\', '\\\\').replace('"', '\\"')
        return [f'{indent_str}"{combined}"'], j

    return None


def _process_list_item(lines: list[str], i: int, m2: re.Match) -> tuple[list[str], int] | None:
    prefix = m2.group(1)
    rest = m2.group(2)
    # Skip if this is actually a mapping item (- key: value)
    if re.match(r'^[\w][\w_]*\s*:', rest):
        return None
    key_col = len(prefix) - 1
    val = rest
    parts = [val]
    cont, j = _gather_continuations(lines, i + 1, key_col)
    parts.extend(cont)
    combined = ' '.join(parts)
    if ': ' in combined and len(parts) > 1:
        combined = combined.replace('\\', '\\\\').replace('"', '\\"')
        return [f'{prefix}"{combined}"'], j
    return None


def _sanitize_captions(text: str) -> str:
    """
    Pre-process YAML text to collapse multi-line plain (unquoted) text
    scalars into single double-quoted strings.

    YAML plain scalars that span multiple lines are valid, but a colon
    followed by a space (': ') on any continuation line is interpreted as a
    mapping-value indicator and causes a parse error.  LLM-generated YAML
    files frequently produce this pattern in fields like caption/body/text:

        caption: Find the angle theta. Rearrange: theta equals arc times 360,
          divided by 2 pi r.

    Also handles half-quoted values where the opening " was added by a prior
    partial fix but the closing " is missing or the continuation is outside:

        caption: "SOH CAH TOA gives us three ratios: sine equals opposite,"
          cosine equals adjacent over hypotenuse.

    This function detects all such blocks across all known text-holding keys,
    collapses them to a single line, and wraps the value in double quotes.
    """
    lines = text.splitlines()
    result = []
    i = 0
    key_pat = re.compile(
        r'^(\s+(?:' + '|'.join(_TEXT_KEYS) + r'): )(.*?)$'
    )
    # List-item plain scalar: "      - Some text that may span lines"
    list_item_pat = re.compile(r'^(\s+- )(?!["\x27\-\{\[])(.+)$')

    while i < len(lines):
        line = lines[i]

        # --- keyed text fields (caption/body/text/etc.) ---
        m = key_pat.match(line)
        if m:
            res = _process_keyed_field(lines, i, m)
            if res is not None:
                res_lines, next_i = res
                result.extend(res_lines)
                i = next_i
                continue

        # --- bare list-item plain scalars spanning multiple lines ---
        else:
            m2 = list_item_pat.match(line)
            if m2:
                res = _process_list_item(lines, i, m2)
                if res is not None:
                    res_lines, next_i = res
                    result.extend(res_lines)
                    i = next_i
                    continue

        result.append(line)
        i += 1

    return '\n'.join(result) + ('\n' if text.endswith('\n') else '')


class MigrationEngine:
    def __init__(self):
        self.rules = []

    def add_rule(self, func):
        self.rules.append(func)

    def _determine_versions(self, data: dict, from_version: str | None, to_version: str) -> tuple[int, int]:
        actual_from_version = from_version
        if not actual_from_version:
            actual_from_version = data.get("schema_version")
            if not actual_from_version:
                raise ValueError("schema_version key is missing in YAML content")
            actual_from_version = str(actual_from_version)

        # Strip any quotes from actual_from_version
        actual_from_version = actual_from_version.strip('"').strip("'")

        versions = ["0.7", "0.8", "0.9", "1.0"]
        if actual_from_version not in versions or to_version not in versions:
            raise ValueError(f"Unsupported migration path from {actual_from_version} to {to_version}")

        idx_from = versions.index(actual_from_version)
        idx_to = versions.index(to_version)

        if idx_from > idx_to:
            raise ValueError(f"Downgrade from {actual_from_version} to {to_version} is not supported")

        return idx_from, idx_to

    def run(self, yaml_content: str, from_version: str | None, to_version: str) -> str:
        sanitized = _sanitize_captions(yaml_content)

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096  # prevent line-wrapping that creates multi-line single-quoted scalars
        yaml.allow_duplicate_keys = True

        try:
            data = yaml.load(sanitized)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if not from_version:
                raise ValueError(f"Error parsing YAML and from_version was not provided: {e}") from e
            print(f"Error parsing YAML: {e}", file=sys.stderr)
            # Fallback: regex bump so schema_version is never silently skipped
            bumped = re.sub(
                r'(schema_version\s*:\s*["\']?)' + re.escape(from_version) + r'(["\']?)',
                r'\g<1>' + to_version + r'\g<2>',
                sanitized,
            )
            return bumped

        if not isinstance(data, dict):
            if not from_version:
                raise ValueError("YAML root is not a dictionary; schema_version cannot be determined")
            return sanitized

        idx_from, idx_to = self._determine_versions(data, from_version, to_version)

        if idx_from == idx_to:
            return yaml_content

        versions = ["0.7", "0.8", "0.9", "1.0"]
        for i in range(idx_from, idx_to):
            v_from = versions[i]
            v_to = versions[i + 1]
            for rule in self.rules:
                rule(data, v_from, v_to)

        from io import StringIO
        buf = StringIO()
        yaml.dump(data, buf)
        return buf.getvalue()


def _migrate_marking_scheme(marking_scheme) -> None:
    if not isinstance(marking_scheme, list):
        return
    for mark in marking_scheme:
        if isinstance(mark, dict):
            for key in ("step", "depends_on"):
                if key in mark and isinstance(mark[key], int):
                    mark[key] = str(mark[key])


def _collect_elements(data: dict) -> list:
    elements = []
    for slide in data.get("slides") or []:
        if isinstance(slide, dict):
            elements.extend(slide.get("elements") or [])
    content = data.get("content")
    if isinstance(content, list):
        elements.extend(content)
    return elements


def v07_to_v08_rule(data, from_version, to_version):
    """
    Migration rule for v0.7 to v0.8.
    Converts marking_scheme step integers to strings.
    """
    if from_version != "0.7" or to_version != "0.8" or not isinstance(data, dict):
        return

    data["schema_version"] = "0.8"
    for el in _collect_elements(data):
        if isinstance(el, dict) and el.get("type") in ("short_answer", "assessment_event"):
            _migrate_marking_scheme(el.get("marking_scheme"))


def v08_to_v09_rule(data, from_version, to_version):
    """
    Migration rule for v0.8 to v0.9.
    Just bumps the schema_version property.
    """
    if from_version != "0.8" or to_version != "0.9" or not isinstance(data, dict):
        return

    data["schema_version"] = "0.9"


def v09_to_v10_rule(data, from_version, to_version):
    """
    Migration rule for v0.9 to v1.0.
    Just bumps the schema_version property.
    """
    if from_version != "0.9" or to_version != "1.0" or not isinstance(data, dict):
        return

    data["schema_version"] = "1.0"


engine = MigrationEngine()
engine.add_rule(v07_to_v08_rule)
engine.add_rule(v08_to_v09_rule)
engine.add_rule(v09_to_v10_rule)
