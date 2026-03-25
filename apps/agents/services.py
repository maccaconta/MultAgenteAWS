from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.bedrock import BedrockAgentPlatformClient
from apps.agents.prompting import PromptComposer
from apps.agents.schemas import AgentContext, AgentDecision
from apps.conversations.models import ConversationSession


class BedrockNativeSupervisorOrchestrator:
    """Executa a simulacao via Amazon Bedrock Agents."""

    def __init__(self, bedrock: BedrockAgentPlatformClient | None = None) -> None:
        self.bedrock = bedrock or BedrockAgentPlatformClient()

    def build_context(self, session: ConversationSession, latest_user_message: str) -> AgentContext:
        history = [{"role": t.role, "content": t.content} for t in session.turns.order_by("sequence")]
        bundle = {
            "blueprint": {
                "slug": session.blueprint.slug,
                "title": session.blueprint.title,
                "description": session.blueprint.description,
            },
            "persona": session.persona.as_prompt_payload(),
            "scenario": session.scenario.as_prompt_payload(),
            "specialty": session.specialty.as_prompt_payload(),
            "policy": session.policy.as_prompt_payload(),
            "instruction": session.instruction.as_prompt_payload(),
            "output_contract": session.output_contract.as_prompt_payload(),
            "evaluation_rubric": (
                session.evaluation_rubric.as_prompt_payload()
                if session.evaluation_rubric
                else None
            ),
        }
        return AgentContext(
            session_id=session.pk,
            user_id=session.user_id,
            blueprint_slug=session.blueprint.slug,
            prompt_bundle=bundle,
            conversation_history=history,
            latest_user_message=latest_user_message,
            team_binding=(session.session_state or {}).get("bedrock_team", {}),
        )

    @staticmethod
    def _safe_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {
                "final_reply": text,
                "evaluation": {},
                "compliance": {"approved": None},
                "citations": [],
                "team_summary": [],
            }

    @staticmethod
    def _classify_question(text: str) -> str:
        t = (text or "").lower()
        factual_patterns = [
            r"quem\s+e",
            r"qual\s+e",
            r"qual\s+o",
            r"qual\s+a",
            r"medico\s+responsavel",
            r"responsavel\s+tecnico",
            r"farmaceutico\s+responsavel",
            r"farmac[eê]utico\s+respons[áa]vel",
            r"autor",
            r"data",
            r"secao",
            r"seção",
            r"pagina",
            r"página",
            r"documento",
            r"bula",
            r"artigo",
            r"paper",
            r"estudo",
            r"guideline",
            r"protocolo",
            r"relatorio",
            r"laudo",
            r"posologia",
            r"indicacao",
            r"indicação",
            r"reacao\s+adversa",
            r"evento\s+adverso",
        ]
        training_patterns = [
            r"como\s+conversar",
            r"como\s+abordar",
            r"como\s+explicar",
            r"como\s+apresentar",
            r"objecao",
            r"objeção",
            r"simule",
            r"simular",
            r"treinar",
            r"treino",
            r"especialidade",
            r"o\s+que\s+e",
            r"o\s+que\s+é",
            r"explique",
            r"resuma",
            r"diferen[cç]a",
        ]
        if any(re.search(p, t) for p in factual_patterns):
            return "factual_documental"
        if any(re.search(p, t) for p in training_patterns):
            return "treinamento_orientado"
        return "treinamento_orientado"

    @staticmethod
    def _extract_entity(text: str) -> str:
        txt = (text or "").strip()
        patterns = [
            r"(?:no documento de|na bula de|no artigo de|no estudo de|sobre)\s+(.+?)(?:,|\?|$)",
            r"(?:do|da|de)\s+(.+?)(?:,|\?|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, txt, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip(" ?.,;:")
        return txt.strip(" ?.,;:")

    @staticmethod
    def _extract_attribute(text: str) -> str:
        txt = (text or "").lower()
        mapping = [
            ("farmaceutico_responsavel", ["farmaceutico responsavel", "farmacêutico responsável", "responsavel tecnico", "responsável técnico", "rt"]),
            ("medico_responsavel", ["medico responsavel", "médico responsável"]),
            ("autor", ["autor", "autora"]),
            ("data", ["data", "publicacao", "publicação"]),
            ("posologia", ["posologia", "dose"]),
            ("indicacao", ["indicacao", "indicação"]),
            ("reacao_adversa", ["reacao adversa", "reação adversa", "evento adverso"]),
            ("secao", ["secao", "seção", "capitulo", "capítulo"]),
        ]
        for canonical, options in mapping:
            if any(opt in txt for opt in options):
                return canonical
        return "assunto_principal"

    @staticmethod
    def _attribute_synonyms(attribute_key: str) -> list[str]:
        synonyms = {
            "farmaceutico_responsavel": [
                "farmaceutico responsavel",
                "farmacêutico responsável",
                "responsavel tecnico",
                "responsável técnico",
                "rt",
                "nome do responsavel tecnico",
                "nome do farmaceutico responsavel",
            ],
            "medico_responsavel": ["medico responsavel", "médico responsável", "nome do medico responsavel"],
            "autor": ["autor", "autora", "autores"],
            "data": ["data", "publicacao", "publicação"],
            "posologia": ["posologia", "dose", "regime posologico"],
            "indicacao": ["indicacao", "indicação", "uso indicado"],
            "reacao_adversa": ["reacao adversa", "reação adversa", "evento adverso"],
            "secao": ["secao", "seção", "capitulo", "capítulo"],
            "assunto_principal": ["resumo", "tema principal", "assunto"],
        }
        return synonyms.get(attribute_key, [attribute_key])

    @classmethod
    def _build_retrieval_hints(cls, latest_user_message: str) -> dict[str, Any]:
        question_type = cls._classify_question(latest_user_message)
        entity = cls._extract_entity(latest_user_message)
        attribute_key = cls._extract_attribute(latest_user_message)
        synonyms = cls._attribute_synonyms(attribute_key)

        queries: list[str] = []
        if latest_user_message:
            queries.append(latest_user_message.strip())
        for syn in synonyms:
            if entity:
                queries.append(f"{entity} {syn}")
                queries.append(f"{entity} documento {syn}")
                queries.append(f"{entity} bula {syn}")
                queries.append(f"{entity} artigo {syn}")
                queries.append(f"{entity} estudo {syn}")
                queries.append(f"{entity} guideline {syn}")
            else:
                queries.append(syn)

        deduped = []
        seen = set()
        for q in queries:
            q_norm = q.strip().lower()
            if q_norm and q_norm not in seen:
                seen.add(q_norm)
                deduped.append(q.strip())

        return {
            "question_type": question_type,
            "entity": entity,
            "attribute_key": attribute_key,
            "attribute_synonyms": synonyms,
            "retrieval_queries": deduped[:10],
        }

    def _resolve_team_binding(self, session: ConversationSession) -> dict[str, Any]:
        team = (session.session_state or {}).get("bedrock_team")
        if team:
            return team
        return {}

    def process_turn(self, session: ConversationSession, latest_user_message: str) -> dict[str, Any]:
        context = self.build_context(session, latest_user_message)
        team = self._resolve_team_binding(session)
        supervisor = team.get("supervisor") or {}
        if not supervisor.get("agent_id") or not supervisor.get("alias_id"):
            raise RuntimeError(
                f"Supervisor Bedrock nao configurado para o blueprint '{context.blueprint_slug}'. "
                f"Binding resolvido: {team}"
            )

        retrieval_hints = self._build_retrieval_hints(latest_user_message)

        session_state = {
            "sessionAttributes": PromptComposer.build_session_attributes(
                session_id=context.session_id,
                blueprint_slug=context.blueprint_slug,
                user_id=context.user_id,
            ),
            "promptSessionAttributes": {
                **PromptComposer.build_prompt_session_attributes(context.prompt_bundle),
                "question_type": retrieval_hints["question_type"],
                "entity": retrieval_hints["entity"],
                "attribute_key": retrieval_hints["attribute_key"],
                "kb_priority": "required" if retrieval_hints["question_type"] == "factual_documental" else "supporting",
            },
        }

        prompt_header = (
            "CONTEXTO OPERACIONAL DA SESSAO\n"
            "- Objetivo principal: treinar propagandistas em assuntos medicos, especialidades, cenarios, medicamentos e abordagem com medicos.\n"
            "- Use a base de conhecimento como apoio factual, mas nao bloqueie a conversa de treinamento quando uma recuperacao especifica falhar.\n"
            "- Para perguntas factuais/documentais, use consultation com retrieval iterativo por entidade, atributo e sinonimos.\n"
            "- Para perguntas de treinamento, explicacao, abordagem ou simulacao, priorize resposta didatica e util ao usuario.\n"
            "- Nunca responda apenas que a ferramenta de consulta nao esta disponivel.\n\n"
            "ULTIMA MENSAGEM DO USUARIO\n"
            f"{latest_user_message}\n\n"
            "HISTORICO RECENTE\n"
            f"{PromptComposer._pretty(context.conversation_history[-12:])}\n\n"
            "BUNDLE ESTRUTURADO DA SESSAO\n"
            f"{PromptComposer._pretty(context.prompt_bundle)}\n\n"
            "PLANO DE RECUPERACAO\n"
            f"{PromptComposer._pretty(retrieval_hints)}\n\n"
            "INSTRUCOES DE SAIDA\n"
            "- Devolva JSON no contrato esperado pelo supervisor.\n"
            "- Se a pergunta for factual e houver resposta na base, coloque o fato primeiro.\n"
            "- Se a base nao trouxer o campo, explique a limitacao factual, mas continue ajudando o usuario no objetivo de treinamento.\n"
            "- Sempre finalize com proximo passo util.\n"
        )

        invoked = self.bedrock.invoke_agent(
            agent_id=supervisor["agent_id"],
            alias_id=supervisor["alias_id"],
            session_id=f"django-session-{session.pk}",
            text=prompt_header,
            session_state=session_state,
            enable_trace=True,
        )

        parsed = self._safe_json(invoked.text)
        final_reply = parsed.get("final_reply") or invoked.text
        evaluation = parsed.get("evaluation") or {}
        compliance = parsed.get("compliance") or {}
        team_summary = parsed.get("team_summary") or []

        if isinstance(final_reply, str):
            lower = final_reply.lower()
            if "a ferramenta de consulta nao esta disponivel" in lower or "a ferramenta de consulta não está disponível" in lower:
                if retrieval_hints["question_type"] == "factual_documental":
                    final_reply = (
                        "Nao consegui confirmar esse campo especifico na base neste turno. "
                        "Posso continuar te ajudando de duas formas: explicar o contexto clinico e documental relacionado ao tema, "
                        "ou estruturar com voce como perguntar e discutir esse ponto em uma conversa com o medico."
                    )
                else:
                    final_reply = (
                        "Posso te ajudar no objetivo principal do treinamento mesmo sem depender dessa consulta factual agora. "
                        "Quer que eu explique o tema de forma didatica, simule a fala de um medico, ou monte uma abordagem para o propagandista?"
                    )

        return {
            "supervisor": AgentDecision(
                role="bedrock_supervisor",
                message=invoked.text,
                payload={
                    "parsed": parsed,
                    "citations": invoked.citations,
                    "traces": invoked.traces,
                    "raw": invoked.raw,
                    "team_binding": team,
                    "retrieval_hints": retrieval_hints,
                },
                telemetry={"latency_ms": invoked.latency_ms, "status": "completed"},
            ),
            "final_reply": final_reply,
            "evaluation": evaluation,
            "compliance": compliance,
            "citations": invoked.citations,
            "traces": invoked.traces,
            "team_summary": team_summary,
        }
