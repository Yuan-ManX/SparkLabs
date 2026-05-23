"""
SparkLabs Agent - Knowledge Synthesis Engine

Cross-session knowledge aggregation, connection discovery, and summarization for
AI-native game creation. Collects fragments from agent sessions, synthesizes
insights, discovers latent cross-references, builds domain indices, and produces
distilled summaries of accumulated expertise across game development domains.

Architecture:
  KnowledgeSynthesisEngine (Singleton)
    |-- KnowledgeFragment (atomic unit of agent-produced knowledge)
    |-- SynthesisResult (aggregated insight bundle)
    |-- DomainIndex (domain-scoped retrieval structure)
    |-- CrossReference (inter-fragment relationship discovery)

Synthesis Modes: aggregate, summarize, connect, distill, refine
Knowledge Domains: game_design, code_generation, asset_creation, debugging,
                   testing, player_experience, optimization
Confidence Levels: low, medium, high, certain

Usage:
    engine = get_knowledge_synthesis()
    frag = engine.ingest_fragment("agent_level_designer", "BSP over midpoint.",
                                   domain="game_design", confidence="high")
    result = engine.synthesize(domain="game_design", mode="aggregate")
    xrefs = engine.cross_reference(fragment_ids=[frag.id])
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SynthesisMode(Enum):
    AGGREGATE = "aggregate"
    SUMMARIZE = "summarize"
    CONNECT = "connect"
    DISTILL = "distill"
    REFINE = "refine"


class KnowledgeDomain(Enum):
    GAME_DESIGN = "game_design"
    CODE_GENERATION = "code_generation"
    ASSET_CREATION = "asset_creation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    PLAYER_EXPERIENCE = "player_experience"
    OPTIMIZATION = "optimization"


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


@dataclass
class KnowledgeFragment:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_agent: str = ""
    content: str = ""
    domain: str = KnowledgeDomain.GAME_DESIGN.value
    confidence: str = ConfidenceLevel.MEDIUM.value
    tags: List[str] = field(default_factory=list)
    session_id: str = ""
    source_ids: List[str] = field(default_factory=list)
    reference_count: int = 0
    synthesis_rounds: int = 0
    token_estimate: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "source_agent": self.source_agent,
            "content": self.content, "domain": self.domain,
            "confidence": self.confidence, "tags": list(self.tags),
            "session_id": self.session_id, "source_ids": list(self.source_ids),
            "reference_count": self.reference_count,
            "synthesis_rounds": self.synthesis_rounds,
            "token_estimate": self.token_estimate,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


@dataclass
class SynthesisResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: str = SynthesisMode.AGGREGATE.value
    domain: str = ""
    fragment_ids: List[str] = field(default_factory=list)
    summary: str = ""
    key_insights: List[str] = field(default_factory=list)
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    source_agent_count: int = 0
    total_fragments_processed: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "mode": self.mode, "domain": self.domain,
            "fragment_count": len(self.fragment_ids), "summary": self.summary,
            "key_insights": list(self.key_insights),
            "confidence_distribution": dict(self.confidence_distribution),
            "source_agent_count": self.source_agent_count,
            "total_fragments_processed": self.total_fragments_processed,
            "created_at": self.created_at,
        }


@dataclass
class DomainIndex:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = KnowledgeDomain.GAME_DESIGN.value
    fragment_ids: List[str] = field(default_factory=list)
    tag_index: Dict[str, List[str]] = field(default_factory=dict)
    agent_index: Dict[str, List[str]] = field(default_factory=dict)
    keyword_index: Dict[str, List[str]] = field(default_factory=dict)
    total_fragments: int = 0
    last_built_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "domain": self.domain,
            "total_fragments": self.total_fragments,
            "unique_tags": len(self.tag_index),
            "unique_keywords": len(self.keyword_index),
            "source_agents": len(self.agent_index),
            "last_built_at": self.last_built_at,
        }


@dataclass
class CrossReference:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    relationship_type: str = "related"
    overlap_score: float = 0.0
    shared_tags: List[str] = field(default_factory=list)
    shared_keywords: List[str] = field(default_factory=list)
    connection_notes: str = ""
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "source_id": self.source_id,
            "target_id": self.target_id, "relationship_type": self.relationship_type,
            "overlap_score": round(self.overlap_score, 4),
            "shared_tags": list(self.shared_tags),
            "shared_keywords": list(self.shared_keywords),
            "connection_notes": self.connection_notes,
            "discovered_at": self.discovered_at,
        }


class KnowledgeSynthesisEngine:
    """Cross-session knowledge aggregation, connection discovery, and
    summarization engine. Ingests fragments from agent sessions,
    synthesizes insights across domains, discovers cross-references,
    builds searchable indices, and exports knowledge bases.
    """

    _instance: Optional["KnowledgeSynthesisEngine"] = None
    _TOKEN_CHARS = 4
    _MIN_KW = 3
    _REL = 0.05
    _MAX_LIMIT = 100
    _TRUNC = 500

    @classmethod
    def get_instance(cls) -> "KnowledgeSynthesisEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._fragments: Dict[str, KnowledgeFragment] = {}
        self._results: List[SynthesisResult] = []
        self._indices: Dict[str, DomainIndex] = {}
        self._cross_refs: List[CrossReference] = []
        self._ingest_count: int = 0
        self._synthesis_count: int = 0
        self._distill_count: int = 0
        self._merge_count: int = 0
        self._domain_counter: Dict[str, int] = {}
        self._agent_counter: Dict[str, int] = {}
        self._session_fragments: Dict[str, List[str]] = {}
    def ingest_fragment(
        self, source_agent: str, content: str, domain: str = "game_design",
        confidence: str = "medium", tags: Optional[List[str]] = None,
        session_id: str = "",
    ) -> KnowledgeFragment:
        if domain not in self._valid_domains():
            domain = KnowledgeDomain.GAME_DESIGN.value
        if confidence not in self._valid_confidences():
            confidence = ConfidenceLevel.MEDIUM.value
        fragment = KnowledgeFragment(
            source_agent=source_agent, content=content, domain=domain,
            confidence=confidence, tags=tags or [], session_id=session_id,
            token_estimate=self._est_tokens(content),
        )
        self._fragments[fragment.id] = fragment
        self._ingest_count += 1
        self._domain_counter[domain] = self._domain_counter.get(domain, 0) + 1
        self._agent_counter[source_agent] = self._agent_counter.get(source_agent, 0) + 1
        if session_id:
            self._session_fragments.setdefault(session_id, []).append(fragment.id)
        return fragment
    def synthesize(
        self, domain: str = "", mode: str = "aggregate", time_range_days: int = 30,
    ) -> SynthesisResult:
        if mode not in self._valid_modes():
            mode = SynthesisMode.AGGREGATE.value
        cutoff = time.time() - (time_range_days * 86400)
        candidates = [
            f for f in self._fragments.values()
            if (not domain or f.domain == domain) and f.created_at >= cutoff
        ]
        result = SynthesisResult(
            mode=mode, domain=domain or "all",
            fragment_ids=[f.id for f in candidates],
            total_fragments_processed=len(candidates),
        )
        if not candidates:
            result.summary = "No fragments available for synthesis."
            result.key_insights = ["No data within the specified range."]
            self._results.append(result)
            self._synthesis_count += 1
            return result
        conf_dist: Dict[str, int] = {}
        agent_set: Set[str] = set()
        for frag in candidates:
            conf_dist[frag.confidence] = conf_dist.get(frag.confidence, 0) + 1
            agent_set.add(frag.source_agent)
        result.confidence_distribution = conf_dist
        result.source_agent_count = len(agent_set)
        label = domain or "all domains"
        if mode == SynthesisMode.AGGREGATE.value:
            result.summary, result.key_insights = self._build_agg(candidates, label)
        elif mode == SynthesisMode.SUMMARIZE.value:
            result.summary, result.key_insights = self._build_sum(candidates)
        elif mode == SynthesisMode.CONNECT.value:
            result.summary, result.key_insights = self._build_con(candidates)
        elif mode == SynthesisMode.DISTILL.value:
            result.summary, result.key_insights = self._build_dis(candidates)
        elif mode == SynthesisMode.REFINE.value:
            result.summary, result.key_insights = self._build_ref(candidates)
        self._results.append(result)
        self._synthesis_count += 1
        for frag in candidates:
            frag.synthesis_rounds += 1
            frag.updated_at = time.time()
        return result
    def cross_reference(
        self, fragment_ids: Optional[List[str]] = None,
    ) -> List[CrossReference]:
        if fragment_ids:
            pool = [f for f in self._fragments.values() if f.id in fragment_ids]
        else:
            pool = list(self._fragments.values())
        if len(pool) < 2:
            return []
        xrefs: List[CrossReference] = []
        scored: List[Tuple[int, int, float, List[str], List[str]]] = []
        for i in range(len(pool)):
            frag_a = pool[i]
            tags_a = set(frag_a.tags)
            kw_a = self._tokenize(frag_a.content)
            for j in range(i + 1, len(pool)):
                frag_b = pool[j]
                shared_tags = sorted(tags_a & set(frag_b.tags))
                kw_b = self._tokenize(frag_b.content)
                shared_kw = sorted(kw_a & kw_b)
                ts = len(shared_tags) / max(1, max(len(tags_a), len(frag_b.tags)))
                ks = len(shared_kw) / max(1, max(len(kw_a), len(kw_b)))
                db = 0.10 if frag_a.domain == frag_b.domain else 0.0
                ab = 0.05 if frag_a.source_agent != frag_b.source_agent else 0.0
                overlap = round(min(1.0, ts * 0.50 + ks * 0.30 + db + ab), 4)
                scored.append((i, j, overlap, shared_tags, shared_kw))
        scored.sort(key=lambda x: -x[2])
        for idx_a, idx_b, score, st, sk in scored[:self._MAX_LIMIT]:
            if score < self._REL:
                continue
            rel_type = "related"
            if score > 0.60:
                rel_type = "strongly_connected"
            elif score > 0.30:
                rel_type = "connected"
            xref = CrossReference(
                source_id=pool[idx_a].id, target_id=pool[idx_b].id,
                relationship_type=rel_type, overlap_score=score,
                shared_tags=st[:10], shared_keywords=sk[:10],
                connection_notes=f"{len(st)} shared tags, {len(sk)} shared keywords",
            )
            xrefs.append(xref)
            pool[idx_a].reference_count += 1
            pool[idx_b].reference_count += 1
        self._cross_refs.extend(xrefs)
        return xrefs
    def distill_session(self, session_id: str) -> SynthesisResult:
        frag_ids = self._session_fragments.get(session_id, [])
        fragments = [self._fragments[fid] for fid in frag_ids if fid in self._fragments]
        if not fragments:
            return SynthesisResult(
                mode=SynthesisMode.DISTILL.value, domain="session",
                summary=f"No fragments found for session {session_id}.",
                key_insights=["Session has no recorded knowledge."],
            )
        conf_dist: Dict[str, int] = {}
        agent_set: Set[str] = set()
        domain_set: Set[str] = set()
        for frag in fragments:
            conf_dist[frag.confidence] = conf_dist.get(frag.confidence, 0) + 1
            agent_set.add(frag.source_agent)
            domain_set.add(frag.domain)
        summary, insights = self._build_dis(fragments)
        result = SynthesisResult(
            mode=SynthesisMode.DISTILL.value,
            domain=",".join(sorted(domain_set)) if domain_set else "session",
            fragment_ids=[f.id for f in fragments],
            summary=summary, key_insights=insights,
            confidence_distribution=conf_dist,
            source_agent_count=len(agent_set),
            total_fragments_processed=len(fragments),
        )
        self._results.append(result)
        self._distill_count += 1
        return result
    def query_knowledge(
        self, query: str, domain: str = "", limit: int = 20,
    ) -> List[KnowledgeFragment]:
        if not query.strip():
            return []
        actual_limit = max(1, min(limit, self._MAX_LIMIT))
        qt = self._tokenize(query)
        if not qt:
            return []
        domain_filter = domain if domain in self._valid_domains() else ""
        scored: List[Tuple[KnowledgeFragment, float]] = []
        for frag in self._fragments.values():
            if domain_filter and frag.domain != domain_filter:
                continue
            score = self._score_rel(frag, query, qt)
            if score >= self._REL:
                scored.append((frag, score))
        scored.sort(key=lambda x: -x[1])
        return [frag for frag, _ in scored[:actual_limit]]
    def build_domain_index(self, domain: str) -> DomainIndex:
        if domain not in self._valid_domains():
            domain = KnowledgeDomain.GAME_DESIGN.value
        index = DomainIndex(domain=domain)
        fragments = [f for f in self._fragments.values() if f.domain == domain]
        index.total_fragments = len(fragments)
        for frag in fragments:
            index.fragment_ids.append(frag.id)
            index.agent_index.setdefault(frag.source_agent, []).append(frag.id)
            for tag in frag.tags:
                index.tag_index.setdefault(tag, []).append(frag.id)
            for kw in self._tokenize(frag.content):
                index.keyword_index.setdefault(kw, []).append(frag.id)
        index.last_built_at = time.time()
        self._indices[domain] = index
        return index
    def merge_fragments(
        self, source_ids: List[str], label: str = "",
    ) -> KnowledgeFragment:
        sources = [self._fragments.get(sid) for sid in source_ids]
        sources = [s for s in sources if s is not None]
        if not sources:
            return KnowledgeFragment(
                source_agent="merge",
                content=f"Merge failed: no valid source fragments. Label: {label}",
                domain=KnowledgeDomain.GAME_DESIGN.value,
                confidence=ConfidenceLevel.LOW.value,
            )
        domain_counts: Dict[str, int] = {}
        crm = {"certain": 4, "high": 3, "medium": 2, "low": 1}
        best_conf = sources[0].confidence
        best_cr = crm.get(best_conf, 0)
        all_tags: Set[str] = set()
        agent_set: Set[str] = set()
        mp: List[str] = []
        if label:
            mp.append(f"## Merge: {label}\n")
        for src in sources:
            domain_counts[src.domain] = domain_counts.get(src.domain, 0) + 1
            cr = crm.get(src.confidence, 0)
            if cr > best_cr:
                best_cr = cr
                best_conf = src.confidence
            all_tags.update(src.tags)
            agent_set.add(src.source_agent)
            mp.append(f"[{src.source_agent}] {src.content}")
        best_domain = max(domain_counts, key=lambda k: domain_counts[k])
        merged = KnowledgeFragment(
            source_agent=",".join(sorted(agent_set)),
            content="\n\n---\n\n".join(mp), domain=best_domain,
            confidence=best_conf, tags=sorted(all_tags),
            source_ids=source_ids,
            token_estimate=self._est_tokens("".join(mp)),
        )
        self._fragments[merged.id] = merged
        self._domain_counter[merged.domain] = self._domain_counter.get(merged.domain, 0) + 1
        self._merge_count += 1
        for src in sources:
            src.reference_count += 1
        return merged
    def export_knowledge_base(self, format: str = "json") -> Dict[str, Any]:
        if format == "compact":
            return {
                "format": "compact", "total_fragments": len(self._fragments),
                "total_synthesis_results": len(self._results),
                "total_cross_references": len(self._cross_refs),
                "domains": dict(self._domain_counter),
                "agent_contributions": dict(self._agent_counter),
                "fragments": [
                    {"id": f.id, "domain": f.domain, "source_agent": f.source_agent,
                     "confidence": f.confidence, "tags": f.tags,
                     "content_preview": f.content[:200]}
                    for f in self._fragments.values()
                ], "exported_at": time.time(),
            }
        if format == "domain_summary":
            summaries: Dict[str, Dict[str, Any]] = {}
            for dom in self._valid_domains():
                df = [f for f in self._fragments.values() if f.domain == dom]
                summaries[dom] = {
                    "fragment_count": len(df),
                    "total_tags": len(set(t for f in df for t in f.tags)),
                    "unique_agents": len(set(f.source_agent for f in df)),
                }
            return {"format": "domain_summary", "domain_summaries": summaries,
                    "exported_at": time.time()}
        if format == "timeline":
            sf = sorted(self._fragments.values(), key=lambda f: f.created_at)
            return {
                "format": "timeline", "total_fragments": len(sf),
                "fragments": [
                    {"id": f.id, "domain": f.domain, "source_agent": f.source_agent,
                     "content": f.content, "created_at": f.created_at}
                    for f in sf
                ], "exported_at": time.time(),
            }
        return {
            "format": "json", "total_fragments": len(self._fragments),
            "total_synthesis_results": len(self._results),
            "total_cross_references": len(self._cross_refs),
            "ingest_count": self._ingest_count,
            "synthesis_count": self._synthesis_count,
            "distill_count": self._distill_count,
            "merge_count": self._merge_count,
            "domains": dict(self._domain_counter),
            "agent_contributions": dict(self._agent_counter),
            "fragments": [f.to_dict() for f in self._fragments.values()],
            "synthesis_results": [r.to_dict() for r in self._results],
            "indices": [idx.to_dict() for idx in self._indices.values()],
            "exported_at": time.time(),
        }
    def get_stats(self) -> Dict[str, Any]:
        dd: Dict[str, int] = {}
        cd: Dict[str, int] = {}
        tcl, ttg = 0, 0
        for frag in self._fragments.values():
            dd[frag.domain] = dd.get(frag.domain, 0) + 1
            cd[frag.confidence] = cd.get(frag.confidence, 0) + 1
            tcl += len(frag.content)
            ttg += len(frag.tags)
        mu: Dict[str, int] = {}
        for result in self._results:
            mu[result.mode] = mu.get(result.mode, 0) + 1
        tf = len(self._fragments)
        return {
            "total_fragments": tf,
            "total_synthesis_results": len(self._results),
            "total_cross_references": len(self._cross_refs),
            "ingest_count": self._ingest_count,
            "synthesis_count": self._synthesis_count,
            "distill_count": self._distill_count,
            "merge_count": self._merge_count,
            "avg_content_length": round(tcl / max(1, tf), 1),
            "avg_tags_per_fragment": round(ttg / max(1, tf), 1),
            "domain_distribution": dd, "confidence_distribution": cd,
            "agent_contributions": dict(self._agent_counter),
            "synthesis_mode_usage": mu,
            "indexed_domains": list(self._indices.keys()),
            "sessions_tracked": len(self._session_fragments),
            "total_session_fragments": sum(len(ids) for ids in self._session_fragments.values()),
            "available_domains": self._valid_domains(),
            "available_modes": self._valid_modes(),
            "available_confidences": self._valid_confidences(),
        }
    def reset(self) -> None:
        self._fragments.clear()
        self._results.clear()
        self._indices.clear()
        self._cross_refs.clear()
        self._session_fragments.clear()
        self._ingest_count = 0
        self._synthesis_count = 0
        self._distill_count = 0
        self._merge_count = 0
        self._domain_counter.clear()
        self._agent_counter.clear()
    def _build_agg(self, fragments: List[KnowledgeFragment],
                   scope_label: str) -> Tuple[str, List[str]]:
        dg: Dict[str, List[KnowledgeFragment]] = {}
        for f in fragments:
            dg.setdefault(f.domain, []).append(f)
        parts = [f"Aggregated synthesis across {len(fragments)} fragments from {scope_label}."]
        insights: List[str] = []
        for d, group in sorted(dg.items()):
            agents = sorted(set(f.source_agent for f in group))
            hc = sum(1 for f in group if f.confidence in ("high", "certain"))
            parts.append(f"- {d}: {len(group)} fragments from {len(agents)} agent(s).")
            insights.append(f"{d}: {len(group)} observations, {hc} high/certain confidence.")
        return "\n".join(parts), insights
    def _build_sum(self, fragments: List[KnowledgeFragment]) -> Tuple[str, List[str]]:
        sf = sorted(fragments, key=lambda f: self._conf_rank(f.confidence), reverse=True)
        parts = [f"Summarized {len(fragments)} knowledge fragments."]
        for frag in sf[:min(10, len(sf))]:
            parts.append(f"[{frag.confidence.upper()}] {frag.content[:self._TRUNC].replace(chr(10), ' ')}")
        tags_all: Dict[str, int] = {}
        for f in fragments:
            for t in f.tags:
                tags_all[t] = tags_all.get(t, 0) + 1
        tt = sorted(tags_all.items(), key=lambda x: -x[1])[:10]
        return "\n\n".join(parts), [f"Top tag: {t} ({c} occurrences)" for t, c in tt]
    def _build_con(self, fragments: List[KnowledgeFragment]) -> Tuple[str, List[str]]:
        connections: Dict[str, Set[str]] = {}
        for i in range(len(fragments)):
            for j in range(i + 1, min(i + 11, len(fragments))):
                fi, fj = fragments[i], fragments[j]
                if fi.domain == fj.domain:
                    connections.setdefault(fi.domain, set()).add(fj.source_agent)
        parts = [f"Connection analysis of {len(fragments)} fragments."]
        insights: List[str] = []
        for dom, agents in sorted(connections.items()):
            parts.append(f"- {dom}: agents involved = {sorted(agents)}")
            insights.append(f"{dom} connects {len(agents)} agents across fragments.")
        return "\n".join(parts), insights
    def _build_dis(self, fragments: List[KnowledgeFragment]) -> Tuple[str, List[str]]:
        hc = [f for f in fragments if self._conf_rank(f.confidence) >= 3]
        if not hc:
            hc = fragments[:min(5, len(fragments))]
        parts = [f"Distilled {len(fragments)} fragments into {len(hc)} core principles."]
        for frag in hc[:8]:
            parts.append(f"* [{frag.confidence}] {frag.content[:300].replace(chr(10), ' ')}")
        agents = sorted(set(f.source_agent for f in hc))
        domains = sorted(set(f.domain for f in hc))
        insights = [
            f"Core agents: {', '.join(agents)}",
            f"Domains covered: {', '.join(domains)}",
            f"High-confidence distillation of {len(hc)} key fragments.",
        ]
        return "\n\n".join(parts), insights
    def _build_ref(self, fragments: List[KnowledgeFragment]) -> Tuple[str, List[str]]:
        bc = sorted(fragments, key=lambda f: self._conf_rank(f.confidence))
        lm = [f for f in bc if self._conf_rank(f.confidence) <= 2]
        hi = [f for f in bc if self._conf_rank(f.confidence) >= 3]
        parts = [
            f"Refinement scan: {len(fragments)} total, {len(lm)} for potential refinement, "
            f"{len(hi)} validated at high confidence."
        ]
        if lm:
            parts.append("\nCandidates for refinement:")
            for frag in lm[:5]:
                parts.append(f"- [{frag.confidence}] {frag.content[:200].replace(chr(10), ' ')}")
        insights = [
            f"{len(lm)} low/medium confidence fragments may need validation.",
            f"{len(hi)} high/certain fragments serve as anchors.",
        ]
        return "\n".join(parts), insights
    def _score_rel(self, fragment: KnowledgeFragment, query: str, qt: Set[str]) -> float:
        fts = self._tokenize(fragment.content)
        if not qt or not fts:
            return 0.0
        eb = 1.0 if query.lower() in fragment.content.lower() else 0.0
        ov = len(qt & fts) / max(len(qt), len(fts))
        th = sum(1 for t in fragment.tags if any(q in t.lower() for q in qt if len(q) >= 3))
        tb = min(0.20, th * 0.05)
        cb = self._conf_rank(fragment.confidence) * 0.03
        ts = ov * 0.55 + eb * 0.15 + tb + cb
        rc = 1.0 / (1.0 + (time.time() - fragment.created_at) / 86400.0)
        return round(min(1.0, ts * 0.70 + rc * 0.30), 4)

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        cl = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text)
        return {t for t in cl.split() if len(t) >= KnowledgeSynthesisEngine._MIN_KW}

    @staticmethod
    def _est_tokens(text: str) -> int:
        return max(1, len(text) // KnowledgeSynthesisEngine._TOKEN_CHARS)

    @staticmethod
    def _conf_rank(confidence: str) -> int:
        return {"low": 1, "medium": 2, "high": 3, "certain": 4}.get(confidence, 2)

    @staticmethod
    def _valid_domains() -> List[str]:
        return [d.value for d in KnowledgeDomain]

    @staticmethod
    def _valid_modes() -> List[str]:
        return [m.value for m in SynthesisMode]

    @staticmethod
    def _valid_confidences() -> List[str]:
        return [c.value for c in ConfidenceLevel]


# Module-level singleton

_knowledge_synthesis: Optional[KnowledgeSynthesisEngine] = None


def get_knowledge_synthesis() -> KnowledgeSynthesisEngine:
    global _knowledge_synthesis
    if _knowledge_synthesis is None:
        _knowledge_synthesis = KnowledgeSynthesisEngine.get_instance()
    return _knowledge_synthesis