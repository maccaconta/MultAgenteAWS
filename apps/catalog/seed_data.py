from __future__ import annotations

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


def seed_default_catalog() -> dict:
    persona_risco, _ = PersonaDefinition.objects.update_or_create(
        slug='persona-risco-v1',
        defaults={
            'title': 'Persona 1 - Risco',
            'description': 'Medico direto, exigente e orientado a resultado.',
            'payload': {
                'nome': 'Dr. Roberto Sato',
                'perfil_psicologico': 'Assertivo, pragmatico e orientado a resultado.',
                'preferencias': 'Conversas curtas e objetivas com abordagem direta e dominio total do conteudo.',
                'profissao': 'Medico psiquiatra',
            },
            'is_active': True,
            'tags': ['persona', 'risco', 'tdah'],
        },
    )

    persona_normas, _ = PersonaDefinition.objects.update_or_create(
        slug='persona-normas-v1',
        defaults={
            'title': 'Persona 3 - Normas',
            'description': 'Medica analitica, organizada e exigente com qualidade.',
            'payload': {
                'nome': 'Dra. Aline',
                'perfil_psicologico': 'Analitica, exigente e perfeccionista.',
                'preferencias': 'Comunicacao tecnica, logica e bem organizada.',
                'profissao': 'Medica psiquiatra',
            },
            'is_active': True,
            'tags': ['persona', 'normas', 'tdah'],
        },
    )

    scenario_tdh, _ = ScenarioDefinition.objects.update_or_create(
        slug='cenario-tdah-adulto-v1',
        defaults={
            'title': 'Cenario 1 - TDAH adulto',
            'description': 'Paciente adulta com perda de efeito no final da tarde.',
            'payload': {
                'nome': 'Cenario 1 - TDAH adulto',
                'produto': 'Lyberdia',
                'perfil_paciente': 'Mulher, 35 anos, executiva de tecnologia',
                'historico': 'Diagnosticada com TDAH ha 1 ano',
                'tratamento_atual': 'Psicoestimulante pela manha',
                'queixa': 'A medicacao funciona bem de manha, mas perde efeito no fim do dia.',
                'desafio': 'Manter atencao e disposicao ate o fim da tarde sem piorar o sono.',
                'argumento_medicamento': 'Lyberdia permite ajuste fino de dose com sustentacao no periodo da tarde.',
            },
            'is_active': True,
            'tags': ['cenario', 'tdah', 'lyberdia'],
        },
    )

    specialty_psiq, _ = SpecialtyDefinition.objects.update_or_create(
        slug='especialidade-psiquiatria-tdah-v1',
        defaults={
            'title': 'Psiquiatria - TDAH adulto',
            'description': 'Contexto clinico de TDAH adulto.',
            'payload': {
                'meta': {'tipo': 'especialidade', 'id': 'psiquiatria_tdah_adulto', 'versao': 'v1'},
                'conteudo': {
                    'descricao_curta': 'Avaliacao clinica de sintomas de desatencao, impulsividade e prejuizo funcional em adultos com TDAH.',
                    'pontos_chave': [
                        'impacto funcional no trabalho e relacoes',
                        'oscilacao do efeito ao longo do dia',
                        'aderencia',
                        'qualidade de vida',
                        'comorbidades',
                    ],
                },
            },
            'is_active': True,
            'tags': ['especialidade', 'psiquiatria', 'tdah'],
        },
    )

    policy_default, _ = PolicyDefinition.objects.update_or_create(
        slug='politicas-farma-v1',
        defaults={
            'title': 'Politicas padrao',
            'description': 'Politicas promocionais e cientificas para simulacao.',
            'payload': {'regras': ['nao inventar fatos', 'nao extrapolar beneficio sem base', 'nao sugerir uso off-label', 'nao afirmar superioridade sem evidencia', 'explicitar limitacoes quando faltar suporte']},
            'is_active': True,
            'tags': ['policy', 'compliance', 'farma'],
        },
    )

    instruction_default, _ = InstructionDefinition.objects.update_or_create(
        slug='instrucao-simulacao-v1',
        defaults={
            'title': 'Instrucao geral da simulacao',
            'description': 'Instrucao geral compartilhada entre supervisor e colaboradores.',
            'payload': {'systemRules': ['responder em portugues do Brasil', 'manter o papel de medico simulado na resposta final', 'usar o contexto de persona, cenario, especialidade e politicas', 'nao inventar evidencias'], 'finalInstruction': 'A resposta final deve ser util para treinamento do propagandista, realista para um medico e alinhada ao contrato JSON do supervisor.'},
            'is_active': True,
            'tags': ['instruction', 'simulacao'],
        },
    )

    output_contract, _ = OutputContractDefinition.objects.update_or_create(
        slug='contrato-supervisor-v1',
        defaults={
            'title': 'Contrato do supervisor',
            'description': 'Contrato JSON esperado da resposta final do supervisor.',
            'payload': {'final_reply': 'string', 'evaluation': {}, 'compliance': {}, 'citations': [], 'team_summary': []},
            'is_active': True,
            'tags': ['output', 'json'],
        },
    )

    rubric_default, _ = EvaluationRubricDefinition.objects.update_or_create(
        slug='rubrica-propagandista-v1',
        defaults={
            'title': 'Rubrica de avaliacao do propagandista',
            'description': 'Rubrica padrao para avaliacao.',
            'payload': {'dimensoes': [{'nome': 'clareza', 'peso': 0.2}, {'nome': 'investigacao_de_necessidade', 'peso': 0.2}, {'nome': 'dominio_tecnico', 'peso': 0.2}, {'nome': 'manejo_de_objecoes', 'peso': 0.2}, {'nome': 'compliance', 'peso': 0.2}], 'escala': {'min': 1, 'max': 5}},
            'is_active': True,
            'tags': ['rubrica', 'avaliacao'],
        },
    )

    bp1, _ = SimulationBlueprint.objects.update_or_create(
        slug='default',
        defaults={
            'title': 'Blueprint padrao - TDAH adulto / Lyberdia',
            'description': 'Blueprint inicial da simulacao.',
            'persona': persona_risco,
            'scenario': scenario_tdh,
            'specialty': specialty_psiq,
            'policy': policy_default,
            'instruction': instruction_default,
            'output_contract': output_contract,
            'evaluation_rubric': rubric_default,
            'is_active': True,
        },
    )

    bp2, _ = SimulationBlueprint.objects.update_or_create(
        slug='default-normas',
        defaults={
            'title': 'Blueprint alternativo - Perfil normas',
            'description': 'Mesmo cenario com persona mais analitica e exigente.',
            'persona': persona_normas,
            'scenario': scenario_tdh,
            'specialty': specialty_psiq,
            'policy': policy_default,
            'instruction': instruction_default,
            'output_contract': output_contract,
            'evaluation_rubric': rubric_default,
            'is_active': True,
        },
    )
    return {'blueprints': [bp1.slug, bp2.slug]}
