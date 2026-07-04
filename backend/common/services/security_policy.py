from __future__ import annotations

import ipaddress
import json
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.common.config import settings

logger = logging.getLogger("lumeward.security")

ALLOWED_NETWORK_ACTIONS = {
    "engine.health",
    "engine.request",
    "search.serper",
    "search.discovery",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    action: str
    target: str


def _normalized_origin(target: str) -> tuple[str, str, int] | None:
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname, port


def _is_configured_engine_target(target: str) -> bool:
    if not settings.ENGINE_ENABLED:
        return False
    engine_origin = _normalized_origin(settings.engine_base_url())
    target_origin = _normalized_origin(target)
    return engine_origin is not None and engine_origin == target_origin


def _is_denied_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not address.is_global


def _resolve_addresses(host: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        addresses.add(ipaddress.ip_address(result[4][0]))
    return addresses


def authorize_network_action(action: str, target: str) -> PolicyDecision:
    if action not in ALLOWED_NETWORK_ACTIONS:
        return PolicyDecision(False, "action_not_allowed", action, target)

    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"}:
        return PolicyDecision(False, "scheme_not_allowed", action, target)

    host = parsed.hostname
    if not host:
        return PolicyDecision(False, "missing_host", action, target)
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return PolicyDecision(False, "invalid_port", action, target)

    if action.startswith("engine."):
        if _is_configured_engine_target(target):
            return PolicyDecision(True, "allowed", action, target)
        return PolicyDecision(False, "engine_target_not_allowlisted", action, target)

    try:
        literal_address = ipaddress.ip_address(host)
    except ValueError:
        literal_address = None

    if literal_address is not None and _is_denied_address(literal_address):
        return PolicyDecision(False, "private_address_denied", action, target)

    if host.rstrip(".").lower() == "localhost":
        return PolicyDecision(False, "localhost_denied", action, target)

    if literal_address is None:
        try:
            addresses = _resolve_addresses(host, port)
        except (OSError, ValueError):
            return PolicyDecision(False, "host_resolution_failed", action, target)
        if not addresses:
            return PolicyDecision(False, "host_resolution_failed", action, target)
        if any(_is_denied_address(address) for address in addresses):
            return PolicyDecision(False, "private_address_denied", action, target)

    return PolicyDecision(True, "allowed", action, target)


def audit_policy_decision(
    *,
    decision: PolicyDecision,
    tool_name: str,
    query: str,
    session_id: str | None = None,
    user_id: str | int | None = None,
) -> None:
    payload = {
        "event": "security_policy_decision",
        "tool": tool_name,
        "action": decision.action,
        "target": decision.target,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "query": query[:300],
        "session_id": session_id or "",
        "user_id": str(user_id) if user_id is not None else "",
    }
    logger.info(json.dumps(payload, sort_keys=True))
