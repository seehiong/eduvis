"""EduVis — Curriculum Graph and Knowledge Engine.

Provides static representation, traversal, completeness validation, importance weighting,
and coverage/dependency gap analytics for curriculum structures.
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import collections
import os
from typing import Any

import yaml


class ConceptNode:
    """Represents a concept in the curriculum taxonomy."""

    def __init__(
        self,
        code: str,
        name: str,
        description: str = "",
        exam_weight: float = 1.0,
    ) -> None:
        self.code = str(code).strip()
        self.name = str(name).strip()
        self.description = str(description).strip()
        self.exam_weight = float(exam_weight)
        self.centrality_weight = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "exam_weight": self.exam_weight,
            "centrality_weight": self.centrality_weight,
        }


class SkillNode:
    """Represents a skill belonging to a concept in the curriculum taxonomy."""

    def __init__(
        self,
        code: str,
        name: str,
        concept: str,
        exam_weight: float = 1.0,
    ) -> None:
        self.code = str(code).strip()
        self.name = str(name).strip()
        self.concept = str(concept).strip()
        self.exam_weight = float(exam_weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "concept": self.concept,
            "exam_weight": self.exam_weight,
        }


class MisconceptionNode:
    """Represents a misconception associated with a concept in the curriculum taxonomy."""

    def __init__(
        self,
        code: str,
        name: str,
        concept: str,
        remediation_weight: float = 1.0,
    ) -> None:
        self.code = str(code).strip()
        self.name = str(name).strip()
        self.concept = str(concept).strip()
        self.remediation_weight = float(remediation_weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "concept": self.concept,
            "remediation_weight": self.remediation_weight,
        }


class DependencyEdge:
    """Represents a dependency relationship between concepts."""

    def __init__(
        self,
        from_concept: str,
        to_concept: str,
        rel_type: str = "prerequisite",
    ) -> None:
        self.from_concept = str(from_concept).strip()
        self.to_concept = str(to_concept).strip()
        self.rel_type = str(rel_type).strip().lower()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_concept,
            "to": self.to_concept,
            "type": self.rel_type,
        }


class CurriculumGraph:
    """Manages the curriculum graph including taxonomy nodes and dependencies."""

    def __init__(self) -> None:
        self.concepts: dict[str, ConceptNode] = {}
        self.skills: dict[str, SkillNode] = {}
        self.misconceptions: dict[str, MisconceptionNode] = {}
        self.dependencies: list[DependencyEdge] = []

    def _parse_concepts(self, data: dict[str, Any]) -> None:
        concepts_list = data.get("concepts") or []
        if isinstance(concepts_list, list):
            for c in concepts_list:
                if isinstance(c, dict) and "code" in c and "name" in c:
                    node = ConceptNode(
                        code=c["code"],
                        name=c["name"],
                        description=c.get("description", ""),
                        exam_weight=c.get("exam_weight", 1.0),
                    )
                    self.concepts[node.code] = node

    def _parse_skills(self, data: dict[str, Any]) -> None:
        skills_list = data.get("skills") or []
        if isinstance(skills_list, list):
            for s in skills_list:
                if isinstance(s, dict) and "code" in s and "name" in s and "concept" in s:
                    node = SkillNode(
                        code=s["code"],
                        name=s["name"],
                        concept=s["concept"],
                        exam_weight=s.get("exam_weight", 1.0),
                    )
                    self.skills[node.code] = node

    def _parse_misconceptions(self, data: dict[str, Any]) -> None:
        misconceptions_list = data.get("misconceptions") or []
        if isinstance(misconceptions_list, list):
            for m in misconceptions_list:
                if isinstance(m, dict) and "code" in m and "name" in m and "concept" in m:
                    node = MisconceptionNode(
                        code=m["code"],
                        name=m["name"],
                        concept=m["concept"],
                        remediation_weight=m.get("remediation_weight", 1.0),
                    )
                    self.misconceptions[node.code] = node

    def _parse_dependencies(self, data: dict[str, Any]) -> None:
        dependencies_list = data.get("dependencies") or []
        if isinstance(dependencies_list, list):
            for d in dependencies_list:
                if isinstance(d, dict) and "from" in d and "to" in d:
                    edge = DependencyEdge(
                        from_concept=d["from"],
                        to_concept=d["to"],
                        rel_type=d.get("type", "prerequisite"),
                    )
                    self.dependencies.append(edge)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CurriculumGraph:
        """Create a CurriculumGraph instance from a dictionary representation."""
        graph = cls()
        if not isinstance(data, dict):
            return graph

        graph._parse_concepts(data)
        graph._parse_skills(data)
        graph._parse_misconceptions(data)
        graph._parse_dependencies(data)

        # Compute centrality weights automatically on load
        graph.compute_centrality()
        return graph

    @classmethod
    def load_from_yaml(cls, filepath: str) -> CurriculumGraph:
        """Load curriculum graph structure from a YAML file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Curriculum file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def compute_centrality(self) -> None:
        """Calculate the graph centrality weight for all concepts.

        Centrality is calculated as the count of all transitive downstream
        prerequisite descendants divided by (total_concepts - 1).
        """
        if not self.concepts:
            return

        # Build forward prerequisite adjacency list (A -> B means A is prerequisite for B)
        adj: dict[str, set[str]] = {code: set() for code in self.concepts}
        for edge in self.dependencies:
            if edge.rel_type == "prerequisite":
                if edge.from_concept in adj and edge.to_concept in self.concepts:
                    adj[edge.from_concept].add(edge.to_concept)

        total_nodes = len(self.concepts)
        denom = float(total_nodes - 1) if total_nodes > 1 else 1.0

        for code, node in self.concepts.items():
            # Find all reachable descendants using BFS/DFS
            visited: set[str] = set()
            queue = collections.deque([code])
            while queue:
                curr = queue.popleft()
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            descendants_count = len(visited)
            node.centrality_weight = round(descendants_count / denom, 4)

    def analyze_centrality(self) -> list[dict[str, Any]]:
        """Return concept centrality analysis sorted by centrality_weight descending."""
        results = []
        total_nodes = len(self.concepts)
        denom = float(total_nodes - 1) if total_nodes > 1 else 1.0

        for node in self.concepts.values():
            downstream_count = int(round(node.centrality_weight * denom))
            results.append({
                "code": node.code,
                "name": node.name,
                "centrality_weight": node.centrality_weight,
                "downstream_count": downstream_count,
            })
        return sorted(results, key=lambda x: x["centrality_weight"], reverse=True)

    def get_prerequisites(self, concept_code: str, transitive: bool = False) -> list[str]:
        """Query direct or transitive prerequisites for a given concept."""
        if concept_code not in self.concepts:
            return []

        # Build reverse adjacency list (B depends on A -> A is prerequisite of B)
        # We want to find nodes A that lead to concept_code
        rev_adj: dict[str, set[str]] = {code: set() for code in self.concepts}
        for edge in self.dependencies:
            if edge.rel_type == "prerequisite":
                if edge.from_concept in self.concepts and edge.to_concept in self.concepts:
                    rev_adj[edge.to_concept].add(edge.from_concept)

        if not transitive:
            return sorted(list(rev_adj.get(concept_code, set())))

        visited: set[str] = set()
        queue = collections.deque([concept_code])
        while queue:
            curr = queue.popleft()
            for parent in rev_adj.get(curr, []):
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
        return sorted(list(visited))

    def get_dependents(self, concept_code: str, transitive: bool = False) -> list[str]:
        """Query concepts that directly or transitively depend on this concept."""
        if concept_code not in self.concepts:
            return []

        # Build forward adjacency list
        adj: dict[str, set[str]] = {code: set() for code in self.concepts}
        for edge in self.dependencies:
            if edge.rel_type == "prerequisite":
                if edge.from_concept in self.concepts and edge.to_concept in self.concepts:
                    adj[edge.from_concept].add(edge.to_concept)

        if not transitive:
            return sorted(list(adj.get(concept_code, set())))

        visited: set[str] = set()
        queue = collections.deque([concept_code])
        while queue:
            curr = queue.popleft()
            for child in adj.get(curr, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return sorted(list(visited))

    def get_skills(self, concept_code: str) -> list[str]:
        """Get all skills belonging to the given concept."""
        return sorted([
            skill.code for skill in self.skills.values()
            if skill.concept == concept_code
        ])

    def get_misconceptions(self, concept_code: str) -> list[str]:
        """Get all misconceptions associated with the given concept."""
        return sorted([
            m.code for m in self.misconceptions.values()
            if m.concept == concept_code
        ])

    def find_path(self, from_concept: str, to_concept: str) -> list[str] | None:
        """Find a directed prerequisite path from from_concept to to_concept."""
        if from_concept not in self.concepts or to_concept not in self.concepts:
            return None
        if from_concept == to_concept:
            return [from_concept]

        # Forward adjacency list
        adj: dict[str, set[str]] = {code: set() for code in self.concepts}
        for edge in self.dependencies:
            if edge.rel_type == "prerequisite":
                if edge.from_concept in self.concepts and edge.to_concept in self.concepts:
                    adj[edge.from_concept].add(edge.to_concept)

        # BFS for shortest path
        queue = collections.deque([[from_concept]])
        visited = {from_concept}
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == to_concept:
                return path
            for neighbor in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def _validate_references(self, errors: list[str]) -> None:
        # Validate skills refer to defined concepts
        for skill in self.skills.values():
            if skill.concept not in self.concepts:
                errors.append(
                    f"ERROR: Skill '{skill.code}' refers to undefined concept '{skill.concept}'"
                )

        # Validate misconceptions refer to defined concepts
        for m in self.misconceptions.values():
            if m.concept not in self.concepts:
                errors.append(
                    f"ERROR: Misconception '{m.code}' refers to undefined concept '{m.concept}'"
                )

        # Validate dependencies refer to defined concepts
        for edge in self.dependencies:
            if edge.from_concept not in self.concepts:
                errors.append(
                    f"ERROR: Dependency references undefined source concept '{edge.from_concept}'"
                )
            if edge.to_concept not in self.concepts:
                errors.append(
                    f"ERROR: Dependency references undefined target concept '{edge.to_concept}'"
                )

    def _has_cycle_dfs(
        self,
        curr: str,
        adj: dict[str, set[str]],
        visited: dict[str, int],
        path: list[str],
        errors: list[str],
    ) -> bool:
        visited[curr] = 1
        path.append(curr)
        for neighbor in adj.get(curr, []):
            if visited[neighbor] == 1:
                cycle_str = " -> ".join(path[path.index(neighbor):] + [neighbor])
                errors.append(f"ERROR: Dependency cycle detected: {cycle_str}")
                return True
            if visited[neighbor] == 0:
                if self._has_cycle_dfs(neighbor, adj, visited, path, errors):
                    return True
        path.pop()
        visited[curr] = 2
        return False

    def _detect_cycles(self, errors: list[str]) -> None:
        # Detect cycles in prerequisite relationships
        adj: dict[str, set[str]] = {code: set() for code in self.concepts}
        for edge in self.dependencies:
            if edge.rel_type == "prerequisite":
                if edge.from_concept in adj and edge.to_concept in self.concepts:
                    adj[edge.from_concept].add(edge.to_concept)

        visited: dict[str, int] = {code: 0 for code in self.concepts}  # 0=unvisited, 1=visiting, 2=visited

        for code in self.concepts:
            if visited[code] == 0:
                self._has_cycle_dfs(code, adj, visited, [], errors)

    def validate_completeness(self) -> list[str]:
        """Validate the completeness and integrity of the curriculum structure.

        Detects undefined references and dependency cycles.
        """
        errors: list[str] = []
        self._validate_references(errors)
        self._detect_cycles(errors)
        return errors

    def _parse_element_coverage(
        self,
        item: dict[str, Any],
        covered_concepts: set[str],
        covered_skills: set[str],
        covered_misconceptions: set[str],
    ) -> None:
        # Element-level concepts
        el_concepts = item.get("concepts")
        if isinstance(el_concepts, list):
            for c in el_concepts:
                if c:
                    covered_concepts.add(str(c).strip())

        # Element-level skills
        el_skills = item.get("skills")
        if isinstance(el_skills, list):
            for s in el_skills:
                if s:
                    covered_skills.add(str(s).strip())

        # MCQ misconceptions
        misconceptions = item.get("misconceptions")
        if isinstance(misconceptions, dict):
            for m_val in misconceptions.values():
                if m_val:
                    covered_misconceptions.add(str(m_val).strip())

    def _parse_lesson_block_concepts(self, lesson: dict[str, Any], covered_concepts: set[str]) -> None:
        curr_block = lesson.get("curriculum")
        if isinstance(curr_block, dict):
            concept = curr_block.get("concept")
            if concept:
                covered_concepts.add(str(concept).strip())

        lesson_block = lesson.get("lesson")
        if isinstance(lesson_block, dict):
            concepts = lesson_block.get("concepts")
            if isinstance(concepts, list):
                for c in concepts:
                    if c:
                        covered_concepts.add(str(c).strip())

    def _parse_lesson_coverage(
        self,
        lesson: dict[str, Any],
        covered_concepts: set[str],
        covered_skills: set[str],
        covered_misconceptions: set[str],
    ) -> None:
        if not isinstance(lesson, dict):
            return

        self._parse_lesson_block_concepts(lesson, covered_concepts)

        # Extract elements content
        content = lesson.get("content") or []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    self._parse_element_coverage(
                        item, covered_concepts, covered_skills, covered_misconceptions
                    )

    def analyze_coverage(self, lessons: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Analyze curriculum coverage based on a list of lesson specs."""
        covered_concepts: set[str] = set()
        covered_skills: set[str] = set()
        covered_misconceptions: set[str] = set()

        for lesson in lessons:
            self._parse_lesson_coverage(
                lesson, covered_concepts, covered_skills, covered_misconceptions
            )

        # Keep only coverage of items defined in the graph
        valid_covered_concepts = covered_concepts & set(self.concepts.keys())
        valid_covered_skills = covered_skills & set(self.skills.keys())
        valid_covered_misconceptions = covered_misconceptions & set(self.misconceptions.keys())

        uncovered_concepts = set(self.concepts.keys()) - valid_covered_concepts
        uncovered_skills = set(self.skills.keys()) - valid_covered_skills
        uncovered_misconceptions = set(self.misconceptions.keys()) - valid_covered_misconceptions

        return {
            "covered_concepts": sorted(list(valid_covered_concepts)),
            "uncovered_concepts": sorted(list(uncovered_concepts)),
            "covered_skills": sorted(list(valid_covered_skills)),
            "uncovered_skills": sorted(list(uncovered_skills)),
            "covered_misconceptions": sorted(list(valid_covered_misconceptions)),
            "uncovered_misconceptions": sorted(list(uncovered_misconceptions)),
        }

    def detect_dependency_gaps(self, covered_concepts: list[str]) -> list[dict[str, str]]:
        """Detect prerequisite gaps where a covered concept lacks covered prerequisites."""
        gaps = []
        covered_set = set(covered_concepts)

        for concept in sorted(list(covered_set)):
            if concept not in self.concepts:
                continue
            prereqs = self.get_prerequisites(concept, transitive=False)
            for p in prereqs:
                if p not in covered_set:
                    gaps.append({
                        "concept": concept,
                        "missing_prerequisite": p
                    })
        return gaps


def validate_curriculum(data: dict) -> list[str]:
    """Validate a standalone curriculum graph document.

    Checks schema format and completeness (undefined references and cycles).
    """
    from .schemas import curriculum as curriculum_schema

    # 1. Schema check
    errors = curriculum_schema.validate(data)
    if errors:
        return errors

    # 2. Completeness check
    graph = CurriculumGraph.from_dict(data)
    errors.extend(graph.validate_completeness())
    return errors
