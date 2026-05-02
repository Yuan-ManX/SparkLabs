"""
Shell Hooks - Sandboxed shell command execution with hook system.

Architecture:
    ShellHooks/
    |-- ShellPermission (access control levels)
    |-- ShellCommand (command specification)
    |-- ShellResult (execution result container)
    |-- CommandHook (pre/post execution hook definition)
    |-- ShellHookManager (unified command execution orchestration)
    |-- BUILTIN_ALLOWLIST (safe command defaults)
    |-- BUILTIN_DENYLIST (dangerous command defaults)

Provides controlled shell command execution for agents with
pre/post hooks, allowlist/denylist enforcement, and resource limits.
"""

from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ShellPermission(Enum):
    DENY = auto()
    ALLOW = auto()
    ASK = auto()


@dataclass
class ShellCommand:
    command: str
    args: List[str] = field(default_factory=list)
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    max_output_bytes: int = 1024 * 1024
    shell: bool = False
    stdin_data: Optional[str] = None


@dataclass
class ShellResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    truncated: bool = False
    killed_by_timeout: bool = False
    command_id: str = ""

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": self.stdout[:2000],
            "stderr": self.stderr[:2000],
            "exit_code": self.exit_code,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "truncated": self.truncated,
            "killed_by_timeout": self.killed_by_timeout,
        }


CommandHook = Callable[[ShellCommand], Optional[ShellCommand]]


BUILTIN_ALLOWLIST: Set[str] = {
    "echo", "cat", "ls", "pwd", "date", "whoami", "uname",
    "head", "tail", "wc", "sort", "uniq", "grep", "find",
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "stat",
    "python", "python3", "node", "npm", "npx", "pip", "pip3",
    "git", "curl", "wget", "tar", "zip", "unzip", "diff",
    "which", "type", "env", "printenv", "basename", "dirname",
    "tr", "cut", "awk", "sed", "tee", "xargs", "printf",
}

BUILTIN_DENYLIST: Set[str] = {
    "shutdown", "reboot", "halt", "poweroff", "init",
    "mkfs", "fdisk", "dd", "mount", "umount", "mkswap",
    "sudo", "su", "passwd", "chown", "chroot",
    "iptables", "ufw", "firewall-cmd", "systemctl",
    "kill", "killall", "pkill", "reboot", "shutdown",
    "crontab", "at", "batch",
}

DANGEROUS_FLAG_PATTERNS: List[str] = [
    r'--no-preserve-root', r'>\s*/dev/', r'rm\s+-rf\s+/',
    r'chmod\s+777', r':\(\)\s*\{',
]


@dataclass
class HookRule:
    hook_id: str
    command_pattern: str
    hook: CommandHook
    position: str = "pre"
    description: str = ""
    enabled: bool = True

    def matches(self, command: str) -> bool:
        return bool(re.search(self.command_pattern, command, re.IGNORECASE))


class ShellHookManager:
    """Controlled shell command execution with comprehensive safety."""

    _instance: Optional["ShellHookManager"] = None

    def __init__(self, allowlist: Optional[Set[str]] = None,
                 denylist: Optional[Set[str]] = None):
        self._allowlist = allowlist or set(BUILTIN_ALLOWLIST)
        self._denylist = denylist or set(BUILTIN_DENYLIST)
        self._pre_hooks: List[HookRule] = []
        self._post_hooks: List[HookRule] = []
        self._registry: Dict[str, HookRule] = {}
        self._total_executed = 0
        self._total_denied = 0
        self._total_timeouts = 0

    @classmethod
    def get_instance(cls) -> "ShellHookManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_to_allowlist(self, command: str) -> None:
        self._allowlist.add(command)

    def add_to_denylist(self, command: str) -> None:
        self._denylist.add(command)

    def remove_from_allowlist(self, command: str) -> None:
        self._allowlist.discard(command)

    def register_hook(self, hook: HookRule) -> None:
        self._registry[hook.hook_id] = hook
        if hook.position == "pre":
            self._pre_hooks.append(hook)
        elif hook.position == "post":
            self._post_hooks.append(hook)

    def unregister_hook(self, hook_id: str) -> bool:
        if hook_id in self._registry:
            hook = self._registry[hook_id]
            self._registry.pop(hook_id)
            if hook.position == "pre":
                self._pre_hooks.remove(hook)
            else:
                self._post_hooks.remove(hook)
            return True
        return False

    def check_permission(self, command: str) -> Tuple[ShellPermission, str]:
        """Determine if a command is allowed to execute."""
        cmd_base = command.split()[0] if command.strip() else ""

        if cmd_base in self._denylist:
            return ShellPermission.DENY, f"Command '{cmd_base}' is denylisted"

        for pattern in DANGEROUS_FLAG_PATTERNS:
            if re.search(pattern, command):
                return ShellPermission.DENY, f"Command contains dangerous pattern: '{pattern}'"

        if cmd_base not in self._allowlist:
            return ShellPermission.ASK, f"Command '{cmd_base}' is not in allowlist"

        return ShellPermission.ALLOW, ""

    def execute(self, cmd: ShellCommand) -> ShellResult:
        """Execute a shell command with full safety checks."""
        self._total_executed += 1
        import uuid
        cmd_id = uuid.uuid4().hex[:12]

        full_command = cmd.command
        if cmd.args:
            full_command = f"{cmd.command} {' '.join(shlex.quote(a) for a in cmd.args)}"

        permission, reason = self.check_permission(full_command)
        if permission == ShellPermission.DENY:
            self._total_denied += 1
            return ShellResult(
                stdout="", stderr=f"Permission denied: {reason}",
                exit_code=1, duration_ms=0, command_id=cmd_id,
            )

        modified_cmd = cmd
        for hook_rule in self._pre_hooks:
            if hook_rule.enabled and hook_rule.matches(full_command):
                result = hook_rule.hook(modified_cmd)
                if result is not None:
                    modified_cmd = result

        start_time = time.monotonic()

        try:
            cmd_args = [modified_cmd.command]
            if modified_cmd.args:
                cmd_args.extend(modified_cmd.args)

            process = subprocess.run(
                full_command if modified_cmd.shell else cmd_args,
                shell=modified_cmd.shell,
                cwd=modified_cmd.cwd,
                env=modified_cmd.env,
                input=modified_cmd.stdin_data,
                capture_output=True,
                text=True,
                timeout=modified_cmd.timeout,
            )

            duration_ms = (time.monotonic() - start_time) * 1000

            stdout = process.stdout or ""
            stderr = process.stderr or ""
            truncated = False

            if len(stdout) > modified_cmd.max_output_bytes:
                stdout = stdout[:modified_cmd.max_output_bytes] + "\n... [output truncated]"
                truncated = True
            if len(stderr) > modified_cmd.max_output_bytes:
                stderr = stderr[:modified_cmd.max_output_bytes] + "\n... [output truncated]"

            result = ShellResult(
                stdout=stdout, stderr=stderr,
                exit_code=process.returncode,
                duration_ms=duration_ms,
                truncated=truncated,
                command_id=cmd_id,
            )

        except subprocess.TimeoutExpired:
            self._total_timeouts += 1
            duration_ms = (time.monotonic() - start_time) * 1000
            result = ShellResult(
                stdout="", stderr=f"Command timed out after {cmd.timeout}s",
                exit_code=124, duration_ms=duration_ms,
                killed_by_timeout=True, command_id=cmd_id,
            )

        except FileNotFoundError:
            result = ShellResult(
                stdout="", stderr=f"Command not found: {cmd.command}",
                exit_code=127, duration_ms=0, command_id=cmd_id,
            )

        except Exception as e:
            result = ShellResult(
                stdout="", stderr=f"Execution error: {e}",
                exit_code=1, duration_ms=0, command_id=cmd_id,
            )

        for hook_rule in self._post_hooks:
            if hook_rule.enabled and hook_rule.matches(full_command):
                hook_rule.hook(modified_cmd)

        return result

    def execute_script(self, script: str, timeout: float = 30.0) -> ShellResult:
        """Execute a multiline script safely."""
        safe_script = self._sanitize_script(script)
        cmd = ShellCommand(
            command=safe_script,
            shell=True,
            timeout=timeout,
        )
        return self.execute(cmd)

    def _sanitize_script(self, script: str) -> str:
        """Remove obviously dangerous script patterns."""
        lines = script.split("\n")
        safe_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                safe_lines.append(line)
                continue
            cmd_base = stripped.split()[0] if stripped else ""
            if cmd_base in self._denylist:
                safe_lines.append(f"# BLOCKED: {line}")
                continue
            dangerous = False
            for pattern in DANGEROUS_FLAG_PATTERNS:
                if re.search(pattern, stripped):
                    safe_lines.append(f"# BLOCKED (dangerous pattern): {line}")
                    dangerous = True
                    break
            if not dangerous:
                safe_lines.append(line)
        return "\n".join(safe_lines)

    def list_allowlist(self) -> List[str]:
        return sorted(self._allowlist)

    def list_denylist(self) -> List[str]:
        return sorted(self._denylist)

    def list_hooks(self) -> List[Dict[str, Any]]:
        return [{
            "hook_id": h.hook_id,
            "description": h.description,
            "position": h.position,
            "enabled": h.enabled,
        } for h in self._registry.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_executed": self._total_executed,
            "total_denied": self._total_denied,
            "total_timeouts": self._total_timeouts,
            "allowlist_size": len(self._allowlist),
            "denylist_size": len(self._denylist),
            "pre_hooks_count": len(self._pre_hooks),
            "post_hooks_count": len(self._post_hooks),
            "deny_rate": (self._total_denied / self._total_executed * 100)
            if self._total_executed > 0 else 0.0,
        }


def get_shell_hooks() -> ShellHookManager:
    return ShellHookManager.get_instance()
