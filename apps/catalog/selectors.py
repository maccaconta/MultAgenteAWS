from __future__ import annotations

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


class CatalogSelector:
    @staticmethod
    def active_blueprints():
        return (
            SimulationBlueprint.objects.filter(is_active=True)
            .select_related(
                'persona',
                'scenario',
                'specialty',
                'policy',
                'instruction',
                'output_contract',
                'evaluation_rubric',
            )
            .order_by('title')
        )

    @staticmethod
    def active_components(component_type: str):
        mapping = {
            'persona': PersonaDefinition,
            'scenario': ScenarioDefinition,
            'specialty': SpecialtyDefinition,
            'policy': PolicyDefinition,
            'instruction': InstructionDefinition,
            'output_contract': OutputContractDefinition,
            'evaluation_rubric': EvaluationRubricDefinition,
        }
        model = mapping[component_type]
        return model.objects.filter(is_active=True).order_by('title')
