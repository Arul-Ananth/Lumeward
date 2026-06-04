from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.common.config import settings
from backend.common.services.security_policy import PolicyDecision

INSTRUCTION_PREFIXES = (
    "thought:",
    "action:",
    "action input:",
    "observation:",
    "final answer:",
    "important:",
    "tool name:",
    "tool arguments:",
    "tool description:",
    "you only have access",
    "moving on then.",
)

SECRET_PATTERNS = (
    re.compile(r"\b(sk-[A-Za-z0-9_-]{16,})\b"),
    re.compile(r"\b(AIza[0-9A-Za-z_-]{20,})\b"),
    re.compile(r"\b(ghp_[0-9A-Za-z_]{20,})\b"),
    re.compile(r"\b(xox[baprs]-[0-9A-Za-z-]{20,})\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\"]{8,})"),
)


class SecureAction(BaseModel):
    action_type: Literal["read_file", "web_search"]
    target: str = Field(min_length=1, max_length=2048)
    query: str | None = Field(default=None, max_length=2048)


class InputSanitizer:
    def sanitize_context(self, text: str) -> str:
        cleaned_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower = line.lower()
            if any(lower.startswith(prefix) for prefix in INSTRUCTION_PREFIXES):
                continue
            if "/docs/" in lower or lower.endswith(".md"):
                continue
            if lower.startswith("```") or lower.endswith("```"):
                continue
            if lower.startswith("tool "):
                continue
            cleaned_lines.append(self.mask_secrets(raw_line))
        return "\n".join(cleaned_lines).strip()

    def mask_secrets(self, text: str) -> str:
        masked = text
        for pattern in SECRET_PATTERNS:
            masked = pattern.sub(self._mask_match, masked)
        return masked

    @staticmethod
    def _mask_match(match: re.Match[str]) -> str:
        if len(match.groups()) >= 2:
            return f"{match.group(1)}=[REDACTED]"
        return "[REDACTED]"


class SecurityPolicy:
    def __init__(self, allowed_roots: list[Path] | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        data_dir = settings.DATA_DIR.resolve()
        self.allowed_roots = [path.resolve() for path in (allowed_roots or [root, data_dir])]

    def validate_and_execute(self, action: SecureAction) -> dict[str, Any]:
        if action.action_type == "read_file":
            return self._read_file(action.target)
        if action.action_type == "web_search":
            return self._web_search(action.query or action.target)
        return {"allowed": False, "reason": "unsupported_action", "action": action.action_type}

    def _read_file(self, target: str) -> dict[str, Any]:
        path = Path(target).expanduser().resolve()
        if not self._is_allowed_path(path):
            return {"allowed": False, "reason": "path_outside_allowed_roots", "target": str(path)}
        if not path.is_file():
            return {"allowed": False, "reason": "not_a_file", "target": str(path)}
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"allowed": True, "target": str(path), "content": InputSanitizer().sanitize_context(text)}

    def _web_search(self, query: str) -> dict[str, Any]:
        from backend.common.services.llm.tool_policy import build_search_tools

        tools = build_search_tools({})
        if not tools:
            return {"allowed": False, "reason": "web_search_unavailable", "query": query}
        return {"allowed": True, "query": query, "result": tools[0].run(query)}

    def _is_allowed_path(self, path: Path) -> bool:
        return any(path == root or root in path.parents for root in self.allowed_roots)

    def validate_network_decision(self, decision: PolicyDecision) -> dict[str, Any]:
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "action": decision.action,
            "target": decision.target,
        }
