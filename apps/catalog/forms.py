from __future__ import annotations

from django import forms

from apps.catalog.models import (
    SimulationBlueprint,
    PersonaDefinition,
    ScenarioDefinition,
    SpecialtyDefinition,
)


class SimulationLaunchForm(forms.Form):
    blueprint = forms.ModelChoiceField(
        queryset=SimulationBlueprint.objects.filter(is_active=True).order_by('title'),
        empty_label='Selecione um blueprint',
    )
    persona = forms.ModelChoiceField(
        queryset=PersonaDefinition.objects.filter(is_active=True).order_by('title'),
        empty_label='Selecione uma persona',
        required=False,
    )
    scenario = forms.ModelChoiceField(
        queryset=ScenarioDefinition.objects.filter(is_active=True).order_by('title'),
        empty_label='Selecione um cenario',
        required=False,
    )
    specialty = forms.ModelChoiceField(
        queryset=SpecialtyDefinition.objects.filter(is_active=True).order_by('title'),
        empty_label='Selecione uma especialidade',
        required=False,
    )
