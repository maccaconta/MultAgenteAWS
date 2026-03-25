from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class AppConfig:
    """Centraliza a leitura das variaveis de ambiente da aplicacao.

    O Django continua usando config/settings.py para configuracao do framework.
    Este arquivo guarda apenas configuracoes funcionais do dominio Bedrock,
    Knowledge Bases, agentes nativos e parametros operacionais do simulador.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent
    VAR_DIR = BASE_DIR / 'var'
    VAR_DIR.mkdir(exist_ok=True)

    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN')

    BEDROCK_KB_ID = os.environ.get('BEDROCK_KB_ID', '')
    BEDROCK_AGENT_ROLE_ARN = os.environ.get('BEDROCK_AGENT_ROLE_ARN', '')

    BEDROCK_TURN_MODEL_ID = os.environ.get('BEDROCK_TURN_MODEL_ID', 'amazon.nova-pro-v1:0')
    BEDROCK_EVALUATE_MODEL_ID = os.environ.get('BEDROCK_EVALUATE_MODEL_ID', 'amazon.nova-pro-v1:0')
    BEDROCK_SUMMARIZE_MODEL_ID = os.environ.get('BEDROCK_SUMMARIZE_MODEL_ID', 'amazon.nova-pro-v1:0')
    BEDROCK_SUPERVISOR_MODEL_ID = os.environ.get('BEDROCK_SUPERVISOR_MODEL_ID', BEDROCK_TURN_MODEL_ID)
    BEDROCK_AGENT_IDLE_SESSION_TTL = int(os.environ.get('BEDROCK_AGENT_IDLE_SESSION_TTL', '900'))
    BEDROCK_TIMEOUT_SECONDS = int(os.environ.get('BEDROCK_TIMEOUT_SECONDS', '20'))
    BEDROCK_ENABLE_TRACE = os.environ.get('BEDROCK_ENABLE_TRACE', 'true').lower() == 'true'
    BEDROCK_STREAM_FINAL_RESPONSE = os.environ.get('BEDROCK_STREAM_FINAL_RESPONSE', 'false').lower() == 'true'

    DEFAULT_TOP_K = int(os.environ.get('DEFAULT_TOP_K', '3'))
    DEFAULT_SCORE_THRESHOLD = float(os.environ.get('DEFAULT_SCORE_THRESHOLD', '0.1'))
    DEFAULT_MAX_OUTPUT_TOKENS = int(os.environ.get('DEFAULT_MAX_OUTPUT_TOKENS', '768'))
    DEFAULT_TEMPERATURE = float(os.environ.get('DEFAULT_TEMPERATURE', '0.2'))
    DEFAULT_TOP_P = float(os.environ.get('DEFAULT_TOP_P', '0.9'))

    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
    SES_SOURCE_EMAIL = os.environ.get('SES_SOURCE_EMAIL', DEFAULT_FROM_EMAIL)

    # Caminho para o manifesto dos agentes Bedrock criados pela aplicacao.
    BEDROCK_AGENT_TEAM_MANIFEST = os.environ.get(
        'BEDROCK_AGENT_TEAM_MANIFEST',
        str(VAR_DIR / 'bedrock_agent_team_manifest.json'),
    )

    # @classmethod
    # def load_manifest(cls) -> dict[str, Any]:
    #     path = Path(cls.BEDROCK_AGENT_TEAM_MANIFEST)
    #     if not path.exists():
    #         return {'blueprints': {}}
    #     return json.loads(path.read_text(encoding='utf-8'))
    

    @staticmethod
    def load_manifest():
        path = Path("bedrock_manifest.json")
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)



    @classmethod
    def save_manifest(cls, payload: dict[str, Any]) -> None:
        path = Path(cls.BEDROCK_AGENT_TEAM_MANIFEST)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def validate_minimum_runtime_config(cls) -> None:
        missing = []
        if not cls.AWS_REGION:
            missing.append('AWS_REGION')
        if missing:
            raise RuntimeError(f'Variaveis obrigatorias ausentes: {missing}')
