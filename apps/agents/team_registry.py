from __future__ import annotations

from typing import Any

from core.config import AppConfig


class BedrockTeamRegistry:
    """Le o manifesto local que mapeia cada blueprint ao seu time Bedrock."""

    @staticmethod
    def get_team_for_blueprint(blueprint_slug: str) -> dict[str, Any]:
        payload = AppConfig.load_manifest()
        return payload.get('blueprints', {}).get(blueprint_slug, {})

    @staticmethod
    def save_team_for_blueprint(blueprint_slug: str, team: dict[str, Any]) -> None:
        payload = AppConfig.load_manifest()
        payload.setdefault('blueprints', {})[blueprint_slug] = team
        AppConfig.save_manifest(payload)
