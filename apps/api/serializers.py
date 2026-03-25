from __future__ import annotations

from typing import Any


def session_payload(session) -> dict[str, Any]:
    return {
        'id': session.pk,
        'title': session.title,
        'status': session.status,
        'blueprint': session.blueprint.slug,
        'persona': session.persona.title,
        'scenario': session.scenario.title,
        'specialty': session.specialty.title,
    }
