from __future__ import annotations

from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views import View

from apps.agents.services import BedrockNativeSupervisorOrchestrator
from apps.conversations.models import ConversationSession


def get_session(request: HttpRequest, session_id: int):
    session = get_object_or_404(ConversationSession, pk=session_id)
    return JsonResponse(
        {
            "id": session.id,
            "title": session.title,
            "status": session.status,
            "blueprint": getattr(session.blueprint, "title", ""),
            "persona": getattr(session.persona, "title", ""),
            "scenario": getattr(session.scenario, "title", ""),
            "specialty": getattr(session.specialty, "title", ""),
        }
    )


def evaluate_session(request: HttpRequest, session_id: int):
    session = get_object_or_404(ConversationSession, pk=session_id)
    latest_turn = session.turns.filter(role="user").order_by("-sequence").first()
    latest_message = latest_turn.content if latest_turn else ""
    orchestrator = BedrockNativeSupervisorOrchestrator()
    result = orchestrator.process_turn(session, latest_message)
    return JsonResponse(
        {
            "reply": result["final_reply"],
            "evaluation": result["evaluation"],
            "compliance": result["compliance"],
            "citations": result.get("citations", []),
            "team_summary": result.get("team_summary", []),
        }
    )


class SessionEvaluateView(View):
    def post(self, request, session_id: int, *args, **kwargs):
        return evaluate_session(request, session_id)
