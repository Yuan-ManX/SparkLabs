"""
SparkLabs Agent - Narrative Branch System

Generates branching storylines with consistency checking for game narratives,
dialogues, and quests. Manages narrative nodes, character profiles, dialogue
lines, and validates story coherence across branching paths.

Architecture:
  NarrativeBranchSystem
    |-- BranchBuilder (constructs branching narrative trees)
    |-- ConsistencyValidator (cross-references characters, locations, events)
    |-- ConflictResolver (automatic plot hole and contradiction resolution)
    |-- DialogueManager (character dialogue with emotional states)
    |-- ConsequenceTracker (cause-effect chain mapping)

Narrative Operations:
  - BRANCH_CREATION: starting new narrative arcs from nodes
  - CONSISTENCY_CHECK: detecting contradictions across branches
  - AUTO_RESOLVE: automatic conflict resolution where possible
  - CHARACTER_GENERATION: creating NPCs with traits and motivations
  - DIALOGUE_ADDITION: injecting dialogue with emotional context
  - BRANCH_MERGE: combining divergent story paths
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class NarrativeNodeType(Enum):
    START = "start"
    BRANCH_POINT = "branch_point"
    DIALOGUE = "dialogue"
    QUEST_START = "quest_start"
    QUEST_COMPLETE = "quest_complete"
    CONSEQUENCE = "consequence"
    ENDING = "ending"
    CHOICE = "choice"


class ConsistencyLevel(Enum):
    STRICT = "strict"
    LOOSE = "loose"
    NONE = "none"


class BranchStrategy(Enum):
    BINARY = "binary"
    MULTI_PATH = "multi_path"
    CYCLICAL = "cyclical"
    CONVERGENT = "convergent"
    EMERGENT = "emergent"


class CharacterRole(Enum):
    PROTAGONIST = "protagonist"
    ALLY = "ally"
    ANTAGONIST = "antagonist"
    NEUTRAL = "neutral"
    MENTOR = "mentor"
    RIVAL = "rival"


@dataclass
class NarrativeNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: NarrativeNodeType = NarrativeNodeType.START
    title: str = ""
    content: str = ""
    characters: List[str] = field(default_factory=list)
    choices: List[str] = field(default_factory=list)
    next_nodes: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    emotional_tone: str = "neutral"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "title": self.title,
            "content": self.content,
            "characters": self.characters,
            "choices": self.choices,
            "next_nodes": self.next_nodes,
            "conditions": self.conditions,
            "emotional_tone": self.emotional_tone,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class NarrativeBranch:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_node_id: str = ""
    nodes: Dict[str, NarrativeNode] = field(default_factory=dict)
    strategy: BranchStrategy = BranchStrategy.BINARY
    total_paths: int = 1
    ending_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes),
            "strategy": self.strategy.value,
            "total_paths": self.total_paths,
            "ending_count": self.ending_count,
            "created_at": self.created_at,
        }


@dataclass
class CharacterProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: CharacterRole = CharacterRole.NEUTRAL
    traits: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    arc_description: str = ""
    dialogue_style: str = "neutral"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "traits": self.traits,
            "motivations": self.motivations,
            "relationships": self.relationships,
            "arc_description": self.arc_description,
            "dialogue_style": self.dialogue_style,
            "created_at": self.created_at,
        }


@dataclass
class ConsistencyReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    branch_id: str = ""
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    fixed_count: int = 0
    remaining_conflicts: int = 0
    is_consistent: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "issues_found": self.issues_found,
            "fixed_count": self.fixed_count,
            "remaining_conflicts": self.remaining_conflicts,
            "is_consistent": self.is_consistent,
            "created_at": self.created_at,
        }


@dataclass
class DialogueLine:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    character_id: str = ""
    text: str = ""
    emotion: str = "neutral"
    conditions: Dict[str, Any] = field(default_factory=dict)
    response_options: List[str] = field(default_factory=list)
    ordering: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "text": self.text,
            "emotion": self.emotion,
            "conditions": self.conditions,
            "response_options": self.response_options,
            "ordering": self.ordering,
            "created_at": self.created_at,
        }


class NarrativeBranchSystem:
    """AI agent for branching narrative generation with consistency validation."""

    _instance: Optional["NarrativeBranchSystem"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "NarrativeBranchSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._branches: Dict[str, NarrativeBranch] = {}
        self._characters: Dict[str, CharacterProfile] = {}
        self._dialogues: Dict[str, List[DialogueLine]] = {}
        self._consistency_reports: Dict[str, List[ConsistencyReport]] = {}
        self._total_branches_created: int = 0
        self._total_nodes_created: int = 0
        self._total_conflicts_resolved: int = 0
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "NarrativeBranchSystem":
        return cls()

    # ---- Branch Management ----

    def create_branch(self,
                      name: str,
                      strategy: str = "binary",
                      root_content: str = "") -> Optional[NarrativeBranch]:
        try:
            st = BranchStrategy(strategy.lower())
        except ValueError:
            st = BranchStrategy.BINARY

        root_node = NarrativeNode(
            node_type=NarrativeNodeType.START,
            title=f"{name} - Root",
            content=root_content,
        )

        branch = NarrativeBranch(
            name=name,
            root_node_id=root_node.id,
            nodes={root_node.id: root_node},
            strategy=st,
        )

        self._branches[branch.id] = branch
        self._consistency_reports[branch.id] = []
        self._total_branches_created += 1
        self._total_nodes_created += 1
        return branch

    def get_branch(self, branch_id: str) -> Optional[NarrativeBranch]:
        return self._branches.get(branch_id)

    def list_branches(self) -> List[NarrativeBranch]:
        return list(self._branches.values())

    # ---- Node Management ----

    def add_node(self,
                 branch_id: str,
                 node_type: str,
                 content: str,
                 parent_node_ids: Optional[List[str]] = None,
                 choices: Optional[List[str]] = None) -> Optional[NarrativeNode]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return None

        try:
            nt = NarrativeNodeType(node_type.lower())
        except ValueError:
            nt = NarrativeNodeType.DIALOGUE

        node = NarrativeNode(
            node_type=nt,
            title=f"Node {len(branch.nodes) + 1}",
            content=content,
            choices=choices or [],
        )

        parent_ids = parent_node_ids or []
        for pid in parent_ids:
            if pid in branch.nodes:
                branch.nodes[pid].next_nodes.append(node.id)

        branch.nodes[node.id] = node

        if nt == NarrativeNodeType.ENDING:
            branch.ending_count += 1

        self._recalculate_paths(branch)
        self._total_nodes_created += 1
        return node

    def get_node(self, branch_id: str, node_id: str) -> Optional[NarrativeNode]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return None
        return branch.nodes.get(node_id)

    def get_nodes_by_type(self,
                          branch_id: str,
                          node_type: str) -> List[NarrativeNode]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return []
        try:
            nt = NarrativeNodeType(node_type.lower())
        except ValueError:
            return []
        return [n for n in branch.nodes.values() if n.node_type == nt]

    # ---- Branching Operations ----

    def branch_from_node(self,
                         branch_id: str,
                         node_id: str,
                         branch_choices: List[Dict[str, Any]]) -> Optional[NarrativeBranch]:
        branch = self._branches.get(branch_id)
        if branch is None or node_id not in branch.nodes:
            return None

        source_node = branch.nodes[node_id]

        sub_branch = NarrativeBranch(
            name=f"{branch.name} - Sub-branch from {source_node.title}",
            strategy=BranchStrategy.MULTI_PATH,
        )

        sub_root = NarrativeNode(
            node_type=NarrativeNodeType.BRANCH_POINT,
            title=f"Sub-branch: {source_node.title}",
            content=source_node.content,
            characters=list(source_node.characters),
            emotional_tone=source_node.emotional_tone,
        )
        sub_branch.nodes[sub_root.id] = sub_root
        sub_branch.root_node_id = sub_root.id

        for choice in branch_choices:
            node = NarrativeNode(
                node_type=NarrativeNodeType.CHOICE,
                title=choice.get("title", "Choice"),
                content=choice.get("content", ""),
                choices=choice.get("options", []),
                conditions=choice.get("conditions", {}),
                emotional_tone=choice.get("tone", "neutral"),
            )
            sub_root.next_nodes.append(node.id)
            sub_branch.nodes[node.id] = node

        self._branches[sub_branch.id] = sub_branch
        self._consistency_reports[sub_branch.id] = []
        self._total_branches_created += 1
        self._total_nodes_created += len(sub_branch.nodes)
        return sub_branch

    def merge_branches(self,
                       branch_id_a: str,
                       branch_id_b: str) -> Optional[NarrativeBranch]:
        branch_a = self._branches.get(branch_id_a)
        branch_b = self._branches.get(branch_id_b)
        if branch_a is None or branch_b is None:
            return None

        merged = NarrativeBranch(
            name=f"Merged: {branch_a.name} + {branch_b.name}",
            strategy=BranchStrategy.CONVERGENT,
        )

        connector = NarrativeNode(
            node_type=NarrativeNodeType.BRANCH_POINT,
            title="Merge Point",
            content="Narrative paths converge here.",
        )
        merged.nodes[connector.id] = merged.nodes.get(connector.id, connector)
        merged.root_node_id = connector.id

        for br in (branch_a, branch_b):
            for node in br.nodes.values():
                merged.nodes[node.id] = node
            connector.next_nodes.append(br.root_node_id)

        merged.ending_count = branch_a.ending_count + branch_b.ending_count
        self._recalculate_paths(merged)

        self._branches[merged.id] = merged
        self._consistency_reports[merged.id] = []
        self._total_branches_created += 1
        return merged

    # ---- Consistency Checking ----

    def check_consistency(self,
                          branch_id: str,
                          level: str = "strict") -> Optional[ConsistencyReport]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return None

        try:
            cl = ConsistencyLevel(level.lower())
        except ValueError:
            cl = ConsistencyLevel.STRICT

        issues = self._detect_contradictions(branch)
        valid_choice_issues = self._validate_choices_for_branch(branch)

        if cl == ConsistencyLevel.STRICT:
            all_issues = issues + valid_choice_issues
        elif cl == ConsistencyLevel.LOOSE:
            all_issues = [i for i in issues if i.get("severity", "low") != "low"]
        else:
            all_issues = []

        report = ConsistencyReport(
            branch_id=branch_id,
            issues_found=all_issues,
            remaining_conflicts=len(all_issues),
            is_consistent=len(all_issues) == 0,
        )

        reports = self._consistency_reports.get(branch_id, [])
        reports.append(report)
        self._consistency_reports[branch_id] = reports
        return report

    def auto_resolve_conflicts(self, branch_id: str) -> Optional[ConsistencyReport]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return None

        issues = self._detect_contradictions(branch)
        choice_issues = self._validate_choices_for_branch(branch)
        all_issues = issues + choice_issues

        fixed = 0
        for issue in all_issues:
            issue_type = issue.get("type", "")
            if issue_type == "orphan_node":
                node_id = issue.get("node_id", "")
                parent_id = issue.get("suggested_parent", "")
                if parent_id and parent_id in branch.nodes:
                    branch.nodes[parent_id].next_nodes.append(node_id)
                    fixed += 1
            elif issue_type == "dangling_choice":
                node_id = issue.get("node_id", "")
                if node_id in branch.nodes:
                    resolution = NarrativeNode(
                        node_type=NarrativeNodeType.CONSEQUENCE,
                        title="Auto-resolved Choice",
                        content="This path was resolved automatically.",
                    )
                    branch.nodes[node_id].next_nodes.append(resolution.id)
                    branch.nodes[resolution.id] = resolution
                    fixed += 1
            elif issue_type == "character_inconsistency":
                char_id = issue.get("character_id", "")
                resolved = issue.get("auto_resolution", False)
                if resolved and char_id in self._characters:
                    fixed += 1

        remaining = len(all_issues) - fixed
        self._total_conflicts_resolved += fixed

        report = ConsistencyReport(
            branch_id=branch_id,
            issues_found=all_issues,
            fixed_count=fixed,
            remaining_conflicts=remaining,
            is_consistent=remaining == 0,
        )

        reports = self._consistency_reports.get(branch_id, [])
        reports.append(report)
        self._consistency_reports[branch_id] = reports
        return report

    def get_consistency_reports(self, branch_id: str) -> List[ConsistencyReport]:
        return self._consistency_reports.get(branch_id, [])

    # ---- Character Management ----

    def generate_character(self,
                           name: str,
                           role: str = "neutral",
                           traits: Optional[List[str]] = None) -> CharacterProfile:
        try:
            cr = CharacterRole(role.lower())
        except ValueError:
            cr = CharacterRole.NEUTRAL

        dialogue_styles = {
            CharacterRole.PROTAGONIST: "determined",
            CharacterRole.ALLY: "supportive",
            CharacterRole.ANTAGONIST: "menacing",
            CharacterRole.NEUTRAL: "neutral",
            CharacterRole.MENTOR: "wise",
            CharacterRole.RIVAL: "competitive",
        }

        character = CharacterProfile(
            name=name,
            role=cr,
            traits=traits or [],
            dialogue_style=dialogue_styles.get(cr, "neutral"),
        )

        self._characters[character.id] = character
        return character

    def get_character(self, character_id: str) -> Optional[CharacterProfile]:
        return self._characters.get(character_id)

    def list_characters(self, role: Optional[str] = None) -> List[CharacterProfile]:
        chars = list(self._characters.values())
        if role is not None:
            try:
                cr = CharacterRole(role.lower())
                chars = [c for c in chars if c.role == cr]
            except ValueError:
                pass
        return chars

    def update_character_relationship(self,
                                      character_id: str,
                                      other_character_id: str,
                                      relationship_type: str) -> bool:
        character = self._characters.get(character_id)
        if character is None:
            return False
        character.relationships[other_character_id] = relationship_type
        return True

    # ---- Dialogue Management ----

    def add_dialogue(self,
                     character_id: str,
                     text: str,
                     emotion: str = "neutral",
                     conditions: Optional[Dict[str, Any]] = None) -> Optional[DialogueLine]:
        character = self._characters.get(character_id)
        if character is None:
            return None

        existing = self._dialogues.get(character_id, [])
        line = DialogueLine(
            character_id=character_id,
            text=text,
            emotion=emotion,
            conditions=conditions or {},
            ordering=len(existing),
        )

        existing.append(line)
        self._dialogues[character_id] = existing
        return line

    def get_dialogue_for_character(self,
                                   character_id: str) -> List[DialogueLine]:
        return self._dialogues.get(character_id, [])

    def get_all_dialogues(self) -> Dict[str, List[DialogueLine]]:
        return dict(self._dialogues)

    def add_response_option(self,
                            dialogue_id: str,
                            character_id: str,
                            option_text: str) -> bool:
        lines = self._dialogues.get(character_id, [])
        for line in lines:
            if line.id == dialogue_id:
                line.response_options.append(option_text)
                return True
        return False

    # ---- Export ----

    def export_narrative(self,
                         branch_id: str,
                         format: str = "dict") -> Optional[Dict[str, Any]]:
        branch = self._branches.get(branch_id)
        if branch is None:
            return None

        if format == "dict":
            nodes_data = {nid: n.to_dict() for nid, n in branch.nodes.items()}
            characters_in_branch: List[str] = []
            for node in branch.nodes.values():
                for cid in node.characters:
                    if cid not in characters_in_branch:
                        characters_in_branch.append(cid)

            character_data = {}
            for cid in characters_in_branch:
                char = self._characters.get(cid)
                if char:
                    character_data[cid] = char.to_dict()

            dialogue_data = {}
            for cid in characters_in_branch:
                lines = self._dialogues.get(cid, [])
                if lines:
                    dialogue_data[cid] = [l.to_dict() for l in lines]

            return {
                "branch": branch.to_dict(),
                "nodes": nodes_data,
                "characters": character_data,
                "dialogues": dialogue_data,
                "consistency_reports": [
                    r.to_dict() for r in self._consistency_reports.get(branch_id, [])
                ],
            }
        elif format == "flat":
            nodes_list = [n.to_dict() for n in branch.nodes.values()]
            return {
                "branch_name": branch.name,
                "branch_id": branch.id,
                "strategy": branch.strategy.value,
                "nodes": nodes_list,
                "node_count": len(nodes_list),
                "ending_count": branch.ending_count,
                "total_paths": branch.total_paths,
            }
        else:
            return {"error": f"Unsupported format: {format}", "branch_id": branch_id}

    # ---- Internal Methods ----

    def _detect_contradictions(self, branch: NarrativeBranch) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        visited: Dict[str, str] = {}

        for node_id, node in branch.nodes.items():
            for next_id in node.next_nodes:
                if next_id not in branch.nodes:
                    issues.append({
                        "type": "orphan_node",
                        "severity": "high",
                        "node_id": next_id,
                        "referenced_by": node_id,
                        "suggested_parent": node_id,
                        "description": f"Node {next_id} referenced but does not exist in branch.",
                    })

            for choice_idx, choice in enumerate(node.choices):
                if choice_idx < len(node.next_nodes):
                    continue
                issues.append({
                    "type": "dangling_choice",
                    "severity": "medium",
                    "node_id": node_id,
                    "choice_index": choice_idx,
                    "choice_text": choice,
                    "description": f"Choice '{choice}' has no corresponding next node.",
                })

            for char_id in node.characters:
                if char_id not in self._characters:
                    issues.append({
                        "type": "missing_character",
                        "severity": "low",
                        "node_id": node_id,
                        "character_id": char_id,
                        "description": f"Character {char_id} referenced but not defined.",
                    })

            if node_id in visited:
                existing_node = branch.nodes.get(visited[node_id])
                if existing_node and existing_node.node_type != node.node_type:
                    issues.append({
                        "type": "character_inconsistency",
                        "severity": "medium",
                        "node_id": node_id,
                        "character_id": "",
                        "auto_resolution": False,
                        "description": f"Node {node_id} appears with inconsistent type.",
                    })

        # Check for unreachable nodes (no incoming edges besides root)
        reachable: set[str] = {branch.root_node_id}
        stack = [branch.root_node_id]
        while stack:
            current = stack.pop()
            node = branch.nodes.get(current)
            if node is None:
                continue
            for next_id in node.next_nodes:
                if next_id not in reachable:
                    reachable.add(next_id)
                    stack.append(next_id)

        for node_id in branch.nodes:
            if node_id not in reachable:
                issues.append({
                    "type": "unreachable_node",
                    "severity": "medium",
                    "node_id": node_id,
                    "description": f"Node {node_id} is not reachable from root.",
                })

        return issues

    def _validate_choices(self, node: NarrativeNode) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if node.node_type == NarrativeNodeType.CHOICE and not node.choices:
            issues.append({
                "type": "empty_choice_node",
                "severity": "high",
                "node_id": node.id,
                "description": f"Choice node {node.id} has no options defined.",
            })
        if node.node_type == NarrativeNodeType.BRANCH_POINT and len(node.next_nodes) < 2:
            issues.append({
                "type": "insufficient_branches",
                "severity": "low",
                "node_id": node.id,
                "description": f"Branch point {node.id} has fewer than 2 outgoing paths.",
            })
        if node.node_type == NarrativeNodeType.ENDING and node.next_nodes:
            issues.append({
                "type": "non_terminal_ending",
                "severity": "medium",
                "node_id": node.id,
                "description": f"Ending node {node.id} should not have outgoing nodes.",
            })
        return issues

    def _validate_choices_for_branch(self, branch: NarrativeBranch) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for node in branch.nodes.values():
            issues.extend(self._validate_choices(node))
        return issues

    def _track_consequences(self, node_id: str) -> List[Dict[str, Any]]:
        chain: List[Dict[str, Any]] = []
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for branch in self._branches.values():
                node = branch.nodes.get(current)
                if node is None:
                    continue
                if node.node_type == NarrativeNodeType.CONSEQUENCE:
                    chain.append({
                        "node_id": node.id,
                        "title": node.title,
                        "effect": node.conditions,
                    })
                for next_id in node.next_nodes:
                    if next_id not in visited:
                        stack.append(next_id)
        return chain

    def _recalculate_paths(self, branch: NarrativeBranch) -> None:
        if not branch.nodes:
            branch.total_paths = 0
            return

        def count_paths(from_id: str, visited: set[str]) -> int:
            if from_id in visited:
                return 0
            node = branch.nodes.get(from_id)
            if node is None:
                return 0
            if node.node_type == NarrativeNodeType.ENDING:
                return 1
            if not node.next_nodes:
                return 1
            total = 0
            for next_id in node.next_nodes:
                new_visited = visited | {from_id}
                total += count_paths(next_id, new_visited)
            return max(total, 1)

        branch.total_paths = count_paths(branch.root_node_id, set())

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(b.nodes) for b in self._branches.values())
        total_dialogue_lines = sum(len(lines) for lines in self._dialogues.values())
        total_reports = sum(len(reports) for reports in self._consistency_reports.values())
        consistent_branches = sum(
            1 for b_id in self._branches
            for r in self._consistency_reports.get(b_id, [])
            if r.is_consistent
        )
        return {
            "total_branches": len(self._branches),
            "total_nodes": total_nodes,
            "total_characters": len(self._characters),
            "total_dialogue_lines": total_dialogue_lines,
            "total_consistency_reports": total_reports,
            "total_branches_created": self._total_branches_created,
            "total_nodes_created": self._total_nodes_created,
            "total_conflicts_resolved": self._total_conflicts_resolved,
            "consistent_branches": consistent_branches,
        }


def get_narrative_branch() -> NarrativeBranchSystem:
    return NarrativeBranchSystem.get_instance()