"""
SparkLabs Agent - Semantic World Indexer"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class EntityCategory(Enum):
    """Semantic categories for world entities."""
    CHARACTER = "character"
    ITEM = "item"
    WEAPON = "weapon"
    CONTAINER = "container"
    FURNITURE = "furniture"
    STRUCTURE = "structure"
    PORTAL = "portal"
    TRIGGER = "trigger"
    VEHICLE = "vehicle"
    FLORA = "flora"
    FAUNA = "fauna"
    HAZARD = "hazard"
    COLLECTIBLE = "collectible"
    UNKNOWN = "unknown"


class RelationType(Enum):
    """Semantic relationship types between entities."""
    CONTAINS = "contains"            # A contains B
    OWNED_BY = "owned_by"            # A is owned by B
    ON_TOP_OF = "on_top_of"          # A rests on B
    INSIDE = "inside"                # A is inside B
    NEAR = "near"                    # A is near B (spatial proximity)
    BLOCKS = "blocks"                # A blocks path to B
    THREATENS = "threatens"          # A threatens B
    ALLIED_WITH = "allied_with"      # A is allied with B
    ENEMY_OF = "enemy_of"            # A is enemy of B
    USES = "uses"                    # A uses B
    CREATES = "creates"              # A creates B
    DESTROYS = "destroys"            # A destroys B
    LEADS_TO = "leads_to"            # A leads to B (portals, paths)
    INTERACTS_WITH = "interacts_with"  # A can interact with B


class IndexerPhase(Enum):
    """Phases of the semantic indexer cycle."""
    INGEST = "ingest"
    INDEX = "index"
    LINK = "link"
    QUERY = "query"
    EVOLVE = "evolve"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SemanticEntity:
    """A world entity with semantic metadata."""
    entity_id: str
    name: str
    category: EntityCategory
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tags: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    semantic_roles: Set[str] = field(default_factory=set)
    last_updated: float = field(default_factory=time.time)


@dataclass
class SemanticRelation:
    """A directed relationship between two entities."""
    source_id: str
    target_id: str
    relation: RelationType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class SemanticQuery:
    """A semantic query record."""
    query_id: str
    query_text: str
    intent: str
    result_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class IndexerStats:
    """Statistics for the semantic indexer."""
    total_entities: int = 0
    total_relations: int = 0
    total_queries: int = 0
    total_cycles: int = 0
    total_links_built: int = 0
    total_relations_decayed: int = 0
    total_merges: int = 0
    avg_query_time_ms: float = 0.0
    category_distribution: Dict[str, int] = field(default_factory=dict)
    relation_distribution: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# AgentSemanticWorldIndexer
# =============================================================================

class AgentSemanticWorldIndexer:
    """Semantic world indexer for AI-native game engine.

    Builds and maintains a semantic graph of the game world, enabling AI
    agents to reason about entities and relationships in human-like terms.
    """

    _instance: Optional["AgentSemanticWorldIndexer"] = None
    _instance_lock = threading.Lock()

    # Distance threshold for NEAR relationships
    NEAR_DISTANCE = 15.0
    # Relations decay after this many seconds without reinforcement
    DECAY_TIMEOUT = 300.0
    # Minimum weight before a relation is pruned
    MIN_RELATION_WEIGHT = 0.05

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entities: Dict[str, SemanticEntity] = {}
        self._relations: Dict[str, SemanticRelation] = {}
        self._spatial_index: Dict[Tuple[int, int, int], Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._query_history: Deque[SemanticQuery] = deque(maxlen=200)
        self._pending_ingest: Deque[SemanticEntity] = deque(maxlen=500)
        self._cycle_count = 0
        self._stats = IndexerStats()
        self._active = False
        logger.info("AgentSemanticWorldIndexer initialized")

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentSemanticWorldIndexer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Entity Management
    # -------------------------------------------------------------------------

    def register_entity(
        self,
        entity_id: str,
        name: str,
        category: str,
        position: Optional[Tuple[float, float, float]] = None,
        tags: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        semantic_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register or update a world entity with semantic metadata."""
        with self._lock:
            cat = self._resolve_category(category)
            entity = SemanticEntity(
                entity_id=entity_id,
                name=name,
                category=cat,
                position=position or (0.0, 0.0, 0.0),
                tags=set(tags or []),
                properties=properties or {},
                semantic_roles=set(semantic_roles or []),
            )
            self._entities[entity_id] = entity
            self._pending_ingest.append(entity)
            self._update_spatial_index(entity_id, entity.position)
            for tag in entity.tags:
                self._tag_index[tag].add(entity_id)
            return self._entity_to_dict(entity)

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its relations."""
        with self._lock:
            if entity_id not in self._entities:
                return False
            del self._entities[entity_id]
            # Remove all relations involving this entity
            to_remove = [
                rid for rid, rel in self._relations.items()
                if rel.source_id == entity_id or rel.target_id == entity_id
            ]
            for rid in to_remove:
                del self._relations[rid]
            # Clean indices
            for tag_set in self._tag_index.values():
                tag_set.discard(entity_id)
            return True

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a semantic relation between two entities."""
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                return {"error": "Source or target entity not found"}
            rel_type = self._resolve_relation(relation)
            if rel_type is None:
                return {"error": f"Invalid relation type: {relation}"}
            rel_id = f"{source_id}->{target_id}:{rel_type.value}"
            relation_obj = SemanticRelation(
                source_id=source_id,
                target_id=target_id,
                relation=rel_type,
                weight=max(0.0, min(1.0, weight)),
                metadata=metadata or {},
            )
            self._relations[rel_id] = relation_obj
            self._stats.total_links_built += 1
            return self._relation_to_dict(relation_obj)

    # -------------------------------------------------------------------------
    # Semantic Queries
    # -------------------------------------------------------------------------

    def query(
        self,
        intent: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        near_entity: Optional[str] = None,
        near_radius: Optional[float] = None,
        has_role: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Query the semantic graph for entities matching criteria."""
        start_time = time.time()
        with self._lock:
            results: List[Dict[str, Any]] = []
            cat_filter = self._resolve_category(category) if category else None
            radius = near_radius or self.NEAR_DISTANCE

            # Determine center point for spatial query
            center = None
            if near_entity and near_entity in self._entities:
                center = self._entities[near_entity].position

            for eid, entity in self._entities.items():
                # Category filter
                if cat_filter and entity.category != cat_filter:
                    continue
                # Tag filter
                if tags:
                    if not all(t in entity.tags for t in tags):
                        continue
                # Role filter
                if has_role and has_role not in entity.semantic_roles:
                    continue
                # Spatial filter
                if center:
                    dist = self._distance(entity.position, center)
                    if dist > radius:
                        continue

                entry = self._entity_to_dict(entity)
                if center:
                    entry["distance"] = round(self._distance(entity.position, center), 2)
                # Attach outgoing relations
                entry["relations"] = self._get_entity_relations(eid)
                results.append(entry)
                if len(results) >= limit:
                    break

            elapsed_ms = (time.time() - start_time) * 1000
            query_id = f"q_{int(time.time() * 1000)}_{self._stats.total_queries}"
            self._query_history.append(SemanticQuery(
                query_id=query_id,
                query_text=intent,
                intent=intent,
                result_count=len(results),
            ))
            self._stats.total_queries += 1
            self._stats.avg_query_time_ms = round(
                (self._stats.avg_query_time_ms * (self._stats.total_queries - 1) + elapsed_ms)
                / self._stats.total_queries,
                2,
            )
            return {
                "query_id": query_id,
                "intent": intent,
                "result_count": len(results),
                "query_time_ms": round(elapsed_ms, 2),
                "results": results,
            }

    def query_relations(
        self,
        entity_id: str,
        direction: str = "both",
        relation_type: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Query relations for a specific entity."""
        with self._lock:
            if entity_id not in self._entities:
                return {"error": "Entity not found"}
            rel_filter = self._resolve_relation(relation_type) if relation_type else None
            results: List[Dict[str, Any]] = []
            for rel in self._relations.values():
                if rel_filter and rel.relation != rel_filter:
                    continue
                if direction in ("out", "both") and rel.source_id == entity_id:
                    results.append(self._relation_to_dict(rel))
                if direction in ("in", "both") and rel.target_id == entity_id:
                    results.append(self._relation_to_dict(rel))
                if len(results) >= limit:
                    break
            return {
                "entity_id": entity_id,
                "direction": direction,
                "relation_count": len(results),
                "relations": results,
            }

    def find_path(self, source_id: str, target_id: str, max_depth: int = 4) -> Dict[str, Any]:
        """Find a semantic path between two entities through the relation graph."""
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                return {"error": "Source or target entity not found"}

            visited: Set[str] = set()
            queue: List[List[str]] = [[source_id]]
            paths_found: List[List[str]] = []

            while queue and len(paths_found) < 5:
                path = queue.pop(0)
                current = path[-1]
                if current in visited:
                    continue
                visited.add(current)
                if current == target_id and len(path) > 1:
                    paths_found.append(path)
                    continue
                if len(path) > max_depth:
                    continue
                # Explore neighbors
                for rel in self._relations.values():
                    if rel.source_id == current and rel.target_id not in visited:
                        queue.append(path + [rel.target_id])
                    elif rel.target_id == current and rel.source_id not in visited:
                        queue.append(path + [rel.source_id])

            return {
                "source": source_id,
                "target": target_id,
                "paths_found": len(paths_found),
                "paths": paths_found,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single indexer cycle.

        Phases: INGEST -> INDEX -> LINK -> QUERY -> EVOLVE
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = IndexerPhase.INGEST

            # Phase 1: INGEST - process pending entities
            ingested = len(self._pending_ingest)
            self._pending_ingest.clear()

            # Phase 2: INDEX - update distribution stats
            phase = IndexerPhase.INDEX
            self._update_distributions()

            # Phase 3: LINK - auto-build spatial NEAR relations
            phase = IndexerPhase.LINK
            links_built = self._auto_link_spatial()

            # Phase 4: QUERY - process is handled on-demand, no batch needed
            phase = IndexerPhase.QUERY

            # Phase 5: EVOLVE - decay stale relations
            phase = IndexerPhase.EVOLVE
            decayed = self._decay_relations()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            self._stats.total_entities = len(self._entities)
            self._stats.total_relations = len(self._relations)

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "ingested": ingested,
                "links_built": links_built,
                "relations_decayed": decayed,
                "total_entities": len(self._entities),
                "total_relations": len(self._relations),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles with simulated entities and relations."""
        with self._lock:
            import random
            categories = list(EntityCategory)
            relation_types = list(RelationType)
            initial_entities = len(self._entities)

            for c in range(cycles):
                # Add a few random entities
                for _ in range(random.randint(2, 5)):
                    eid = f"sim_ent_{initial_entities + c}_{random.randint(0, 9999)}"
                    cat = random.choice(categories)
                    pos = (
                        round(random.uniform(-50, 50), 1),
                        round(random.uniform(-50, 50), 1),
                        round(random.uniform(0, 10), 1),
                    )
                    tags = random.sample(["dangerous", "valuable", "fragile", "heavy",
                                          "magical", "ancient", "hidden"], k=random.randint(1, 3))
                    self.register_entity(
                        entity_id=eid,
                        name=f"SimEntity_{eid[-4:]}",
                        category=cat.value,
                        position=pos,
                        tags=tags,
                        semantic_roles=random.sample(["obstacle", "resource", "landmark",
                                                       "quest_target", "decoration"], k=random.randint(0, 2)),
                    )

                # Add some relations
                entity_ids = list(self._entities.keys())
                if len(entity_ids) >= 2:
                    for _ in range(random.randint(1, 3)):
                        src = random.choice(entity_ids)
                        tgt = random.choice(entity_ids)
                        if src != tgt:
                            rt = random.choice(relation_types)
                            self.add_relation(src, tgt, rt.value, weight=random.uniform(0.3, 1.0))

                self.run_cycle()

            return {
                "cycles_run": cycles,
                "entities_added": len(self._entities) - initial_entities,
                "total_entities": len(self._entities),
                "total_relations": len(self._relations),
            }

    # -------------------------------------------------------------------------
    # Status and Accessors
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the semantic indexer."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_entities": len(self._entities),
                "total_relations": len(self._relations),
                "pending_ingest": len(self._pending_ingest),
                "stats": {
                    "total_entities": self._stats.total_entities,
                    "total_relations": self._stats.total_relations,
                    "total_queries": self._stats.total_queries,
                    "total_cycles": self._stats.total_cycles,
                    "total_links_built": self._stats.total_links_built,
                    "total_relations_decayed": self._stats.total_relations_decayed,
                    "total_merges": self._stats.total_merges,
                    "avg_query_time_ms": self._stats.avg_query_time_ms,
                    "category_distribution": dict(self._stats.category_distribution),
                    "relation_distribution": dict(self._stats.relation_distribution),
                },
            }

    def get_entities(self, limit: int = 20, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get a list of indexed entities."""
        with self._lock:
            cat_filter = self._resolve_category(category) if category else None
            entities = list(self._entities.values())
            if cat_filter:
                entities = [e for e in entities if e.category == cat_filter]
            entities = entities[:limit]
            return [self._entity_to_dict(e) for e in entities]

    def get_relations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get a list of indexed relations."""
        with self._lock:
            relations = list(self._relations.values())[:limit]
            return [self._relation_to_dict(r) for r in relations]

    def get_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent query history."""
        with self._lock:
            queries = list(self._query_history)[-limit:]
            return [
                {
                    "query_id": q.query_id,
                    "query_text": q.query_text,
                    "intent": q.intent,
                    "result_count": q.result_count,
                    "timestamp": q.timestamp,
                }
                for q in reversed(queries)
            ]

    def reset(self) -> Dict[str, Any]:
        """Reset the semantic indexer to initial state."""
        with self._lock:
            self._entities.clear()
            self._relations.clear()
            self._spatial_index.clear()
            self._tag_index.clear()
            self._query_history.clear()
            self._pending_ingest.clear()
            self._cycle_count = 0
            self._stats = IndexerStats()
            self._active = False
            logger.info("AgentSemanticWorldIndexer reset")
            return {"reset": True, "message": "Semantic world indexer reset"}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _resolve_category(self, category: str) -> EntityCategory:
        """Resolve a string to an EntityCategory (case-insensitive)."""
        for cat in EntityCategory:
            if cat.value == category.lower() or cat.name.lower() == category.lower():
                return cat
        return EntityCategory.UNKNOWN

    def _resolve_relation(self, relation: str) -> Optional[RelationType]:
        """Resolve a string to a RelationType (case-insensitive)."""
        for rt in RelationType:
            if rt.value == relation.lower() or rt.name.lower() == relation.lower():
                return rt
        return None

    def _update_spatial_index(self, entity_id: str, position: Tuple[float, float, float]) -> None:
        """Update the spatial grid index for an entity."""
        cell = self._position_to_cell(position)
        # Remove from old cells
        for cells in self._spatial_index.values():
            cells.discard(entity_id)
        self._spatial_index[cell].add(entity_id)

    def _position_to_cell(self, pos: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """Convert a position to a spatial grid cell."""
        cell_size = 10
        return (
            int(pos[0]) // cell_size,
            int(pos[1]) // cell_size,
            int(pos[2]) // cell_size,
        )

    def _distance(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        """Euclidean distance between two 3D points."""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

    def _auto_link_spatial(self) -> int:
        """Automatically create NEAR relations for spatially close entities."""
        links = 0
        entity_list = list(self._entities.values())
        for i, a in enumerate(entity_list):
            for b in entity_list[i + 1:]:
                dist = self._distance(a.position, b.position)
                if dist <= self.NEAR_DISTANCE:
                    weight = max(0.1, 1.0 - dist / self.NEAR_DISTANCE)
                    rel_id_a = f"{a.entity_id}->{b.entity_id}:near"
                    rel_id_b = f"{b.entity_id}->{a.entity_id}:near"
                    if rel_id_a not in self._relations:
                        self._relations[rel_id_a] = SemanticRelation(
                            source_id=a.entity_id,
                            target_id=b.entity_id,
                            relation=RelationType.NEAR,
                            weight=weight,
                            metadata={"distance": round(dist, 2)},
                        )
                        links += 1
                    if rel_id_b not in self._relations:
                        self._relations[rel_id_b] = SemanticRelation(
                            source_id=b.entity_id,
                            target_id=a.entity_id,
                            relation=RelationType.NEAR,
                            weight=weight,
                            metadata={"distance": round(dist, 2)},
                        )
                        links += 1
        self._stats.total_links_built += links
        return links

    def _decay_relations(self) -> int:
        """Decay and prune stale relations."""
        now = time.time()
        to_remove: List[str] = []
        for rid, rel in self._relations.items():
            if now - rel.created_at > self.DECAY_TIMEOUT:
                rel.weight *= 0.5
                if rel.weight < self.MIN_RELATION_WEIGHT:
                    to_remove.append(rid)
        for rid in to_remove:
            del self._relations[rid]
        self._stats.total_relations_decayed += len(to_remove)
        return len(to_remove)

    def _update_distributions(self) -> None:
        """Update category and relation distribution stats."""
        cat_dist: Dict[str, int] = defaultdict(int)
        for e in self._entities.values():
            cat_dist[e.category.value] += 1
        self._stats.category_distribution = dict(cat_dist)

        rel_dist: Dict[str, int] = defaultdict(int)
        for r in self._relations.values():
            rel_dist[r.relation.value] += 1
        self._stats.relation_distribution = dict(rel_dist)

    def _get_entity_relations(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relations for an entity."""
        result: List[Dict[str, Any]] = []
        for rel in self._relations.values():
            if rel.source_id == entity_id or rel.target_id == entity_id:
                result.append(self._relation_to_dict(rel))
        return result[:10]  # limit to prevent huge payloads

    def _entity_to_dict(self, entity: SemanticEntity) -> Dict[str, Any]:
        """Convert a SemanticEntity to a dictionary."""
        return {
            "entity_id": entity.entity_id,
            "name": entity.name,
            "category": entity.category.value,
            "position": list(entity.position),
            "tags": sorted(entity.tags),
            "properties": entity.properties,
            "semantic_roles": sorted(entity.semantic_roles),
            "last_updated": entity.last_updated,
        }

    def _relation_to_dict(self, rel: SemanticRelation) -> Dict[str, Any]:
        """Convert a SemanticRelation to a dictionary."""
        return {
            "relation_id": f"{rel.source_id}->{rel.target_id}:{rel.relation.value}",
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "relation": rel.relation.value,
            "weight": round(rel.weight, 3),
            "metadata": rel.metadata,
            "created_at": rel.created_at,
        }
