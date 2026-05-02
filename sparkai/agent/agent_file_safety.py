"""
SparkLabs Agent - File Safety Controller

Path-based access control for agent file operations within the game
engine project workspace. Prevents agents from accessing sensitive
system paths, credential files, and internal engine configuration.

Architecture:
  FileSafetyController
    |-- DeniedPaths (exact-match blocked absolute paths)
    |-- DeniedPrefixes (directory-prefix blocked paths)
    |-- AllowedRoots (write-safety root boundaries)
    |-- PathNormalizer (resolves symlinks and relative paths)

Safety Rules:
  - Write operations restricted to project workspace
  - Read operations blocked on internal cache/config directories
  - Symlink traversal checked for escape attempts
  - Environment variable access through designated APIs only

Usage:
    fsc = FileSafetyController(workspace_root="/path/to/project")
    if fsc.is_write_allowed("/path/to/project/assets/sprite.png"):
        write_file(path, content)
    if not fsc.is_write_allowed("/etc/passwd"):
        raise SecurityError("Access denied")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Set


class FileSafetyController:
    """
    File access safety controller for agent operations.

    Maintains deny-lists for sensitive paths and enforces
    workspace boundaries for write operations. All path checking
    uses resolved absolute paths to prevent traversal attacks.

    Usage:
        fsc = FileSafetyController("/Users/project/game")
        assert fsc.is_write_allowed("/Users/project/game/assets/img.png")
        assert not fsc.is_write_allowed("/etc/passwd")
    """

    def __init__(self, workspace_root: str):
        self._workspace = os.path.realpath(os.path.expanduser(workspace_root))
        self._home = os.path.realpath(os.path.expanduser("~"))
        self._denied_paths: Set[str] = self._build_denied_paths()
        self._denied_prefixes: List[str] = self._build_denied_prefixes()
        self._blocked_read_dirs: List[str] = self._build_blocked_read_dirs()
        self._violation_count: int = 0
        self._total_checks: int = 0

    def _build_denied_paths(self) -> Set[str]:
        return {
            os.path.realpath(p)
            for p in [
                os.path.join(self._home, ".ssh", "authorized_keys"),
                os.path.join(self._home, ".ssh", "id_rsa"),
                os.path.join(self._home, ".ssh", "id_ed25519"),
                os.path.join(self._home, ".ssh", "config"),
                os.path.join(self._home, ".bashrc"),
                os.path.join(self._home, ".zshrc"),
                os.path.join(self._home, ".profile"),
                os.path.join(self._home, ".netrc"),
                os.path.join(self._home, ".pgpass"),
                os.path.join(self._home, ".npmrc"),
                os.path.join(self._home, ".pypirc"),
                "/etc/sudoers",
                "/etc/passwd",
                "/etc/shadow",
            ]
        }

    def _build_denied_prefixes(self) -> List[str]:
        return [
            os.path.realpath(p) + os.sep
            for p in [
                os.path.join(self._home, ".ssh"),
                os.path.join(self._home, ".aws"),
                os.path.join(self._home, ".gnupg"),
                os.path.join(self._home, ".kube"),
                os.path.join(self._home, ".docker"),
                os.path.join(self._home, ".azure"),
                os.path.join(self._home, ".config", "gh"),
                "/etc/sudoers.d",
                "/etc/systemd",
            ]
        ]

    def _build_blocked_read_dirs(self) -> List[str]:
        return [
            os.path.join(self._workspace, ".sparkai"),
            os.path.join(self._workspace, ".sparklabs_cache"),
        ]

    def _resolve(self, path: str) -> str:
        try:
            p = Path(path).expanduser()
            if p.exists():
                return str(p.resolve())
            parent = p.parent
            if parent.exists():
                return str((parent / p.name).resolve())
            return str(p.resolve())
        except Exception:
            return os.path.realpath(os.path.expanduser(str(path)))

    def is_write_allowed(self, path: str) -> bool:
        self._total_checks += 1
        resolved = self._resolve(path)

        if resolved in self._denied_paths:
            self._violation_count += 1
            return False

        for prefix in self._denied_prefixes:
            if resolved.startswith(prefix):
                self._violation_count += 1
                return False

        workspace_with_sep = self._workspace + os.sep
        if not (resolved == self._workspace or resolved.startswith(workspace_with_sep)):
            self._violation_count += 1
            return False

        return True

    def is_read_allowed(self, path: str) -> bool:
        self._total_checks += 1
        resolved = self._resolve(path)
        for blocked in self._blocked_read_dirs:
            blocked_with_sep = blocked + os.sep
            if resolved == blocked or resolved.startswith(blocked_with_sep):
                self._violation_count += 1
                return False
        return True

    def get_safe_paths(self, path: str) -> Optional[str]:
        resolved = self._resolve(path)
        workspace_sep = self._workspace + os.sep
        if resolved.startswith(workspace_sep):
            return resolved
        if resolved == self._workspace:
            return resolved
        return None

    def validate_paths(self, paths: List[str]) -> List[str]:
        violations = []
        for p in paths:
            if not self.is_write_allowed(p):
                violations.append(p)
        return violations

    def set_workspace(self, new_root: str) -> None:
        self._workspace = os.path.realpath(os.path.expanduser(new_root))
        self._blocked_read_dirs = self._build_blocked_read_dirs()

    def get_stats(self) -> dict:
        return {
            "workspace": self._workspace,
            "total_checks": self._total_checks,
            "violations": self._violation_count,
            "violation_rate": round(
                self._violation_count / max(self._total_checks, 1) * 100, 1,
            ),
            "denied_paths_count": len(self._denied_paths),
            "denied_prefixes_count": len(self._denied_prefixes),
        }

    def clear(self) -> None:
        self._violation_count = 0
        self._total_checks = 0


_global_file_safety: Optional[FileSafetyController] = None


def get_file_safety() -> FileSafetyController:
    global _global_file_safety
    if _global_file_safety is None:
        _global_file_safety = FileSafetyController(os.getcwd())
    return _global_file_safety
