from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from core.config import AppConfig
from apps.conversations.models import AgentRun, ConversationSession, ConversationTurn


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            return str(value)
    return str(value)


@dataclass
class AgentResult:
    role: str
    content: str
    payload: dict
    telemetry: dict


class ConversationSessionService:
    @staticmethod
    def create_session_from_form(user, cleaned_data):
        blueprint = cleaned_data["blueprint"]

        persona = cleaned_data.get("persona") or blueprint.persona
        scenario = cleaned_data.get("scenario") or blueprint.scenario
        specialty = cleaned_data.get("specialty") or blueprint.specialty

        manifest = AppConfig.load_manifest().get("blueprints", {})
        bedrock_team = manifest.get(blueprint.slug) or manifest.get("default")

        if not bedrock_team:
            raise RuntimeError(
                f"Nao foi possivel resolver o binding Bedrock para o blueprint '{blueprint.slug}'."
            )

        session = ConversationSession.objects.create(
            user=user,
            title=f"{blueprint.title} - {persona.title}",
            blueprint=blueprint,
            persona=persona,
            scenario=scenario,
            specialty=specialty,
            policy=blueprint.policy,
            instruction=blueprint.instruction,
            output_contract=blueprint.output_contract,
            evaluation_rubric=blueprint.evaluation_rubric,
            status="active",
            session_state={"bedrock_team": _json_safe(bedrock_team)},
        )
        return session


class ConversationTurnService:
    @staticmethod
    def append_turn(
        session: ConversationSession,
        *,
        role: str,
        content: str,
        speaker_name: str = "",
        input_payload: dict | None = None,
        output_payload: dict | None = None,
        evidence_payload: dict | None = None,
        telemetry: dict | None = None,
    ) -> ConversationTurn:
        next_sequence = (session.turns.order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1

        return ConversationTurn.objects.create(
            session=session,
            sequence=next_sequence,
            role=role,
            content=content,
            speaker_name=speaker_name,
            input_payload=_json_safe(input_payload or {}),
            output_payload=_json_safe(output_payload or {}),
            evidence_payload=_json_safe(evidence_payload or {}),
            telemetry=_json_safe(telemetry or {}),
        )

    @staticmethod
    def register_agent_run(turn: ConversationTurn, agent_result: AgentResult) -> AgentRun:
        return AgentRun.objects.create(
            turn=turn,
            role=agent_result.role,
            content=agent_result.content,
            payload=_json_safe(agent_result.payload or {}),
            telemetry=_json_safe(agent_result.telemetry or {}),
        )
