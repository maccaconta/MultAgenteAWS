from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DefinitionBase(TimeStampedModel):
    slug = models.SlugField(unique=True, max_length=120)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        abstract = True
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def as_prompt_payload(self) -> dict:
        return {
            "id": self.pk,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "payload": self.payload,
        }


class PersonaDefinition(DefinitionBase):
    pass


class ScenarioDefinition(DefinitionBase):
    pass


class SpecialtyDefinition(DefinitionBase):
    pass


class PolicyDefinition(DefinitionBase):
    pass


class InstructionDefinition(DefinitionBase):
    pass


class OutputContractDefinition(DefinitionBase):
    pass


class EvaluationRubricDefinition(DefinitionBase):
    pass


class SimulationBlueprint(TimeStampedModel):
    slug = models.SlugField(unique=True, max_length=120)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    persona = models.ForeignKey(PersonaDefinition, on_delete=models.PROTECT, related_name='blueprints')
    scenario = models.ForeignKey(ScenarioDefinition, on_delete=models.PROTECT, related_name='blueprints')
    specialty = models.ForeignKey(SpecialtyDefinition, on_delete=models.PROTECT, related_name='blueprints')
    policy = models.ForeignKey(PolicyDefinition, on_delete=models.PROTECT, related_name='blueprints')
    output_contract = models.ForeignKey(OutputContractDefinition, on_delete=models.PROTECT, related_name='blueprints')
    instruction = models.ForeignKey(InstructionDefinition, on_delete=models.PROTECT, related_name='blueprints')
    evaluation_rubric = models.ForeignKey(
        EvaluationRubricDefinition,
        on_delete=models.PROTECT,
        related_name='blueprints',
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title
