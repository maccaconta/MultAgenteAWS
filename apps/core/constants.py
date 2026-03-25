from __future__ import annotations

PROMPT_COMPONENT_TYPES = (
    ('persona', 'Persona'),
    ('scenario', 'Cenário'),
    ('specialty', 'Especialidade'),
    ('policy', 'Política'),
    ('output_contract', 'Contrato de saída'),
    ('instruction', 'Instrução do agente'),
    ('rubric', 'Rubrica de avaliação'),
)

SESSION_STATUS = (
    ('draft', 'Rascunho'),
    ('active', 'Ativa'),
    ('ended', 'Encerrada'),
    ('archived', 'Arquivada'),
)

TURN_ROLE = (
    ('user', 'Usuário'),
    ('doctor_simulator', 'Médico simulado'),
    ('system', 'Sistema'),
    ('coach', 'Coach'),
    ('evaluator', 'Avaliador'),
)

AGENT_ROLE = (
    ('orchestrator', 'Orquestrador'),
    ('consultation', 'Consulta'),
    ('synthesis', 'Síntese'),
    ('compliance', 'Compliance'),
    ('transaction', 'Transacional'),
    ('evaluation', 'Avaliação'),
)
