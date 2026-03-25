from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings

from core.config import AppConfig
from apps.core.exceptions import BedrockInvocationError


@dataclass
class AgentInvocationResult:
    text: str
    raw: dict[str, Any]
    traces: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    latency_ms: int


class BedrockAgentPlatformClient:
    """Cliente unificado para control plane e runtime dos agentes nativos do Bedrock."""

    def __init__(self) -> None:
        shared_cfg = BotoConfig(read_timeout=AppConfig.BEDROCK_TIMEOUT_SECONDS, retries={'max_attempts': 3})
        self.control = boto3.client('bedrock-agent', region_name=settings.BEDROCK_REGION, config=shared_cfg)
        self.runtime = boto3.client('bedrock-agent-runtime', region_name=settings.BEDROCK_REGION, config=shared_cfg)

    def create_agent(self, *, name: str, model_id: str, instruction: str, description: str) -> dict[str, Any]:
        return self.control.create_agent(
            agentName=name,
            foundationModel=model_id,
            agentResourceRoleArn=AppConfig.BEDROCK_AGENT_ROLE_ARN,
            instruction=instruction,
            description=description,
            idleSessionTTLInSeconds=AppConfig.BEDROCK_AGENT_IDLE_SESSION_TTL,
        )

    def update_agent(self, *, agent_id: str, name: str, model_id: str, instruction: str, description: str) -> dict[str, Any]:
        return self.control.update_agent(
            agentId=agent_id,
            agentName=name,
            foundationModel=model_id,
            agentResourceRoleArn=AppConfig.BEDROCK_AGENT_ROLE_ARN,
            instruction=instruction,
            description=description,
            idleSessionTTLInSeconds=AppConfig.BEDROCK_AGENT_IDLE_SESSION_TTL,
        )

    def prepare_agent(self, agent_id: str) -> dict[str, Any]:
        return self.control.prepare_agent(agentId=agent_id)

    def create_agent_alias(self, agent_id: str, alias_name: str) -> dict[str, Any]:
        return self.control.create_agent_alias(agentId=agent_id, agentAliasName=alias_name)

    def list_agent_aliases(self, agent_id: str) -> list[dict[str, Any]]:
        return self.control.list_agent_aliases(agentId=agent_id).get('agentAliasSummaries', [])

    def associate_knowledge_base(self, *, agent_id: str, kb_id: str, description: str, state: str = 'ENABLED') -> dict[str, Any]:
        return self.control.associate_agent_knowledge_base(
            agentId=agent_id,
            knowledgeBaseId=kb_id,
            description=description,
            knowledgeBaseState=state,
        )

    def associate_collaborator(
        self,
        *,
        supervisor_agent_id: str,
        collaborator_alias_arn: str,
        collaborator_name: str,
        relay_history: str = 'TO_COLLABORATOR',
        instruction: str = '',
    ) -> dict[str, Any]:
        return self.control.associate_agent_collaborator(
            agentId=supervisor_agent_id,
            agentDescriptor={'aliasArn': collaborator_alias_arn},
            collaboratorName=collaborator_name,
            collaborationInstruction=instruction,
            relayConversationHistory=relay_history,
        )

    def invoke_agent(
        self,
        *,
        agent_id: str,
        alias_id: str,
        session_id: str,
        text: str,
        session_state: dict[str, Any] | None = None,
        enable_trace: bool | None = None,
        source_arn: str | None = None,
    ) -> AgentInvocationResult:
        started = time.perf_counter()
        kwargs: dict[str, Any] = {
            'agentId': agent_id,
            'agentAliasId': alias_id,
            'sessionId': session_id,
            'inputText': text,
            'enableTrace': AppConfig.BEDROCK_ENABLE_TRACE if enable_trace is None else enable_trace,
        }
        if session_state:
            kwargs['sessionState'] = session_state
        if source_arn:
            kwargs['sourceArn'] = source_arn
        if AppConfig.BEDROCK_STREAM_FINAL_RESPONSE:
            kwargs['streamingConfigurations'] = {'streamFinalResponse': True}
        try:
            response = self.runtime.invoke_agent(**kwargs)
        except Exception as exc:
            raise BedrockInvocationError(str(exc)) from exc

        text_chunks: list[str] = []
        traces: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        raw_events: list[dict[str, Any]] = []

        for event in response.get('completion', []):
            raw_events.append(event)
            if 'chunk' in event:
                chunk = event['chunk']
                chunk_bytes = chunk.get('bytes') or b''
                if isinstance(chunk_bytes, (bytes, bytearray)):
                    text_chunks.append(chunk_bytes.decode('utf-8'))
                else:
                    text_chunks.append(str(chunk_bytes))
                attribution = chunk.get('attribution') or {}
                for citation in attribution.get('citations', []) or []:
                    citations.append(citation)
            if 'trace' in event:
                traces.append(event['trace'])
            if 'returnControl' in event:
                traces.append({'returnControl': event['returnControl']})

        latency_ms = int((time.perf_counter() - started) * 1000)
        return AgentInvocationResult(
            text=''.join(text_chunks).strip(),
            raw={'events': raw_events},
            traces=traces,
            citations=citations,
            latency_ms=latency_ms,
        )
