"""
SparkLabs Agent - Goal Decomposer

Two-phase goal decomposition engine with verification. Breaks
complex game development objectives into structured checklists,
evaluates item completion against verifiable criteria, and tracks
blocking dependency chains for AI-driven project planning.

Architecture:
  GoalDecomposer
    |-- Phase One: Structural Decomposition (goal → checklist items)
    |-- Phase Two: Verification (evidence-driven status evaluation)
    |-- Dependency Graph Analyzer (blocking chain computation)
    |-- Merge Engine (combine parent-child decompositions)

Goal Categories span the full game development lifecycle from
core mechanics through deployment, enabling comprehensive
coverage of all project dimensions.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChecklistStatus(Enum):
    COMPLETED = "completed"
    IMPOSSIBLE = "impossible"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"


class GoalCategory(Enum):
    MECHANICS = "mechanics"
    ASSETS = "assets"
    UI = "ui"
    AUDIO = "audio"
    OPTIMIZATION = "optimization"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class GoalLevel(Enum):
    EPIC = "epic"
    FEATURE = "feature"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"


@dataclass
class GoalNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    level: GoalLevel = GoalLevel.TASK
    parent_id: str = ""
    children: List[str] = field(default_factory=list)
    checklist_item: Optional[ChecklistItem] = None
    weight: float = 1.0
    estimated_hours: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "weight": self.weight,
            "estimated_hours": self.estimated_hours,
        }


@dataclass
class GoalTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    root_goal: str = ""
    nodes: Dict[str, GoalNode] = field(default_factory=dict)
    max_depth: int = 0
    total_nodes: int = 0

    def add_node(self, node: GoalNode) -> None:
        self.nodes[node.id] = node
        self.total_nodes = len(self.nodes)
        self.max_depth = max(self.max_depth, self._compute_depth(node.id))

    def get_children(self, node_id: str) -> List[GoalNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[c] for c in node.children if c in self.nodes]

    def _compute_depth(self, node_id: str, depth: int = 0) -> int:
        node = self.nodes.get(node_id)
        if not node:
            return depth
        if not node.parent_id:
            return depth
        return self._compute_depth(node.parent_id, depth + 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "root_goal": self.root_goal,
            "max_depth": self.max_depth,
            "total_nodes": self.total_nodes,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


@dataclass
class ChecklistItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    status: ChecklistStatus = ChecklistStatus.PENDING
    category: GoalCategory = GoalCategory.MECHANICS
    dependencies: List[str] = field(default_factory=list)
    verification_criteria: str = ""
    assigned_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "category": self.category.value,
            "dependencies": self.dependencies,
            "verification_criteria": self.verification_criteria,
            "assigned_agent": self.assigned_agent,
        }


@dataclass
class GoalDecomposition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal_text: str = ""
    items: List[ChecklistItem] = field(default_factory=list)
    total_items: int = 0
    completed_items: int = 0
    blocked_items: int = 0
    estimated_complexity: int = 1
    parent_goal_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_text": self.goal_text,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "blocked_items": self.blocked_items,
            "estimated_complexity": self.estimated_complexity,
            "parent_goal_id": self.parent_goal_id,
            "items": [it.to_dict() for it in self.items],
        }

    def _recompute_counts(self) -> None:
        self.total_items = len(self.items)
        self.completed_items = sum(
            1 for it in self.items if it.status == ChecklistStatus.COMPLETED
        )
        self.blocked_items = sum(
            1 for it in self.items if it.status == ChecklistStatus.BLOCKED
        )


class GoalDecomposer:
    """Two-phase goal decomposition with evidence-driven verification."""

    _instance: Optional["GoalDecomposer"] = None
    _lock = threading.Lock()

    MAX_DECOMPOSITIONS = 150
    MAX_ITEMS_PER_DECOMPOSITION = 300

    def __init__(self):
        self._decompositions: Dict[str, GoalDecomposition] = {}
        self._item_index: Dict[str, str] = {}
        self._total_decomposed: int = 0

    @classmethod
    def get_instance(cls) -> "GoalDecomposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def decompose(self, goal_str: str, custom_items: Optional[List[str]] = None) -> GoalDecomposition:
        """Decompose a goal into structured checklist items using domain-aware keyword analysis.
        
        Phase One - Structural Decomposition: Analyzes the goal text against
        domain-specific keyword libraries to generate semantically relevant
        subtasks organized by game development category.
        
        Phase Two - Dependency Detection: Automatically identifies prerequisite
        relationships between generated subtasks based on category ordering
        and item sequencing heuristics.
        """
        decomp = GoalDecomposition(goal_text=goal_str)

        category_keywords = {
            GoalCategory.MECHANICS: ["movement", "combat", "physics", "collision", "control", "input", "jump",
                                       "shoot", "melee", "dash", "ability", "skill", "action", "interact"],
            GoalCategory.ASSETS: ["sprite", "texture", "model", "mesh", "material", "animation", "character",
                                   "environment", "prop", "tileset", "spritesheet", "background", "effect"],
            GoalCategory.UI: ["menu", "hud", "button", "panel", "dialog", "overlay", "inventory", "shop",
                               "score", "healthbar", "minimap", "tooltip", "settings", "pause"],
            GoalCategory.AUDIO: ["sound", "music", "sfx", "voice", "ambient", "effect", "bgm", "footstep",
                                  "explosion", "collect", "hit", "jump", "background", "theme"],
            GoalCategory.OPTIMIZATION: ["performance", "fps", "memory", "batching", "lod", "culling",
                                         "atlas", "pool", "cache", "drawcall", "framerate", "lag"],
            GoalCategory.TESTING: ["test", "qa", "debug", "verify", "validate", "assert", "edgecase",
                                    "regression", "balance", "playtest", "feedback"],
            GoalCategory.DEPLOYMENT: ["build", "publish", "release", "bundle", "package", "deploy",
                                       "export", "platform", "web", "mobile", "desktop", "store"],
        }

        # Domain-specific subtask templates per category
        subtask_templates = {
            GoalCategory.MECHANICS: [
                "Design core {goal} loop and state machine",
                "Implement {goal} input handling and control mapping",
                "Create {goal} physics interactions and collision rules",
                "Build {goal} feedback systems (visual/audio cues)",
                "Configure {goal} parameters and tuning variables",
            ],
            GoalCategory.ASSETS: [
                "Define {goal} art style and visual direction",
                "Create primary {goal} sprites/models with placeholder variants",
                "Design {goal} animation keyframes and transitions",
                "Generate {goal} variant assets and palette swaps",
                "Set up {goal} asset import pipeline and compression",
            ],
            GoalCategory.UI: [
                "Sketch {goal} wireframe layout and information architecture",
                "Implement {goal} interactive elements and event handlers",
                "Design {goal} visual styling: colors, typography, spacing",
                "Add {goal} state management (loading/empty/error/success)",
                "Wire {goal} to game data bindings and update logic",
            ],
            GoalCategory.AUDIO: [
                "Design {goal} sound palette and audio direction",
                "Create or source {goal} primary sound effects",
                "Implement {goal} audio playback with spatial positioning",
                "Add {goal} audio mixing, ducking, and volume curves",
                "Set up {goal} dynamic audio transitions and layering",
            ],
            GoalCategory.OPTIMIZATION: [
                "Profile {goal} baseline performance metrics",
                "Identify {goal} bottlenecks via profiler analysis",
                "Implement {goal} batching/culling/pooling optimizations",
                "Apply {goal} asset compression and LOD strategies",
                "Validate {goal} performance targets across target platforms",
            ],
            GoalCategory.TESTING: [
                "Write {goal} unit test suite covering core paths",
                "Design {goal} integration test scenarios and edge cases",
                "Execute {goal} manual playthrough with structured checklist",
                "Collect and triage {goal} playtest feedback and bug reports",
                "Run {goal} regression suite and generate coverage report",
            ],
            GoalCategory.DEPLOYMENT: [
                "Configure {goal} build settings and platform targets",
                "Run {goal} production build with asset optimization",
                "Perform {goal} smoke test on target platform build",
                "Prepare {goal} store listing assets and metadata",
                "Execute {goal} release and verify post-deployment health",
            ],
        }

        goal_lower = goal_str.lower()
        goal_short = goal_str[:40]

        # Detect all applicable categories by keyword matching
        detected_categories: Dict[GoalCategory, int] = {}
        for cat, kws in category_keywords.items():
            score = sum(1 for kw in kws if kw in goal_lower)
            if score > 0:
                detected_categories[cat] = score

        if not detected_categories:
            detected_categories[GoalCategory.MECHANICS] = 1

        primary_category = max(detected_categories, key=detected_categories.get)
        secondary_categories = [
            cat for cat in detected_categories
            if cat != primary_category and detected_categories[cat] > 0
        ]

        complexity = min(10, max(1, len(goal_str.split()) // 3))
        
        # Generate items from custom list or templates
        if custom_items:
            for desc in custom_items:
                item = ChecklistItem(
                    description=desc,
                    category=primary_category,
                    verification_criteria=f"Verify: {desc[:60]} meets specification requirements",
                )
                decomp.items.append(item)
                self._item_index[item.id] = decomp.id
        else:
            # Primary category: generate all templates
            primary_templates = subtask_templates.get(primary_category, subtask_templates[GoalCategory.MECHANICS])
            for template in primary_templates[:complexity]:
                desc = template.format(goal=goal_short)
                item = ChecklistItem(
                    description=desc,
                    category=primary_category,
                    verification_criteria=self._generate_verification(desc, primary_category),
                )
                decomp.items.append(item)
                self._item_index[item.id] = decomp.id

            # Secondary categories: generate 2-3 items each
            for sec_cat in secondary_categories[:2]:
                sec_templates = subtask_templates.get(sec_cat, subtask_templates[GoalCategory.MECHANICS])
                for template in sec_templates[:min(3, complexity)]:
                    desc = template.format(goal=goal_short)
                    item = ChecklistItem(
                        description=desc,
                        category=sec_cat,
                        verification_criteria=self._generate_verification(desc, sec_cat),
                    )
                    decomp.items.append(item)
                    self._item_index[item.id] = decomp.id

        # Phase Two: Auto-detect dependencies based on category ordering
        self._detect_dependencies(decomp)

        decomp.estimated_complexity = complexity
        decomp._recompute_counts()
        self._decompositions[decomp.id] = decomp
        self._total_decomposed += 1

        if len(self._decompositions) > self.MAX_DECOMPOSITIONS:
            oldest = min(
                self._decompositions.values(),
                key=lambda d: d.created_at,
            )
            for it in oldest.items:
                self._item_index.pop(it.id, None)
            del self._decompositions[oldest.id]

        return decomp

    def _generate_verification(self, description: str, category: GoalCategory) -> str:
        """Generate verification criteria based on category-specific standards."""
        criteria_map = {
            GoalCategory.MECHANICS: f"Unit tests pass; manual playthrough confirms {description[:40]} works as designed",
            GoalCategory.ASSETS: f"Asset loads correctly; visual inspection confirms {description[:40]} meets quality standards",
            GoalCategory.UI: f"UI renders correctly at all resolutions; interaction flow for {description[:40]} functions end-to-end",
            GoalCategory.AUDIO: f"Audio plays without distortion; {description[:40]} triggers at correct timing and volume",
            GoalCategory.OPTIMIZATION: f"Performance profiling shows measurable improvement; {description[:40]} meets target metrics",
            GoalCategory.TESTING: f"All test cases pass; {description[:40]} coverage meets minimum threshold",
            GoalCategory.DEPLOYMENT: f"Build succeeds on all target platforms; {description[:40]} passes smoke test",
        }
        return criteria_map.get(category, f"Verify: {description[:60]} meets specification requirements")

    def _detect_dependencies(self, decomp: GoalDecomposition) -> None:
        """Auto-detect prerequisite dependencies between checklist items.
        
        Items in earlier categories (MECHANICS, ASSETS) are set as prerequisites
        for items in later categories (TESTING, DEPLOYMENT). Items within the
        same category form a sequential chain.
        """
        category_order = [
            GoalCategory.MECHANICS,
            GoalCategory.ASSETS,
            GoalCategory.UI,
            GoalCategory.AUDIO,
            GoalCategory.OPTIMIZATION,
            GoalCategory.TESTING,
            GoalCategory.DEPLOYMENT,
        ]
        
        items_by_category: Dict[GoalCategory, List[ChecklistItem]] = defaultdict(list)
        for item in decomp.items:
            items_by_category[item.category].append(item)

        # Chain dependencies: items in earlier categories are prerequisites for later
        for i in range(len(category_order) - 1):
            earlier_cat = category_order[i]
            for later_cat in category_order[i + 1:]:
                if earlier_cat in items_by_category and later_cat in items_by_category:
                    for later_item in items_by_category[later_cat]:
                        last_earlier = items_by_category[earlier_cat][-1]
                        if last_earlier.id not in later_item.dependencies:
                            later_item.dependencies.append(last_earlier.id)

    def add_dependency(self, item_id: str, depends_on_id: str) -> bool:
        """Explicitly declare that one checklist item depends on another."""
        if item_id not in self._item_index or depends_on_id not in self._item_index:
            return False
        if self._item_index[item_id] != self._item_index[depends_on_id]:
            return False
        decomp_id = self._item_index[item_id]
        decomp = self._decompositions.get(decomp_id)
        if decomp is None:
            return False
        item = next((it for it in decomp.items if it.id == item_id), None)
        if item is None:
            return False
        if depends_on_id not in item.dependencies:
            item.dependencies.append(depends_on_id)
        return True

    def prioritize_items(self, decomposition_id: str) -> List[Dict[str, Any]]:
        """Return items ordered by dependency depth (most foundational first)."""
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return []

        depth_cache: Dict[str, int] = {}

        def compute_depth(item_id: str, visited: Optional[set] = None) -> int:
            if visited is None:
                visited = set()
            if item_id in visited:
                return 0
            if item_id in depth_cache:
                return depth_cache[item_id]
            visited.add(item_id)
            item = next((it for it in decomp.items if it.id == item_id), None)
            if item is None:
                return 0
            if not item.dependencies:
                depth_cache[item_id] = 0
                return 0
            max_dep = max(compute_depth(d, visited.copy()) for d in item.dependencies)
            depth_cache[item_id] = max_dep + 1
            return max_dep + 1

        for item in decomp.items:
            compute_depth(item.id)

        sorted_items = sorted(
            decomp.items,
            key=lambda it: (depth_cache.get(it.id, 0), it.category.value),
        )
        return [{"id": it.id, "description": it.description, "depth": depth_cache.get(it.id, 0),
                 "category": it.category.value, "status": it.status.value} for it in sorted_items]

    def get_next_available(self, decomposition_id: str) -> List[Dict[str, Any]]:
        """Get items that are unblocked and ready to work on."""
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return []
        available = []
        for item in decomp.items:
            if item.status != ChecklistStatus.PENDING:
                continue
            if not item.dependencies:
                available.append(item)
                continue
            all_deps_met = all(
                any(d.id == dep_id and d.status == ChecklistStatus.COMPLETED for d in decomp.items)
                for dep_id in item.dependencies
            )
            if all_deps_met:
                available.append(item)
        return [{"id": it.id, "description": it.description, "category": it.category.value,
                 "verification": it.verification_criteria} for it in available]

    def create_milestones(self, decomposition_id: str) -> List[Dict[str, Any]]:
        """Group checklist items into logical milestone phases."""
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return []
        
        milestone_phases = [
            ("Foundation", [GoalCategory.MECHANICS]),
            ("Content Creation", [GoalCategory.ASSETS, GoalCategory.AUDIO]),
            ("Interface & Experience", [GoalCategory.UI]),
            ("Refinement", [GoalCategory.OPTIMIZATION]),
            ("Validation", [GoalCategory.TESTING]),
            ("Release", [GoalCategory.DEPLOYMENT]),
        ]
        
        milestones = []
        for phase_name, phase_cats in milestone_phases:
            phase_items = [it for it in decomp.items if it.category in phase_cats]
            if not phase_items:
                continue
            completed = sum(1 for it in phase_items if it.status == ChecklistStatus.COMPLETED)
            milestones.append({
                "phase": phase_name,
                "item_count": len(phase_items),
                "completed": completed,
                "progress_pct": round(completed / max(1, len(phase_items)) * 100, 1),
                "categories": [cat.value for cat in phase_cats],
            })
        return milestones

    def evaluate_item(
        self, item_id: str, evidence: str
    ) -> ChecklistStatus:
        if item_id not in self._item_index:
            return ChecklistStatus.PENDING

        decomp_id = self._item_index[item_id]
        decomp = self._decompositions.get(decomp_id)
        if decomp is None:
            return ChecklistStatus.PENDING

        item = next((it for it in decomp.items if it.id == item_id), None)
        if item is None:
            return ChecklistStatus.PENDING

        evidence_lower = evidence.lower()
        positive_markers = ["done", "complete", "finished", "pass", "success", "works", "verified"]
        negative_markers = ["fail", "error", "broken", "cannot", "impossible", "blocked"]
        progress_markers = ["started", "working", "wip", "in progress", "ongoing"]

        if any(m in evidence_lower for m in negative_markers):
            if "impossible" in evidence_lower or "cannot" in evidence_lower:
                item.status = ChecklistStatus.IMPOSSIBLE
            else:
                item.status = ChecklistStatus.BLOCKED
                self._propagate_block(item, decomp)
        elif any(m in evidence_lower for m in positive_markers):
            item.status = ChecklistStatus.COMPLETED
            self._unblock_dependents(item, decomp)
        elif any(m in evidence_lower for m in progress_markers):
            item.status = ChecklistStatus.IN_PROGRESS
        else:
            item.status = ChecklistStatus.PENDING

        decomp._recompute_counts()
        return item.status

    def _propagate_block(
        self, blocked_item: ChecklistItem, decomp: GoalDecomposition
    ) -> None:
        for item in decomp.items:
            if blocked_item.id in item.dependencies:
                if item.status not in (
                    ChecklistStatus.COMPLETED,
                    ChecklistStatus.IMPOSSIBLE,
                ):
                    item.status = ChecklistStatus.BLOCKED
                    self._propagate_block(item, decomp)

    def _unblock_dependents(
        self, completed_item: ChecklistItem, decomp: GoalDecomposition
    ) -> None:
        for item in decomp.items:
            if completed_item.id in item.dependencies:
                if item.status == ChecklistStatus.BLOCKED:
                    all_deps_met = all(
                        dep_id == completed_item.id
                        or any(
                            d.id == dep_id and d.status == ChecklistStatus.COMPLETED
                            for d in decomp.items
                        )
                        for dep_id in item.dependencies
                    )
                    if all_deps_met:
                        item.status = ChecklistStatus.PENDING

    def get_progress(self, decomposition_id: str) -> dict:
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return {"error": "Decomposition not found"}

        status_counts = {
            s.value: sum(1 for it in decomp.items if it.status == s)
            for s in ChecklistStatus
        }
        category_counts: Dict[str, int] = defaultdict(int)
        for it in decomp.items:
            category_counts[it.category.value] += 1

        return {
            "decomposition_id": decomposition_id,
            "goal_text": decomp.goal_text[:100],
            "total_items": decomp.total_items,
            "completed_items": decomp.completed_items,
            "blocked_items": decomp.blocked_items,
            "progress_pct": round(
                decomp.completed_items / max(1, decomp.total_items) * 100, 1
            ),
            "status_breakdown": status_counts,
            "category_breakdown": dict(category_counts),
            "estimated_complexity": decomp.estimated_complexity,
        }

    def get_blocking_chain(self, decomposition_id: str) -> list:
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return []

        incoming: Dict[str, List[str]] = defaultdict(list)
        for item in decomp.items:
            for dep_id in item.dependencies:
                incoming[dep_id].append(item.id)

        blocking_chain: List[Dict[str, Any]] = []
        visited: set = set()

        def dfs(item_id: str, depth: int) -> None:
            if item_id in visited or depth > 20:
                return
            visited.add(item_id)
            item = next((it for it in decomp.items if it.id == item_id), None)
            if item is None:
                return
            blocking_chain.append({
                "item_id": item_id,
                "description": item.description,
                "status": item.status.value,
                "depth": depth,
                "blocks": len(incoming.get(item_id, [])),
            })
            for child_id in incoming.get(item_id, []):
                child = next((it for it in decomp.items if it.id == child_id), None)
                if child and child.status == ChecklistStatus.BLOCKED:
                    dfs(child_id, depth + 1)

        for item in decomp.items:
            if item.status == ChecklistStatus.BLOCKED:
                is_root_blocker = not any(
                    dep_id in incoming
                    for dep_id in item.dependencies
                )
                if is_root_blocker:
                    dfs(item.id, 0)

        return blocking_chain

    def merge_decomposition(self, parent_id: str, child_id: str) -> bool:
        parent = self._decompositions.get(parent_id)
        child = self._decompositions.get(child_id)
        if parent is None or child is None:
            return False
        if len(parent.items) + len(child.items) > self.MAX_ITEMS_PER_DECOMPOSITION:
            return False

        for child_item in child.items:
            child_item.id = uuid.uuid4().hex
            self._item_index[child_item.id] = parent_id
            parent.items.append(child_item)

        for item in parent.items:
            if item.assigned_agent:
                item.dependencies.append(child.id)

        parent._recompute_counts()
        for it in child.items:
            self._item_index.pop(it.id, None)
        del self._decompositions[child_id]
        return True

    def get_stats(self) -> dict:
        total_items = sum(d.total_items for d in self._decompositions.values())
        total_completed = sum(d.completed_items for d in self._decompositions.values())
        total_blocked = sum(d.blocked_items for d in self._decompositions.values())
        category_dist: Dict[str, int] = defaultdict(int)
        for d in self._decompositions.values():
            for it in d.items:
                category_dist[it.category.value] += 1

        return {
            "total_decompositions": len(self._decompositions),
            "total_decomposed_ever": self._total_decomposed,
            "total_items": total_items,
            "total_completed": total_completed,
            "total_blocked": total_blocked,
            "overall_progress_pct": round(
                total_completed / max(1, total_items) * 100, 1
            ),
            "category_distribution": dict(category_dist),
            "max_decompositions": self.MAX_DECOMPOSITIONS,
            "max_items_per_decomposition": self.MAX_ITEMS_PER_DECOMPOSITION,
        }


def get_goal_decomposer() -> GoalDecomposer:
    return GoalDecomposer.get_instance()