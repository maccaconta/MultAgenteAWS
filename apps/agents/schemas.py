from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    session_id: int
    user_id: int
    blueprint_slug: str
    prompt_bundle: dict[str, Any]
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    latest_user_message: str = ''
    team_binding: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentDecision:
    role: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
