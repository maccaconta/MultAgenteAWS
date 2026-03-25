from __future__ import annotations

from decimal import Decimal

from apps.evaluations.models import EvaluationSnapshot


class EvaluationSnapshotService:
    @staticmethod
    def persist(session, turn_number: int, payload: dict):
        score = payload.get('score_global', 0) or 0
        return EvaluationSnapshot.objects.create(
            session=session,
            turn=turn_number,
            score_global=Decimal(str(score)),
            dimensions=payload.get('dimensoes', {}),
            strengths=payload.get('pontos_fortes', []),
            improvements=payload.get('pontos_melhorar', []),
            payload=payload,
        )
