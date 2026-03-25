from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.catalog.models import (
    EvaluationRubricDefinition,
    InstructionDefinition,
    OutputContractDefinition,
    PersonaDefinition,
    PolicyDefinition,
    ScenarioDefinition,
    SimulationBlueprint,
    SpecialtyDefinition,
)


@dataclass
class BlueprintBundle:
    blueprint: SimulationBlueprint
    persona: PersonaDefinition
    scenario: ScenarioDefinition
    specialty: SpecialtyDefinition
    policy: PolicyDefinition
    output_contract: OutputContractDefinition
    instruction: InstructionDefinition
    evaluation_rubric: EvaluationRubricDefinition | None


class BlueprintService:
    @staticmethod
    def load_bundle(blueprint: SimulationBlueprint) -> BlueprintBundle:
        return BlueprintBundle(
            blueprint=blueprint,
            persona=blueprint.persona,
            scenario=blueprint.scenario,
            specialty=blueprint.specialty,
            policy=blueprint.policy,
            output_contract=blueprint.output_contract,
            instruction=blueprint.instruction,
            evaluation_rubric=blueprint.evaluation_rubric,
        )

    @staticmethod
    def export_bundle_as_prompt_json(bundle: BlueprintBundle) -> dict[str, Any]:
        return {
            'meta': {
                'blueprint': bundle.blueprint.slug,
                'title': bundle.blueprint.title,
            },
            'persona': bundle.persona.payload,
            'scenario': bundle.scenario.payload,
            'specialty': bundle.specialty.payload,
            'policy': bundle.policy.payload,
            'output_contract': bundle.output_contract.payload,
            'instruction': bundle.instruction.payload,
            'evaluation_rubric': bundle.evaluation_rubric.payload if bundle.evaluation_rubric else None,
        }
