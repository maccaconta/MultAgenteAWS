from __future__ import annotations

import logging
from datetime import datetime, timezone

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.agents.services import BedrockNativeSupervisorOrchestrator
from apps.conversations.models import ConversationSession
from apps.conversations.services import AgentResult, ConversationTurnService
from apps.evaluations.services import EvaluationSnapshotService

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulationConsumer(AsyncJsonWebsocketConsumer):
    orchestrator = BedrockNativeSupervisorOrchestrator()

    async def connect(self):
        self.session_id = int(self.scope["url_route"]["kwargs"]["session_id"])
        self.group_name = f"simulation_{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def _send_timeline_event(self, *, agent: str, title: str, message: str, status: str = "done", input_payload=None, output_payload=None):
        await self.send_json({"type": "timeline_event", "agent": agent, "title": title, "message": message, "status": status, "timestamp": _iso_now(), "input_payload": input_payload, "output_payload": output_payload})

    async def receive_json(self, content, **kwargs):
        try:
            message = content.get("message", "").strip()
            if not message:
                await self.send_json({"type": "error", "error": "Mensagem vazia."})
                return
            session = await self._get_session()
            await database_sync_to_async(ConversationTurnService.append_turn)(session, role="user", content=message, speaker_name=getattr(self.scope.get("user"), "username", "Usuario"), input_payload=content)
            await self._send_timeline_event(agent="supervisor", title="Orquestração iniciada", message="O supervisor recebeu a mensagem do usuário e iniciou a preparação do turno.", status="running", input_payload={"message": message})
            result = await database_sync_to_async(self.orchestrator.process_turn)(session, message)
            for event in result.get("timeline") or []:
                await self._send_timeline_event(agent=event.get("agent", "system"), title=event.get("title", "Etapa confirmada"), message=event.get("message", "Sem detalhe adicional."), status=event.get("status", "done"), input_payload=event.get("input_payload"), output_payload=event.get("output_payload"))
            evaluation_payload = result["evaluation"] or {}
            doctor_turn = await database_sync_to_async(ConversationTurnService.append_turn)(session, role="doctor_simulator", content=result["final_reply"], speaker_name=session.persona.title, output_payload={"final_reply": result["final_reply"], "evaluation": result["evaluation"], "compliance": result["compliance"], "factual_guard": result.get("factual_guard")}, evidence_payload={"citations": result["citations"]}, telemetry={"supervisor": result["supervisor"].telemetry, "trace_count": len(result["traces"])})
            await database_sync_to_async(ConversationTurnService.register_agent_run)(doctor_turn, AgentResult(role="bedrock_supervisor", content=result["supervisor"].message, payload={"input": {"message": message}, "output": result["supervisor"].payload}, telemetry=result["supervisor"].telemetry))
            if evaluation_payload:
                await database_sync_to_async(EvaluationSnapshotService.persist)(session, doctor_turn.sequence, evaluation_payload)
            await self.send_json({"type": "assistant_message", "turn_id": doctor_turn.id, "reply": result["final_reply"], "evaluation": evaluation_payload, "citations": result["citations"], "trace_count": len(result["traces"])})
        except Exception as exc:
            logger.exception("WS receive failed session_id=%s error=%s", getattr(self, "session_id", None), exc)
            await self.send_json({"type": "error", "error": "Ocorreu uma falha no processamento do turno. Revise a configuracao da sessao e tente novamente."})

    @database_sync_to_async
    def _get_session(self) -> ConversationSession:
        return ConversationSession.objects.select_related("blueprint", "persona", "scenario", "specialty", "policy", "output_contract", "instruction", "evaluation_rubric").get(pk=self.session_id)