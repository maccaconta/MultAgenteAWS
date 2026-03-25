from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.catalog.models import (
    SimulationBlueprint,
    PersonaDefinition,
    ScenarioDefinition,
    SpecialtyDefinition,
    PolicyDefinition,
    InstructionDefinition,
    OutputContractDefinition,
    EvaluationRubricDefinition,
)


class ConversationSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Ativa'),
        ('completed', 'Concluida'),
        ('archived', 'Arquivada'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_sessions')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    blueprint = models.ForeignKey(SimulationBlueprint, on_delete=models.PROTECT, related_name='sessions')
    persona = models.ForeignKey(PersonaDefinition, on_delete=models.PROTECT, related_name='sessions')
    scenario = models.ForeignKey(ScenarioDefinition, on_delete=models.PROTECT, related_name='sessions')
    specialty = models.ForeignKey(SpecialtyDefinition, on_delete=models.PROTECT, related_name='sessions')
    policy = models.ForeignKey(PolicyDefinition, on_delete=models.PROTECT, related_name='sessions')
    instruction = models.ForeignKey(InstructionDefinition, on_delete=models.PROTECT, related_name='sessions')
    output_contract = models.ForeignKey(OutputContractDefinition, on_delete=models.PROTECT, related_name='sessions')
    evaluation_rubric = models.ForeignKey(
        EvaluationRubricDefinition,
        on_delete=models.PROTECT,
        related_name='sessions',
        null=True,
        blank=True,
    )

    session_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title


class ConversationTurn(models.Model):
    ROLE_CHOICES = [
        ('user', 'Usuario'),
        ('doctor_simulator', 'Medico simulado'),
        ('system', 'Sistema'),
    ]

    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='turns')
    sequence = models.PositiveIntegerField()
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    content = models.TextField()
    speaker_name = models.CharField(max_length=255, blank=True)

    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    evidence_payload = models.JSONField(default=dict, blank=True)
    telemetry = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence']
        unique_together = [('session', 'sequence')]

    def __str__(self) -> str:
        return f'{self.session_id}#{self.sequence} {self.role}'


class AgentRun(models.Model):
    turn = models.ForeignKey(ConversationTurn, on_delete=models.CASCADE, related_name='agent_runs')
    role = models.CharField(max_length=64)
    content = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    telemetry = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
