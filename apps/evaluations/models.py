from __future__ import annotations

from django.db import models

from apps.conversations.models import ConversationSession


class EvaluationSnapshot(models.Model):
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='evaluation_snapshots')
    turn = models.PositiveIntegerField(default=0)
    score_global = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dimensions = models.JSONField(default=dict, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
