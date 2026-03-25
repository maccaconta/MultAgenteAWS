from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.agents.bedrock import BedrockAgentPlatformClient
from apps.agents.prompting import PromptComposer
from apps.agents.team_registry import BedrockTeamRegistry
from apps.catalog.models import SimulationBlueprint
from apps.catalog.services import BlueprintService
from core.config import AppConfig


@dataclass
class TeamProvisioningResult:
    blueprint_slug: str
    supervisor: dict[str, Any]
    collaborators: dict[str, Any]


class BedrockTeamProvisioner:
    """Cria os agentes Bedrock nativos e persiste um manifesto local.

    Estrategia:
    1. Cria quatro agentes colaboradores especializados.
    2. Cria o agente supervisor.
    3. Associa a knowledge base ao colaborador de consulta.
    4. Associa os colaboradores ao supervisor.
    5. Prepara e cria aliases.
    """

    def __init__(self, client: BedrockAgentPlatformClient | None = None) -> None:
        self.client = client or BedrockAgentPlatformClient()

    def _create_and_alias(self, *, name: str, model_id: str, instruction: str, description: str) -> dict[str, Any]:
        created = self.client.create_agent(name=name, model_id=model_id, instruction=instruction, description=description)
        agent = created['agent']
        agent_id = agent['agentId']
        self.client.prepare_agent(agent_id)
        alias = self.client.create_agent_alias(agent_id, alias_name='prod')
        alias_payload = alias['agentAlias']
        return {
            'agent_id': agent_id,
            'agent_name': agent.get('agentName', name),
            'alias_id': alias_payload['agentAliasId'],
            'alias_arn': alias_payload['agentAliasArn'],
        }

    def provision_blueprint_team(self, blueprint: SimulationBlueprint) -> TeamProvisioningResult:
        bundle = BlueprintService.export_bundle_as_prompt_json(BlueprintService.load_bundle(blueprint))
        bundle['persona'] = blueprint.persona.payload
        bundle['scenario'] = blueprint.scenario.payload
        bundle['specialty'] = blueprint.specialty.payload
        bundle['policy'] = blueprint.policy.payload
        bundle['output_contract'] = blueprint.output_contract.payload
        bundle['instruction'] = blueprint.instruction.payload
        bundle['evaluation_rubric'] = blueprint.evaluation_rubric.payload if blueprint.evaluation_rubric else None

        collaborators = {
            'consultation': self._create_and_alias(
                name=f'{blueprint.slug}-consultation',
                model_id=AppConfig.BEDROCK_TURN_MODEL_ID,
                instruction=PromptComposer.compose_consultation_instruction(bundle),
                description='Agente colaborador de consulta e recuperacao de evidencias.',
            ),
            'synthesis': self._create_and_alias(
                name=f'{blueprint.slug}-synthesis',
                model_id=AppConfig.BEDROCK_TURN_MODEL_ID,
                instruction=PromptComposer.compose_synthesis_instruction(bundle),
                description='Agente colaborador que responde como medico simulado.',
            ),
            'compliance': self._create_and_alias(
                name=f'{blueprint.slug}-compliance',
                model_id=AppConfig.BEDROCK_SUMMARIZE_MODEL_ID,
                instruction=PromptComposer.compose_compliance_instruction(bundle),
                description='Agente colaborador de compliance promocional e cientifico.',
            ),
            'evaluation': self._create_and_alias(
                name=f'{blueprint.slug}-evaluation',
                model_id=AppConfig.BEDROCK_EVALUATE_MODEL_ID,
                instruction=PromptComposer.compose_evaluation_instruction(bundle),
                description='Agente colaborador de avaliacao do desempenho do propagandista.',
            ),
        }

        if AppConfig.BEDROCK_KB_ID:
            self.client.associate_knowledge_base(
                agent_id=collaborators['consultation']['agent_id'],
                kb_id=AppConfig.BEDROCK_KB_ID,
                description=f'Knowledge Base da simulacao {blueprint.slug}',
            )

        supervisor = self._create_and_alias(
            name=f'{blueprint.slug}-supervisor',
            model_id=AppConfig.BEDROCK_SUPERVISOR_MODEL_ID,
            instruction=PromptComposer.compose_supervisor_instruction(bundle),
            description='Agente supervisor do time multiagente de simulacao medica.',
        )

        self.client.associate_collaborator(
            supervisor_agent_id=supervisor['agent_id'],
            collaborator_alias_arn=collaborators['consultation']['alias_arn'],
            collaborator_name='consultation',
            instruction='Recupere evidencias, fatos e citacoes na base de conhecimento.',
        )
        self.client.associate_collaborator(
            supervisor_agent_id=supervisor['agent_id'],
            collaborator_alias_arn=collaborators['synthesis']['alias_arn'],
            collaborator_name='synthesis',
            instruction='Responda como medico simulado, com realismo e objecoes plausiveis.',
        )
        self.client.associate_collaborator(
            supervisor_agent_id=supervisor['agent_id'],
            collaborator_alias_arn=collaborators['compliance']['alias_arn'],
            collaborator_name='compliance',
            instruction='Valide claims e reescreva em caso de risco promocional.',
        )
        self.client.associate_collaborator(
            supervisor_agent_id=supervisor['agent_id'],
            collaborator_alias_arn=collaborators['evaluation']['alias_arn'],
            collaborator_name='evaluation',
            instruction='Pontue o propagandista e devolva coaching objetivo.',
        )
        self.client.prepare_agent(supervisor['agent_id'])

        team = {'supervisor': supervisor, 'collaborators': collaborators, 'knowledge_base_id': AppConfig.BEDROCK_KB_ID}
        BedrockTeamRegistry.save_team_for_blueprint(blueprint.slug, team)
        return TeamProvisioningResult(blueprint_slug=blueprint.slug, supervisor=supervisor, collaborators=collaborators)
