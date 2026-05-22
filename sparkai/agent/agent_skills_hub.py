"""
Skills Hub - Open skills registry and marketplace for discovering, sharing,
and installing agent skills within SparkLabs AI game development studio.

Architecture:
    SkillsHub/
    |-- SkillCategory (CODE_GEN, GAME_DESIGN, ART, AUDIO, PHYSICS,
    |                  NETWORKING, NARRATIVE, UTILITY enumeration)
    |-- SkillStatus (PUBLISHED, DRAFT, DEPRECATED, INSTALLED enumeration)
    |-- LicenseType (MIT, APACHE, PROPRIETARY, CC_BY enumeration)
    |-- SkillPackage (published skill artifact dataclass)
    |-- SkillVersion (versioned release record dataclass)
    |-- SkillReview (community rating and feedback dataclass)
    |-- DependencyRequirement (skill dependency descriptor dataclass)
    |-- InstallRecord (local installation tracking dataclass)
    |-- SkillsHub (global registry and marketplace orchestration)

Provides a community-driven skill ecosystem where developers publish,
discover, rate, and install agent skills. Each skill is versioned with
dependency resolution, license tracking, and install provenance.
"""

from __future__ import annotations

import uuid
import time
import json
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class SkillCategory(Enum):
    CODE_GEN = auto()
    GAME_DESIGN = auto()
    ART = auto()
    AUDIO = auto()
    PHYSICS = auto()
    NETWORKING = auto()
    NARRATIVE = auto()
    UTILITY = auto()


class SkillStatus(Enum):
    PUBLISHED = auto()
    DRAFT = auto()
    DEPRECATED = auto()
    INSTALLED = auto()


class LicenseType(Enum):
    MIT = auto()
    APACHE = auto()
    PROPRIETARY = auto()
    CC_BY = auto()


@dataclass
class DependencyRequirement:
    dependency_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    skill_name: str = ""
    min_version: str = "1.0.0"
    max_version: str = ""
    optional: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "skill_name": self.skill_name,
            "min_version": self.min_version,
            "max_version": self.max_version,
            "optional": self.optional,
        }


@dataclass
class SkillVersion:
    version_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    version: str = "1.0.0"
    release_date: float = 0.0
    changelog: str = ""
    source_url: str = ""
    package_size_bytes: int = 0
    min_agent_version: str = "1.0.0"
    dependencies: List[DependencyRequirement] = field(default_factory=list)
    is_prerelease: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "version": self.version,
            "release_date": self.release_date,
            "changelog": self.changelog[:200],
            "source_url": self.source_url,
            "size_bytes": self.package_size_bytes,
            "min_agent": self.min_agent_version,
            "dependencies": len(self.dependencies),
            "prerelease": self.is_prerelease,
        }


@dataclass
class SkillPackage:
    package_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.UTILITY
    status: SkillStatus = SkillStatus.DRAFT
    license: LicenseType = LicenseType.MIT
    author: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    tags: List[str] = field(default_factory=list)
    versions: List[SkillVersion] = field(default_factory=list)
    total_installs: int = 0
    total_ratings: int = 0
    average_rating: float = 0.0
    source_repository: str = ""
    homepage: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_latest_version(self) -> Optional[SkillVersion]:
        stable = [v for v in self.versions if not v.is_prerelease]
        if stable:
            return stable[-1]
        return self.versions[-1] if self.versions else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "name": self.name,
            "description": self.description[:200],
            "category": self.category.name,
            "status": self.status.name,
            "license": self.license.name,
            "author": self.author,
            "version_count": len(self.versions),
            "latest_version": self.get_latest_version().version if self.get_latest_version() else None,
            "installs": self.total_installs,
            "rating": round(self.average_rating, 1),
            "review_count": self.total_ratings,
            "tags": self.tags,
        }


@dataclass
class SkillReview:
    review_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    package_id: str = ""
    author: str = ""
    rating: float = 0.0
    title: str = ""
    body: str = ""
    created_at: float = 0.0
    version_used: str = ""
    helpful_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "author": self.author,
            "rating": self.rating,
            "title": self.title,
            "body_preview": self.body[:150],
            "version": self.version_used,
            "helpful": self.helpful_count,
        }


@dataclass
class InstallRecord:
    install_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    package_id: str = ""
    version: str = ""
    installed_at: float = 0.0
    installed_by: str = ""
    source_url: str = ""
    is_active: bool = True
    check_updates_enabled: bool = True
    custom_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "install_id": self.install_id,
            "package_id": self.package_id,
            "version": self.version,
            "installed_at": self.installed_at,
            "active": self.is_active,
            "updates_enabled": self.check_updates_enabled,
        }


class SkillsHub:
    _instance: Optional["SkillsHub"] = None
    _lock = threading.RLock()
    _MAX_REVIEWS_PER_PACKAGE = 500

    def __init__(self):
        self._packages: Dict[str, SkillPackage] = {}
        self._reviews: Dict[str, List[SkillReview]] = {}
        self._installs: Dict[str, InstallRecord] = {}
        self._name_index: Dict[str, str] = {}
        self._category_index: Dict[SkillCategory, List[str]] = {c: [] for c in SkillCategory}
        self._tag_index: Dict[str, Set[str]] = {}
        self._total_published: int = 0
        self._total_installed: int = 0

    @classmethod
    def get_instance(cls) -> "SkillsHub":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish_skill(
        self,
        name: str,
        description: str,
        category: SkillCategory,
        source_url: str,
        license: LicenseType = LicenseType.MIT,
        author: str = "",
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[DependencyRequirement]] = None,
        homepage: str = "",
    ) -> SkillPackage:
        with self._lock:
            skill_version = SkillVersion(
                version=version,
                release_date=time.time(),
                source_url=source_url,
                dependencies=dependencies or [],
            )

            package = SkillPackage(
                name=name,
                description=description,
                category=category,
                status=SkillStatus.PUBLISHED,
                license=license,
                author=author,
                created_at=time.time(),
                updated_at=time.time(),
                tags=tags or [],
                versions=[skill_version],
                source_repository=source_url,
                homepage=homepage,
            )

            self._packages[package.package_id] = package
            self._name_index[name.lower()] = package.package_id
            self._category_index[category].append(package.package_id)

            for tag in (tags or []):
                tag_lower = tag.lower()
                if tag_lower not in self._tag_index:
                    self._tag_index[tag_lower] = set()
                self._tag_index[tag_lower].add(package.package_id)

            self._reviews[package.package_id] = []
            self._total_published += 1
            return package

    def install_skill(
        self,
        skill_id: str,
        version: Optional[str] = None,
        installed_by: str = "",
    ) -> Optional[InstallRecord]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        target_version = version
        if target_version is None:
            latest = package.get_latest_version()
            if latest is None:
                return None
            target_version = latest.version

        version_obj = None
        for v in package.versions:
            if v.version == target_version:
                version_obj = v
                break

        if version_obj is None:
            return None

        unresolved = self._check_dependency_conflicts(version_obj.dependencies)
        if unresolved:
            return None

        with self._lock:
            record = InstallRecord(
                package_id=skill_id,
                version=target_version,
                installed_at=time.time(),
                installed_by=installed_by,
                source_url=version_obj.source_url,
            )
            self._installs[record.install_id] = record
            package.status = SkillStatus.INSTALLED
            package.total_installs += 1
            self._total_installed += 1
            return record

    def uninstall_skill(self, skill_id: str) -> bool:
        with self._lock:
            package = self._packages.get(skill_id)
            if package is None:
                return False

            to_remove = [
                iid for iid, rec in self._installs.items()
                if rec.package_id == skill_id and rec.is_active
            ]
            for iid in to_remove:
                self._installs[iid].is_active = False

            dependents = self._find_dependents(skill_id)
            if dependents:
                return False

            package.status = SkillStatus.PUBLISHED
            return True

    def update_skill(
        self,
        skill_id: str,
        to_version: str,
    ) -> Optional[InstallRecord]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        version_obj = None
        for v in package.versions:
            if v.version == to_version:
                version_obj = v
                break

        if version_obj is None:
            return None

        self.uninstall_skill(skill_id)
        return self.install_skill(skill_id, version=to_version)

    def search_skills(
        self,
        query: str = "",
        category: Optional[SkillCategory] = None,
        sort_by: str = "rating",
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[SkillPackage]:
        query_lower = query.lower()
        candidates: set = set(self._packages.keys())

        if category:
            candidates &= set(self._category_index.get(category, []))

        if tags:
            for tag in tags:
                candidates &= self._tag_index.get(tag.lower(), set())

        results: List[Tuple[float, SkillPackage]] = []
        for pid in candidates:
            package = self._packages[pid]
            if package.status == SkillStatus.DEPRECATED:
                continue

            relevance = 1.0
            if query_lower:
                relevance = self._compute_search_relevance(package, query_lower)
                if relevance <= 0:
                    continue

            sort_value = {
                "rating": package.average_rating,
                "installs": float(package.total_installs),
                "name": 0.0,
                "recent": package.updated_at,
            }.get(sort_by, package.average_rating)

            results.append((sort_value * relevance, package))

        if sort_by == "name":
            results.sort(key=lambda x: x[1].name.lower())
        elif sort_by == "recent":
            results.sort(key=lambda x: x[0], reverse=True)
        else:
            results.sort(key=lambda x: x[0], reverse=True)

        return [pkg for _, pkg in results[:limit]]

    def rate_skill(
        self,
        skill_id: str,
        rating: float,
        review: str = "",
        author: str = "",
        title: str = "",
    ) -> Optional[SkillReview]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        clamped_rating = max(0.0, min(5.0, rating))

        with self._lock:
            skill_review = SkillReview(
                package_id=skill_id,
                author=author,
                rating=clamped_rating,
                title=title,
                body=review,
                created_at=time.time(),
                version_used=package.get_latest_version().version if package.get_latest_version() else "",
            )
            if skill_id not in self._reviews:
                self._reviews[skill_id] = []
            self._reviews[skill_id].append(skill_review)

            if len(self._reviews[skill_id]) > self._MAX_REVIEWS_PER_PACKAGE:
                self._reviews[skill_id] = self._reviews[skill_id][-self._MAX_REVIEWS_PER_PACKAGE:]

            total = sum(r.rating for r in self._reviews[skill_id])
            package.total_ratings = len(self._reviews[skill_id])
            package.average_rating = total / package.total_ratings if package.total_ratings > 0 else 0.0

            return skill_review

    def resolve_dependencies(self, skill_id: str) -> Optional[Dict[str, Any]]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        latest = package.get_latest_version()
        if latest is None:
            return None

        resolved: List[Dict[str, Any]] = []
        missing: List[Dict[str, Any]] = []
        visited: Set[str] = set()

        self._resolve_recursive(latest.dependencies, resolved, missing, visited)

        return {
            "skill_id": skill_id,
            "name": package.name,
            "version": latest.version,
            "total_dependencies": len(resolved) + len(missing),
            "resolved": resolved,
            "missing": missing,
            "fully_resolved": len(missing) == 0,
        }

    def get_installed_skills(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for rec in self._installs.values():
            if not rec.is_active:
                continue
            package = self._packages.get(rec.package_id)
            if package is None:
                continue
            result.append({
                "install_id": rec.install_id,
                "package_id": rec.package_id,
                "name": package.name,
                "version": rec.version,
                "category": package.category.name,
                "installed_at": rec.installed_at,
                "author": package.author,
            })
        result.sort(key=lambda x: x["installed_at"], reverse=True)
        return result

    def check_updates(self) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        for rec in self._installs.values():
            if not rec.is_active or not rec.check_updates_enabled:
                continue
            package = self._packages.get(rec.package_id)
            if package is None:
                continue
            latest = package.get_latest_version()
            if latest and latest.version != rec.version:
                updates.append({
                    "package_id": rec.package_id,
                    "name": package.name,
                    "installed_version": rec.version,
                    "latest_version": latest.version,
                    "changelog": latest.changelog[:200],
                })
        return updates

    def export_skill(self, skill_id: str) -> Optional[str]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        reviews = self._reviews.get(skill_id, [])
        export_data = {
            "package": {
                "name": package.name,
                "description": package.description,
                "category": package.category.name,
                "license": package.license.name,
                "author": package.author,
                "tags": package.tags,
                "homepage": package.homepage,
                "source_repository": package.source_repository,
            },
            "versions": [v.to_dict() for v in package.versions],
            "reviews_count": len(reviews),
            "average_rating": round(package.average_rating, 1),
            "exported_at": time.time(),
        }
        return json.dumps(export_data, default=str, indent=2)

    def import_skill(self, package_data: Dict[str, Any]) -> Optional[SkillPackage]:
        pkg = package_data.get("package", {})
        if not pkg or not pkg.get("name"):
            return None

        name_lower = pkg["name"].lower()
        if name_lower in self._name_index:
            return self._packages[self._name_index[name_lower]]

        category_map = {c.name: c for c in SkillCategory}
        license_map = {l.name: l for l in LicenseType}

        category = category_map.get(pkg.get("category", "UTILITY"), SkillCategory.UTILITY)
        license_type = license_map.get(pkg.get("license", "MIT"), LicenseType.MIT)

        versions_data = package_data.get("versions", [])
        versions: List[SkillVersion] = []
        for vd in versions_data:
            deps = []
            for dep in vd.get("dependencies", []):
                if isinstance(dep, dict):
                    deps.append(DependencyRequirement(
                        skill_name=dep.get("skill_name", ""),
                        min_version=dep.get("min_version", "1.0.0"),
                        max_version=dep.get("max_version", ""),
                        optional=dep.get("optional", False),
                    ))
            versions.append(SkillVersion(
                version=vd.get("version", "1.0.0"),
                release_date=vd.get("release_date", time.time()),
                changelog=vd.get("changelog", ""),
                source_url=vd.get("source_url", ""),
                dependencies=deps,
            ))

        return self.publish_skill(
            name=pkg["name"],
            description=pkg.get("description", ""),
            category=category,
            source_url=pkg.get("source_repository", ""),
            license=license_type,
            author=pkg.get("author", ""),
            version=versions[0].version if versions else "1.0.0",
            tags=pkg.get("tags", []),
            dependencies=versions[0].dependencies if versions else [],
            homepage=pkg.get("homepage", ""),
        )

    def get_package(self, package_id: str) -> Optional[SkillPackage]:
        return self._packages.get(package_id)

    def get_package_by_name(self, name: str) -> Optional[SkillPackage]:
        pid = self._name_index.get(name.lower())
        if pid:
            return self._packages.get(pid)
        return None

    def get_reviews(
        self,
        skill_id: str,
        limit: int = 50,
    ) -> List[SkillReview]:
        reviews = self._reviews.get(skill_id, [])
        return sorted(reviews, key=lambda r: r.created_at, reverse=True)[:limit]

    def list_categories(self) -> List[Dict[str, Any]]:
        return [{
            "category": c.name,
            "package_count": len(self._category_index.get(c, [])),
        } for c in SkillCategory]

    def list_tags(self) -> Dict[str, int]:
        return {tag: len(pkg_ids) for tag, pkg_ids in self._tag_index.items()}

    def deprecate_skill(self, skill_id: str) -> bool:
        with self._lock:
            package = self._packages.get(skill_id)
            if package is None:
                return False
            package.status = SkillStatus.DEPRECATED
            return True

    def add_version(
        self,
        skill_id: str,
        version: str,
        source_url: str,
        changelog: str = "",
        dependencies: Optional[List[DependencyRequirement]] = None,
        is_prerelease: bool = False,
    ) -> Optional[SkillVersion]:
        package = self._packages.get(skill_id)
        if package is None:
            return None

        with self._lock:
            skill_version = SkillVersion(
                version=version,
                release_date=time.time(),
                changelog=changelog,
                source_url=source_url,
                dependencies=dependencies or [],
                is_prerelease=is_prerelease,
            )
            package.versions.append(skill_version)
            package.updated_at = time.time()
            return skill_version

    def _resolve_recursive(
        self,
        deps: List[DependencyRequirement],
        resolved: List[Dict[str, Any]],
        missing: List[Dict[str, Any]],
        visited: Set[str],
    ) -> None:
        for dep in deps:
            dep_package = self.get_package_by_name(dep.skill_name)
            if dep_package is None:
                if not dep.optional:
                    missing.append({
                        "name": dep.skill_name,
                        "min_version": dep.min_version,
                        "optional": dep.optional,
                    })
                continue

            latest = dep_package.get_latest_version()
            if latest is None:
                continue

            if dep_package.package_id in visited:
                continue
            visited.add(dep_package.package_id)

            resolved.append({
                "package_id": dep_package.package_id,
                "name": dep_package.name,
                "version": latest.version,
                "category": dep_package.category.name,
                "optional": dep.optional,
            })

            self._resolve_recursive(
                latest.dependencies, resolved, missing, visited,
            )

    def _check_dependency_conflicts(
        self,
        deps: List[DependencyRequirement],
    ) -> List[str]:
        conflicts: List[str] = []
        for dep in deps:
            if dep.optional:
                continue
            dep_package = self.get_package_by_name(dep.skill_name)
            if dep_package is None:
                conflicts.append(dep.skill_name)
        return conflicts

    def _find_dependents(self, skill_id: str) -> List[str]:
        package = self._packages.get(skill_id)
        if package is None:
            return []

        dependents: List[str] = []
        for pid, pkg in self._packages.items():
            if pid == skill_id:
                continue
            latest = pkg.get_latest_version()
            if latest is None:
                continue
            for dep in latest.dependencies:
                if dep.skill_name.lower() == package.name.lower():
                    dependents.append(pid)
        return dependents

    def _compute_search_relevance(
        self,
        package: SkillPackage,
        query: str,
    ) -> float:
        searchable = (
            f"{package.name} {package.description} "
            f"{package.author} {' '.join(package.tags)}"
        ).lower()

        if query in searchable:
            direct_match = searchable.count(query)
            return min(1.0, 0.3 + 0.15 * direct_match)

        query_words = set(query.split())
        text_words = set(searchable.split())
        overlap = query_words & text_words

        if not overlap:
            return 0.0

        return 0.1 + 0.3 * (len(overlap) / len(query_words))

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_category: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            by_license: Dict[str, int] = {}
            total_versions = 0

            for pkg in self._packages.values():
                by_category[pkg.category.name] = by_category.get(pkg.category.name, 0) + 1
                by_status[pkg.status.name] = by_status.get(pkg.status.name, 0) + 1
                by_license[pkg.license.name] = by_license.get(pkg.license.name, 0) + 1
                total_versions += len(pkg.versions)

            active_installs = sum(
                1 for rec in self._installs.values() if rec.is_active
            )

            return {
                "total_packages": len(self._packages),
                "total_versions": total_versions,
                "total_published": self._total_published,
                "total_installs": active_installs,
                "total_reviews": sum(len(r) for r in self._reviews.values()),
                "unique_tags": len(self._tag_index),
                "by_category": by_category,
                "by_status": by_status,
                "by_license": by_license,
                "packages": [
                    p.to_dict() for p in list(self._packages.values())[:20]
                ],
            }


def get_skills_hub() -> SkillsHub:
    return SkillsHub.get_instance()