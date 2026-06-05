from __future__ import annotations

import re

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
    def validate_network_decision(self, decision: PolicyDecision) -> dict[str, Any]:
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "action": decision.action,
            "target": decision.target,
        }
