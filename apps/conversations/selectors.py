from __future__ import annotations

from apps.conversations.models import ConversationSession


class ConversationSelector:
    @staticmethod
    def session_detail(session_id: int, user_id: int) -> ConversationSession:
        return ConversationSession.objects.select_related(
            'blueprint', 'persona', 'scenario', 'specialty', 'policy', 'output_contract', 'instruction'
        ).prefetch_related('turns__agent_runs').get(pk=session_id, user_id=user_id)
