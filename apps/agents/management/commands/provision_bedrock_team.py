from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.agents.provisioning import BedrockTeamProvisioner
from apps.catalog.models import SimulationBlueprint
from core.config import AppConfig


class Command(BaseCommand):
    help = 'Cria um time de agentes nativos do Amazon Bedrock para um blueprint do simulador.'

    def add_arguments(self, parser):
        parser.add_argument('--blueprint', required=True, help='Slug do blueprint que sera convertido em time Bedrock.')

    def handle(self, *args, **options):
        AppConfig.validate_minimum_runtime_config()
        if not AppConfig.BEDROCK_AGENT_ROLE_ARN:
            raise CommandError('Defina BEDROCK_AGENT_ROLE_ARN antes de provisionar os agentes.')
        blueprint = SimulationBlueprint.objects.select_related(
            'persona', 'scenario', 'specialty', 'policy', 'output_contract', 'instruction', 'evaluation_rubric'
        ).filter(slug=options['blueprint']).first()
        if not blueprint:
            raise CommandError(f'Blueprint nao encontrado: {options["blueprint"]}')
        result = BedrockTeamProvisioner().provision_blueprint_team(blueprint)
        self.stdout.write(self.style.SUCCESS(f'Time Bedrock criado para blueprint {result.blueprint_slug}.'))
        self.stdout.write(f'Supervisor agent_id={result.supervisor["agent_id"]} alias_id={result.supervisor["alias_id"]}')
        for role, payload in result.collaborators.items():
            self.stdout.write(f'Collaborator {role}: agent_id={payload["agent_id"]} alias_id={payload["alias_id"]}')
