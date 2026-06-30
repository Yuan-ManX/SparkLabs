"""
SparkLabs Engine - Scene Query

Declarative query language for scene state. Allows AI agents and tools to
query the scene graph through a unified interface without knowledge of its
internal structure. Supports component-based predicates, tag lookups,
spatial region queries, and compound expressions with AND/OR/NOT logic.

The query engine maintains an in-memory index of entities, their components,
tags, and spatial positions. External systems register entities through
the upsert API; queries are evaluated against this index. Results are
returned as a list of matching entity records with their relevant components.

Query expressions can be constructed programmatically through the dataclass
API or parsed from a simple text syntax for natural integration with
agent intent systems.

Architecture:
  SceneQueryEngine (Singleton)
    |-- ComponentPredicate  (one component property comparison)
    |-- SpatialRegion       (aabb / sphere / point / radius shape)
    |-- QueryClause          (one atomic match condition)
    |-- QueryExpression      (recursive AND/OR/NOT tree of clauses)
    |-- QueryOrder           (ordering directive for results)
    |-- Query                (top-level query description)
    |-- EntityRecord         (one indexed entity)
    |-- QueryResult          (one query execution outcome)
    |-- SceneQuerySnapshot   (point-in-time index summary)
"""

from __future__ import annotations

import datetime
import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class QueryOperator(Enum):
    """Comparison operators for component predicates."""
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class LogicOperator(Enum):
    """Boolean combinators for query expressions."""
    AND = "and"
    OR = "or"
    NOT = "not"


class QueryClauseKind(Enum):
    """The kind of condition expressed by a single query clause."""
    COMPONENT_PREDICATE = "component_predicate"
    TAG_MATCH = "tag_match"
    SPATIAL_REGION = "spatial_region"
    ENTITY_ID = "entity_id"
    ENTITY_TYPE = "entity_type"
    CUSTOM = "custom"


class SpatialShape(Enum):
    """Geometric shapes used for spatial region clauses."""
    AABB = "aabb"
    SPHERE = "sphere"
    POINT = "point"
    RADIUS = "radius"


class SortOrder(Enum):
    """Sort direction for query results."""
    ASCENDING = "ascending"
    DESCENDING = "descending"


class SortField(Enum):
    """Field on which query results may be ordered."""
    ENTITY_ID = "entity_id"
    ENTITY_TYPE = "entity_type"
    DISTANCE = "distance"
    PROPERTY = "property"
    INDEX = "index"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ComponentPredicate:
    """A single component property comparison.

    Attributes:
        component_name: Name of the component to inspect.
        property_name: Property path within the component. When empty and the
            operator is EXISTS, the predicate matches on component presence.
        operator: Comparison operator to apply.
        value: Comparison value. Ignored for EXISTS / NOT_EXISTS.
    """
    component_name: str = ""
    property_name: str = ""
    operator: QueryOperator = QueryOperator.EQ
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "property_name": self.property_name,
            "operator": self.operator.value,
            "value": self.value,
        }


@dataclass
class SpatialRegion:
    """A geometric region used for spatial queries.

    Attributes:
        shape: The shape of the region.
        center: Center point (x, y) of the region.
        half_extents: Half-size (hx, hy) for AABB regions.
        radius: Radius for sphere / radius regions.
        property_name: Name of the entity attribute that holds the position.
            Defaults to "position", which reads the entity's position field.
    """
    shape: SpatialShape = SpatialShape.SPHERE
    center: Tuple[float, float] = (0.0, 0.0)
    half_extents: Optional[Tuple[float, float]] = None
    radius: Optional[float] = None
    property_name: str = "position"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shape": self.shape.value,
            "center": list(self.center),
            "half_extents": list(self.half_extents) if self.half_extents else None,
            "radius": self.radius,
            "property_name": self.property_name,
        }


@dataclass
class QueryClause:
    """One atomic match condition.

    Attributes:
        id: Auto-generated unique identifier.
        kind: The kind of condition.
        predicate: Component predicate (for COMPONENT_PREDICATE clauses).
        tags: Tag list (for TAG_MATCH clauses).
        spatial: Spatial region (for SPATIAL_REGION clauses).
        entity_id: Entity identifier (for ENTITY_ID clauses).
        entity_type: Entity type (for ENTITY_TYPE clauses).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: QueryClauseKind = QueryClauseKind.COMPONENT_PREDICATE
    predicate: Optional[ComponentPredicate] = None
    tags: Optional[List[str]] = None
    spatial: Optional[SpatialRegion] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "predicate": self.predicate.to_dict() if self.predicate else None,
            "tags": list(self.tags) if self.tags else None,
            "spatial": self.spatial.to_dict() if self.spatial else None,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
        }


@dataclass
class QueryExpression:
    """A recursive boolean expression over query clauses.

    Attributes:
        id: Auto-generated unique identifier.
        logic: Combinator applied to clauses and children.
        clauses: Clauses combined by the logic operator.
        children: Nested expressions combined by the logic operator.
        negated: When True, the result of the expression is inverted.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    logic: LogicOperator = LogicOperator.AND
    clauses: List[QueryClause] = field(default_factory=list)
    children: List["QueryExpression"] = field(default_factory=list)
    negated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "logic": self.logic.value,
            "clauses": [c.to_dict() for c in self.clauses],
            "children": [ch.to_dict() for ch in self.children],
            "negated": self.negated,
        }


@dataclass
class QueryOrder:
    """Ordering directive for query results.

    Attributes:
        field: Field to sort by.
        order: Sort direction.
        property_name: For PROPERTY sort, a "Component.property" path.
    """
    field: SortField = SortField.INDEX
    order: SortOrder = SortOrder.ASCENDING
    property_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field.value,
            "order": self.order.value,
            "property_name": self.property_name,
        }


@dataclass
class Query:
    """A top-level query description.

    Attributes:
        id: Auto-generated unique identifier.
        expression: Boolean expression evaluated against each entity.
        order_by: Optional ordering directive.
        limit: Optional maximum number of returned entities.
        offset: Number of entities to skip before returning results.
        include_components: Optional whitelist of component names to include
            in the result. When None, all components are included.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    expression: QueryExpression = field(default_factory=QueryExpression)
    order_by: Optional[QueryOrder] = None
    limit: Optional[int] = None
    offset: int = 0
    include_components: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "expression": self.expression.to_dict(),
            "order_by": self.order_by.to_dict() if self.order_by else None,
            "limit": self.limit,
            "offset": self.offset,
            "include_components": list(self.include_components) if self.include_components else None,
        }


@dataclass
class EntityRecord:
    """A single indexed entity.

    Attributes:
        id: Entity identifier.
        type: Entity type label.
        components: Mapping of component name to its property dict.
        tags: Tags attached to the entity.
        position: Spatial position (x, y), or None when unknown.
    """
    id: str = ""
    type: str = ""
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    position: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "components": {k: dict(v) for k, v in self.components.items()},
            "tags": list(self.tags),
            "position": list(self.position) if self.position else None,
        }


@dataclass
class QueryResult:
    """The outcome of one query execution.

    Attributes:
        query_id: Identifier of the query that produced this result.
        matched_count: Total number of matching entities (before limit/offset).
        entities: Entity records returned for this page.
        execution_time_ms: Wall-clock execution time in milliseconds.
        cache_hit: Whether the result was served from the cache.
    """
    query_id: str = ""
    matched_count: int = 0
    entities: List[EntityRecord] = field(default_factory=list)
    execution_time_ms: float = 0.0
    cache_hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "matched_count": self.matched_count,
            "entities": [e.to_dict() for e in self.entities],
            "execution_time_ms": self.execution_time_ms,
            "cache_hit": self.cache_hit,
        }


@dataclass
class SceneQuerySnapshot:
    """Point-in-time summary of the query index.

    Attributes:
        entity_count: Number of indexed entities.
        component_count: Total components across all entities.
        tag_count: Total tags across all entities.
        query_count: Total queries executed since startup.
        stats: Additional statistics.
        timestamp: Snapshot time (seconds since epoch).
    """
    entity_count: int = 0
    component_count: int = 0
    tag_count: int = 0
    query_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_count": self.entity_count,
            "component_count": self.component_count,
            "tag_count": self.tag_count,
            "query_count": self.query_count,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


# =============================================================================
# Scene Query Engine (Singleton)
# =============================================================================


class SceneQueryEngine:
    """Singleton scene query index with a declarative query language.

    Maintains an in-memory index of entities, their components, tags, and
    spatial positions. Supports component predicates, tag matches, spatial
    region queries, entity id/type lookups, and compound boolean expressions.
    Results can be ordered, limited, and projected to a subset of components.
    All public methods are thread-safe.
    """

    _instance: Optional["SceneQueryEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 500

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._entities: Dict[str, EntityRecord] = {}
        self._entity_order: List[str] = []
        self._query_cache: Dict[str, QueryResult] = {}
        self._history: List[QueryResult] = []
        self._handlers: Dict[str, Callable[[QueryClause, EntityRecord], bool]] = {}
        # Counters
        self._query_count: int = 0
        self._total_query_time_ms: float = 0.0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._last_query_at: Optional[str] = None
        self._seed_default_entities()

    @classmethod
    def get_instance(cls) -> "SceneQueryEngine":
        """Return the singleton SceneQueryEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_default_entities(self) -> None:
        """Populate the index with a small default scene."""
        self.upsert_entity(
            "player",
            entity_type="character",
            components={
                "Transform": {"x": 0, "y": 0},
                "Health": {"hp": 100, "max_hp": 100},
            },
            tags=["player", "alive"],
            position=(0.0, 0.0),
        )
        self.upsert_entity(
            "goblin-1",
            entity_type="goblin",
            components={
                "Transform": {"x": 50, "y": 30},
                "Health": {"hp": 30, "max_hp": 30},
                "AI": {"state": "patrol"},
            },
            tags=["enemy", "alive"],
            position=(50.0, 30.0),
        )
        self.upsert_entity(
            "goblin-2",
            entity_type="goblin",
            components={
                "Transform": {"x": 80, "y": 60},
                "Health": {"hp": 25, "max_hp": 30},
                "AI": {"state": "chase"},
            },
            tags=["enemy", "alive"],
            position=(80.0, 60.0),
        )
        self.upsert_entity(
            "treasure-chest",
            entity_type="item",
            components={
                "Transform": {"x": 100, "y": 100},
                "Item": {"value": 500, "rarity": "rare"},
            },
            tags=["loot", "interactable"],
            position=(100.0, 100.0),
        )
        self.upsert_entity(
            "wall-1",
            entity_type="structure",
            components={
                "Transform": {"x": 200, "y": 200},
                "Collider": {"width": 50, "height": 50},
            },
            tags=["solid"],
            position=(200.0, 200.0),
        )

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def upsert_entity(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
        components: Optional[Dict[str, Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        position: Optional[Tuple[float, float]] = None,
    ) -> EntityRecord:
        """Register or update an entity in the index."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                record = EntityRecord(id=entity_id)
                self._entities[entity_id] = record
                self._entity_order.append(entity_id)
            if entity_type is not None:
                record.type = entity_type
            if components is not None:
                record.components = {k: dict(v) for k, v in components.items()}
            if tags is not None:
                record.tags = list(tags)
            if position is not None:
                record.position = (float(position[0]), float(position[1]))
            self._invalidate_cache()
            return self._copy_record(record)

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the index. Returns True if removed."""
        with self._instance_lock:
            if entity_id not in self._entities:
                return False
            del self._entities[entity_id]
            if entity_id in self._entity_order:
                self._entity_order.remove(entity_id)
            self._invalidate_cache()
            return True

    def get_entity(self, entity_id: str) -> Optional[EntityRecord]:
        """Return a copy of the entity record, or None if not found."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return None
            return self._copy_record(record)

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[EntityRecord]:
        """List entities, optionally filtered by type and/or tag."""
        with self._instance_lock:
            results: List[EntityRecord] = []
            for eid in self._entity_order:
                record = self._entities.get(eid)
                if record is None:
                    continue
                if entity_type is not None and record.type != entity_type:
                    continue
                if tag is not None and tag not in record.tags:
                    continue
                results.append(self._copy_record(record))
                if len(results) >= limit:
                    break
            return results

    def add_tag(self, entity_id: str, tag: str) -> bool:
        """Attach a tag to an entity. Returns True on success."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return False
            if tag not in record.tags:
                record.tags.append(tag)
                self._invalidate_cache()
            return True

    def remove_tag(self, entity_id: str, tag: str) -> bool:
        """Remove a tag from an entity. Returns True if removed."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return False
            if tag in record.tags:
                record.tags.remove(tag)
                self._invalidate_cache()
                return True
            return False

    def update_position(self, entity_id: str, x: float, y: float) -> bool:
        """Update the spatial position of an entity."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return False
            record.position = (float(x), float(y))
            self._invalidate_cache()
            return True

    def update_component(
        self,
        entity_id: str,
        component_name: str,
        component_data: Dict[str, Any],
    ) -> bool:
        """Insert or replace a component on an entity."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return False
            record.components[component_name] = dict(component_data)
            self._invalidate_cache()
            return True

    def remove_component(self, entity_id: str, component_name: str) -> bool:
        """Remove a component from an entity. Returns True if removed."""
        with self._instance_lock:
            record = self._entities.get(entity_id)
            if record is None:
                return False
            if component_name in record.components:
                del record.components[component_name]
                self._invalidate_cache()
                return True
            return False

    # ------------------------------------------------------------------
    # Query Evaluation
    # ------------------------------------------------------------------

    def query(self, query_obj: Query) -> QueryResult:
        """Evaluate a Query against the index and return the result."""
        with self._instance_lock:
            start = time.perf_counter()
            cache_key = self._cache_key(query_obj)
            cached = self._query_cache.get(cache_key)
            if cached is not None:
                elapsed = (time.perf_counter() - start) * 1000.0
                self._cache_hits += 1
                result = QueryResult(
                    query_id=query_obj.id,
                    matched_count=cached.matched_count,
                    entities=[self._copy_record(e) for e in cached.entities],
                    execution_time_ms=elapsed,
                    cache_hit=True,
                )
                self._record_history(result)
                self._touch_query_stats(elapsed)
                return result

            self._cache_misses += 1
            matched: List[EntityRecord] = []
            expression = query_obj.expression
            for eid in self._entity_order:
                record = self._entities.get(eid)
                if record is None:
                    continue
                if self.evaluate_expression(expression, record):
                    matched.append(record)
            total = len(matched)
            matched = self._apply_ordering(matched, query_obj)

            offset = max(0, query_obj.offset)
            if offset:
                matched = matched[offset:]
            if query_obj.limit is not None:
                matched = matched[: max(0, query_obj.limit)]

            include = query_obj.include_components
            projected = [self._project_record(e, include) for e in matched]

            elapsed = (time.perf_counter() - start) * 1000.0
            result = QueryResult(
                query_id=query_obj.id,
                matched_count=total,
                entities=projected,
                execution_time_ms=elapsed,
                cache_hit=False,
            )
            self._query_cache[cache_key] = result
            self._record_history(result)
            self._touch_query_stats(elapsed)
            return result

    def query_by_component(
        self,
        component_name: str,
        property_name: Optional[str] = None,
        operator: Optional[QueryOperator] = None,
        value: Any = None,
    ) -> QueryResult:
        """Convenience query over a single component predicate."""
        if operator is None:
            predicate = ComponentPredicate(
                component_name=component_name,
                property_name=property_name or "",
                operator=QueryOperator.EXISTS,
                value=value,
            )
        else:
            predicate = ComponentPredicate(
                component_name=component_name,
                property_name=property_name or "",
                operator=operator,
                value=value,
            )
        clause = QueryClause(
            kind=QueryClauseKind.COMPONENT_PREDICATE,
            predicate=predicate,
        )
        expression = QueryExpression(
            logic=LogicOperator.AND,
            clauses=[clause],
        )
        return self.query(Query(expression=expression))

    def query_by_tag(self, tags: List[str], match_any: bool = True) -> QueryResult:
        """Convenience query over entity tags.

        Args:
            tags: Tags to match.
            match_any: True means OR semantics (any tag), False means AND (all tags).
        """
        if not tags:
            expression = QueryExpression(logic=LogicOperator.AND, clauses=[])
        elif len(tags) == 1:
            clause = QueryClause(
                kind=QueryClauseKind.TAG_MATCH,
                tags=[tags[0]],
            )
            expression = QueryExpression(
                logic=LogicOperator.AND,
                clauses=[clause],
            )
        else:
            terms = []
            for tag in tags:
                clause = QueryClause(
                    kind=QueryClauseKind.TAG_MATCH,
                    tags=[tag],
                )
                terms.append(QueryExpression(
                    logic=LogicOperator.AND,
                    clauses=[clause],
                ))
            logic = LogicOperator.OR if match_any else LogicOperator.AND
            expression = QueryExpression(logic=logic, children=terms)
        return self.query(Query(expression=expression))

    def query_by_region(
        self,
        shape: Union[SpatialShape, str],
        center: Tuple[float, float],
        half_extents: Optional[Tuple[float, float]] = None,
        radius: Optional[float] = None,
    ) -> QueryResult:
        """Convenience spatial query."""
        region = SpatialRegion(
            shape=self._normalize_shape(shape),
            center=(float(center[0]), float(center[1])),
            half_extents=(float(half_extents[0]), float(half_extents[1])) if half_extents else None,
            radius=float(radius) if radius is not None else None,
        )
        clause = QueryClause(
            kind=QueryClauseKind.SPATIAL_REGION,
            spatial=region,
        )
        expression = QueryExpression(
            logic=LogicOperator.AND,
            clauses=[clause],
        )
        return self.query(Query(expression=expression))

    def query_by_entity_id(self, entity_id: str) -> QueryResult:
        """Convenience query by entity identifier."""
        clause = QueryClause(
            kind=QueryClauseKind.ENTITY_ID,
            entity_id=entity_id,
        )
        expression = QueryExpression(
            logic=LogicOperator.AND,
            clauses=[clause],
        )
        return self.query(Query(expression=expression))

    def query_by_entity_type(self, entity_type: str) -> QueryResult:
        """Convenience query by entity type."""
        clause = QueryClause(
            kind=QueryClauseKind.ENTITY_TYPE,
            entity_type=entity_type,
        )
        expression = QueryExpression(
            logic=LogicOperator.AND,
            clauses=[clause],
        )
        return self.query(Query(expression=expression))

    def evaluate_expression(self, expression: QueryExpression, entity: EntityRecord) -> bool:
        """Evaluate a QueryExpression against a single entity."""
        if expression is None:
            return True
        logic = expression.logic
        clauses_match = all(
            self.evaluate_clause(c, entity) for c in expression.clauses
        )
        children_match = all(
            self.evaluate_expression(ch, entity) for ch in expression.children
        )
        has_terms = bool(expression.clauses) or bool(expression.children)

        if logic == LogicOperator.AND:
            result = clauses_match and children_match if has_terms else True
        elif logic == LogicOperator.OR:
            result = (
                any(self.evaluate_clause(c, entity) for c in expression.clauses)
                or any(self.evaluate_expression(ch, entity) for ch in expression.children)
            )
        elif logic == LogicOperator.NOT:
            result = not (clauses_match and children_match)
        else:
            result = clauses_match and children_match

        if expression.negated:
            result = not result
        return result

    def evaluate_clause(self, clause: QueryClause, entity: EntityRecord) -> bool:
        """Evaluate a single QueryClause against an entity."""
        if clause is None:
            return False
        kind = clause.kind
        if kind == QueryClauseKind.COMPONENT_PREDICATE:
            if clause.predicate is None:
                return False
            return self.evaluate_predicate(clause.predicate, entity)
        if kind == QueryClauseKind.TAG_MATCH:
            if not clause.tags:
                return False
            return all(tag in entity.tags for tag in clause.tags)
        if kind == QueryClauseKind.SPATIAL_REGION:
            if clause.spatial is None:
                return False
            return self.evaluate_spatial(clause.spatial, entity)
        if kind == QueryClauseKind.ENTITY_ID:
            return entity.id == (clause.entity_id or "")
        if kind == QueryClauseKind.ENTITY_TYPE:
            return entity.type == (clause.entity_type or "")
        if kind == QueryClauseKind.CUSTOM:
            handler = self._handlers.get(clause.kind.value)
            if handler is None:
                return False
            try:
                return bool(handler(clause, entity))
            except Exception:
                return False
        return False

    def evaluate_predicate(self, predicate: ComponentPredicate, entity: EntityRecord) -> bool:
        """Evaluate a ComponentPredicate against an entity."""
        if predicate is None:
            return False
        component = entity.components.get(predicate.component_name)
        if component is None:
            return False
        op = predicate.operator
        prop = predicate.property_name
        value = predicate.value

        if op == QueryOperator.EXISTS:
            if not prop:
                return True
            return prop in component
        if op == QueryOperator.NOT_EXISTS:
            if not prop:
                return False
            return prop not in component

        if not prop or prop not in component:
            return False
        actual = component[prop]

        try:
            if op == QueryOperator.EQ:
                return actual == value
            if op == QueryOperator.NEQ:
                return actual != value
            if op == QueryOperator.LT:
                return actual < value
            if op == QueryOperator.LTE:
                return actual <= value
            if op == QueryOperator.GT:
                return actual > value
            if op == QueryOperator.GTE:
                return actual >= value
            if op == QueryOperator.CONTAINS:
                return value in actual
            if op == QueryOperator.STARTS_WITH:
                return str(actual).startswith(str(value))
            if op == QueryOperator.ENDS_WITH:
                return str(actual).endswith(str(value))
            if op == QueryOperator.IN:
                return actual in value
            if op == QueryOperator.NOT_IN:
                return actual not in value
        except TypeError:
            return False
        return False

    def evaluate_spatial(self, region: SpatialRegion, entity: EntityRecord) -> bool:
        """Evaluate a SpatialRegion against an entity."""
        if region is None or entity.position is None:
            return False
        pos_x, pos_y = float(entity.position[0]), float(entity.position[1])
        cx, cy = float(region.center[0]), float(region.center[1])
        shape = region.shape

        if shape == SpatialShape.AABB:
            if region.half_extents is None:
                return False
            hx, hy = float(region.half_extents[0]), float(region.half_extents[1])
            return (cx - hx <= pos_x <= cx + hx) and (cy - hy <= pos_y <= cy + hy)

        if shape in (SpatialShape.SPHERE, SpatialShape.RADIUS):
            if region.radius is None:
                return False
            dx = pos_x - cx
            dy = pos_y - cy
            return (dx * dx + dy * dy) <= (float(region.radius) ** 2)

        if shape == SpatialShape.POINT:
            eps = 1e-6
            return abs(pos_x - cx) < eps and abs(pos_y - cy) < eps

        return False

    # ------------------------------------------------------------------
    # Custom Handlers
    # ------------------------------------------------------------------

    def register_query_handler(
        self,
        kind: Union[QueryClauseKind, str],
        handler: Callable[[QueryClause, EntityRecord], bool],
    ) -> None:
        """Register a handler for a custom clause kind."""
        key = kind.value if isinstance(kind, QueryClauseKind) else str(kind)
        with self._instance_lock:
            self._handlers[key] = handler

    # ------------------------------------------------------------------
    # History, Cache, Status
    # ------------------------------------------------------------------

    def list_queries(self, limit: int = 50) -> List[QueryResult]:
        """Return recent query results (most recent first)."""
        with self._instance_lock:
            if limit <= 0:
                return []
            return list(reversed(self._history[-limit:]))

    def clear_cache(self) -> None:
        """Clear the query result cache."""
        with self._instance_lock:
            self._query_cache.clear()

    def get_status(self) -> Dict[str, Any]:
        """Return runtime statistics about the index."""
        with self._instance_lock:
            total_components = sum(len(r.components) for r in self._entities.values())
            total_tags = sum(len(r.tags) for r in self._entities.values())
            return {
                "total_entities": len(self._entities),
                "total_components": total_components,
                "total_tags": total_tags,
                "total_queries": self._query_count,
                "total_query_time_ms": self._total_query_time_ms,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "last_query_at": self._last_query_at,
            }

    def get_snapshot(self) -> SceneQuerySnapshot:
        """Return a point-in-time snapshot of the index."""
        with self._instance_lock:
            status = self.get_status()
            return SceneQuerySnapshot(
                entity_count=status["total_entities"],
                component_count=status["total_components"],
                tag_count=status["total_tags"],
                query_count=status["total_queries"],
                stats=status,
                timestamp=time.time(),
            )

    def reset(self) -> None:
        """Clear all entities, history, cache, and counters, then re-seed defaults."""
        with self._instance_lock:
            self._entities.clear()
            self._entity_order.clear()
            self._query_cache.clear()
            self._history.clear()
            self._query_count = 0
            self._total_query_time_ms = 0.0
            self._cache_hits = 0
            self._cache_misses = 0
            self._last_query_at = None
            self._seed_default_entities()

    # ------------------------------------------------------------------
    # Text Query Parsing
    # ------------------------------------------------------------------

    def parse(self, text: str) -> Query:
        """Parse a simple text query syntax into a Query object.

        Supported forms:
            component:Transform where x > 100
            tag:enemy
            region:sphere center=10,20 radius=50
            entity:abc-123
            type:goblin

        Clauses may be joined with ``and`` / ``or`` and prefixed with ``not``::

            component:Health where hp < 50 and tag:enemy
        """
        if not text or not text.strip():
            return Query()
        words = text.strip().split()

        groups: List[Tuple[bool, List[str]]] = []
        ops: List[str] = []
        current: List[str] = []
        current_negated = False
        for word in words:
            lowered = word.lower()
            if lowered in ("and", "or") and current:
                groups.append((current_negated, current))
                ops.append(lowered)
                current = []
                current_negated = False
            elif lowered == "not" and not current:
                current_negated = True
            else:
                current.append(word)
        if current:
            groups.append((current_negated, current))

        terms: List[QueryExpression] = []
        for negated, group_words in groups:
            clause = self._parse_clause_group(group_words)
            if clause is None:
                continue
            terms.append(QueryExpression(
                logic=LogicOperator.AND,
                clauses=[clause],
                negated=negated,
            ))

        if not terms:
            return Query()
        if len(terms) == 1:
            expression = terms[0]
        elif ops and all(op == "and" for op in ops):
            expression = QueryExpression(logic=LogicOperator.AND, children=terms)
        elif ops and all(op == "or" for op in ops):
            expression = QueryExpression(logic=LogicOperator.OR, children=terms)
        else:
            expression = terms[0]
            for idx, term in enumerate(terms[1:]):
                logic = LogicOperator.AND if ops[idx] == "and" else LogicOperator.OR
                expression = QueryExpression(logic=logic, children=[expression, term])

        return Query(expression=expression)

    def _parse_clause_group(self, words: List[str]) -> Optional[QueryClause]:
        """Parse one clause group (e.g. ``component:Health where hp < 50``)."""
        if not words:
            return None
        head = words[0]

        if head.startswith("component:"):
            name = head[len("component:"):]
            if "where" in words:
                where_idx = words.index("where")
                rest = words[where_idx + 1:]
                predicate = self._parse_where_clause(name, rest)
            else:
                predicate = ComponentPredicate(
                    component_name=name,
                    property_name="",
                    operator=QueryOperator.EXISTS,
                )
            return QueryClause(
                kind=QueryClauseKind.COMPONENT_PREDICATE,
                predicate=predicate,
            )

        if head.startswith("tag:"):
            value = head[len("tag:"):]
            tags = [t for t in value.split(",") if t]
            return QueryClause(kind=QueryClauseKind.TAG_MATCH, tags=tags)

        if head.startswith("region:"):
            shape_name = head[len("region:"):]
            region = SpatialRegion(shape=self._normalize_shape(shape_name))
            for token in words[1:]:
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                if key == "center":
                    region.center = self._parse_pair(value)
                elif key in ("half_extents", "half"):
                    region.half_extents = self._parse_pair(value)
                elif key == "radius":
                    region.radius = float(value)
            return QueryClause(kind=QueryClauseKind.SPATIAL_REGION, spatial=region)

        if head.startswith("entity:"):
            entity_id = head[len("entity:"):]
            return QueryClause(kind=QueryClauseKind.ENTITY_ID, entity_id=entity_id)

        if head.startswith("type:"):
            entity_type = head[len("type:"):]
            return QueryClause(kind=QueryClauseKind.ENTITY_TYPE, entity_type=entity_type)

        return None

    def _parse_where_clause(self, component_name: str, tokens: List[str]) -> ComponentPredicate:
        """Parse the ``<property> <operator> <value>`` tail of a component clause."""
        if len(tokens) >= 1:
            prop = tokens[0]
        else:
            return ComponentPredicate(
                component_name=component_name,
                property_name="",
                operator=QueryOperator.EXISTS,
            )
        op = QueryOperator.EQ
        value: Any = None
        if len(tokens) >= 2:
            op = self._parse_operator(tokens[1])
            if len(tokens) >= 3:
                value = self._parse_value(tokens[2], op)
        return ComponentPredicate(
            component_name=component_name,
            property_name=prop,
            operator=op,
            value=value,
        )

    def _parse_operator(self, token: str) -> QueryOperator:
        """Map a text operator token to a QueryOperator."""
        mapping = {
            "=": QueryOperator.EQ,
            "==": QueryOperator.EQ,
            "!=": QueryOperator.NEQ,
            "<>": QueryOperator.NEQ,
            "<": QueryOperator.LT,
            "<=": QueryOperator.LTE,
            ">": QueryOperator.GT,
            ">=": QueryOperator.GTE,
            "contains": QueryOperator.CONTAINS,
            "starts_with": QueryOperator.STARTS_WITH,
            "ends_with": QueryOperator.ENDS_WITH,
            "in": QueryOperator.IN,
            "not_in": QueryOperator.NOT_IN,
            "exists": QueryOperator.EXISTS,
            "not_exists": QueryOperator.NOT_EXISTS,
        }
        return mapping.get(token.lower(), QueryOperator.EQ)

    def _parse_value(self, token: str, op: QueryOperator) -> Any:
        """Parse a value token, honoring the operator for list values."""
        if op in (QueryOperator.IN, QueryOperator.NOT_IN):
            parts = [p for p in token.split(",") if p != ""]
            return [self._parse_scalar(p) for p in parts]
        return self._parse_scalar(token)

    @staticmethod
    def _parse_scalar(token: str) -> Any:
        """Parse a scalar value (int, float, bool, or string)."""
        lowered = token.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null" or lowered == "none":
            return None
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return token

    @staticmethod
    def _parse_pair(token: str) -> Tuple[float, float]:
        """Parse a ``x,y`` pair into a float tuple."""
        parts = [p for p in token.split(",") if p != ""]
        if len(parts) < 2:
            return (0.0, 0.0)
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            return (0.0, 0.0)

    @staticmethod
    def _normalize_shape(shape: Union[SpatialShape, str]) -> SpatialShape:
        """Normalize a shape argument (enum or string) to a SpatialShape."""
        if isinstance(shape, SpatialShape):
            return shape
        if isinstance(shape, str):
            token = shape.strip().lower()
            for candidate in SpatialShape:
                if candidate.value == token or candidate.name.lower() == token:
                    return candidate
        return SpatialShape.SPHERE

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _cache_key(self, query_obj: Query) -> str:
        """Compute a stable cache key for a query."""
        try:
            return json.dumps(query_obj.to_dict(), sort_keys=True, default=str)
        except (TypeError, ValueError):
            return str(query_obj.id)

    def _invalidate_cache(self) -> None:
        """Drop the query cache after an index mutation."""
        self._query_cache.clear()

    def _record_history(self, result: QueryResult) -> None:
        """Append a result to the bounded history."""
        self._history.append(result)
        if len(self._history) > self._MAX_HISTORY:
            del self._history[: len(self._history) - self._MAX_HISTORY]

    def _touch_query_stats(self, elapsed_ms: float) -> None:
        """Update query counters after an execution."""
        self._query_count += 1
        self._total_query_time_ms += elapsed_ms
        self._last_query_at = datetime.datetime.utcnow().isoformat()

    def _apply_ordering(self, entities: List[EntityRecord], query_obj: Query) -> List[EntityRecord]:
        """Apply the query's ordering directive to the matched entities."""
        order = query_obj.order_by
        if order is None:
            return list(entities)
        reverse = order.order == SortOrder.DESCENDING
        field = order.field

        if field == SortField.INDEX:
            ordered = sorted(
                entities,
                key=lambda e: self._entity_index(e.id),
                reverse=reverse,
            )
            return ordered
        if field == SortField.ENTITY_ID:
            return self._sorted_safe(entities, lambda e: e.id, reverse)
        if field == SortField.ENTITY_TYPE:
            return self._sorted_safe(entities, lambda e: e.type, reverse)
        if field == SortField.DISTANCE:
            cx, cy = self._reference_center(query_obj)
            return self._sorted_safe(
                entities, lambda e: self._distance(e, cx, cy), reverse
            )
        if field == SortField.PROPERTY:
            prop = order.property_name or ""
            return self._sorted_safe(
                entities, lambda e: self._property_value(e, prop), reverse
            )
        return list(entities)

    def _entity_index(self, entity_id: str) -> int:
        """Return the insertion index of an entity (for INDEX sort)."""
        try:
            return self._entity_order.index(entity_id)
        except ValueError:
            return len(self._entity_order)

    @staticmethod
    def _distance(entity: EntityRecord, cx: float, cy: float) -> float:
        """Return the distance from an entity to a reference point."""
        if entity.position is None:
            return float("inf")
        dx = float(entity.position[0]) - cx
        dy = float(entity.position[1]) - cy
        return math.sqrt(dx * dx + dy * dy)

    def _reference_center(self, query_obj: Query) -> Tuple[float, float]:
        """Return the spatial reference center for a DISTANCE sort."""
        center = self._find_spatial_center(query_obj.expression)
        if center is None:
            return (0.0, 0.0)
        return (float(center[0]), float(center[1]))

    def _find_spatial_center(self, expression: Optional[QueryExpression]) -> Optional[Tuple[float, float]]:
        """Search an expression tree for the first spatial clause's center."""
        if expression is None:
            return None
        for clause in expression.clauses:
            if clause.spatial is not None:
                return clause.spatial.center
        for child in expression.children:
            center = self._find_spatial_center(child)
            if center is not None:
                return center
        return None

    @staticmethod
    def _property_value(entity: EntityRecord, path: str) -> Any:
        """Read a ``Component.property`` value from an entity."""
        if not path:
            return None
        if "." in path:
            comp_name, prop = path.split(".", 1)
        else:
            comp_name, prop = path, ""
        component = entity.components.get(comp_name)
        if component is None:
            return None
        if not prop:
            return component
        return component.get(prop)

    @staticmethod
    def _sorted_safe(
        entities: List[EntityRecord],
        key_func: Callable[[EntityRecord], Any],
        reverse: bool,
    ) -> List[EntityRecord]:
        """Sort entities, falling back to string comparison on type errors."""
        try:
            return sorted(entities, key=key_func, reverse=reverse)
        except TypeError:
            return sorted(entities, key=lambda e: str(key_func(e)), reverse=reverse)

    def _copy_record(self, record: EntityRecord) -> EntityRecord:
        """Return a shallow-deep copy of an entity record."""
        return EntityRecord(
            id=record.id,
            type=record.type,
            components={k: dict(v) for k, v in record.components.items()},
            tags=list(record.tags),
            position=record.position,
        )

    def _project_record(
        self,
        record: EntityRecord,
        include: Optional[List[str]],
    ) -> EntityRecord:
        """Return a copy of the record, restricted to the listed components."""
        if include is None:
            return self._copy_record(record)
        return EntityRecord(
            id=record.id,
            type=record.type,
            components={
                name: dict(data)
                for name, data in record.components.items()
                if name in include
            },
            tags=list(record.tags),
            position=record.position,
        )


def get_scene_query_engine() -> SceneQueryEngine:
    """Return the singleton SceneQueryEngine instance."""
    return SceneQueryEngine.get_instance()
