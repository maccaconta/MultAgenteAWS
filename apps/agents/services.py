from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from core.config import AppConfig
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
            r"forma\s+farmac[eê]utica",
            r"apresenta[cç][aã]o",
            r"para\s+que\s+serve",
        ]
        training_patterns = [
            r"como\s+conversar",
            r"como\s+abordar",
            r"como\s+explicar",
            r"como\s+apresentar",
            r"como\s+falar",
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
            ("indicacao", ["indicacao", "indicação", "para que serve"]),
            ("reacao_adversa", ["reacao adversa", "reação adversa", "evento adverso"]),
            ("forma_farmaceutica", ["forma farmacêutica", "forma farmaceutica", "apresentação", "apresentacao"]),
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
            "indicacao": ["indicacao", "indicação", "uso indicado", "para que serve"],
            "reacao_adversa": ["reacao adversa", "reação adversa", "evento adverso"],
            "forma_farmaceutica": ["forma farmacêutica", "forma farmaceutica", "apresentação", "apresentacao"],
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

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _manifest_team_for(self, session: ConversationSession) -> dict[str, Any]:
        manifest = AppConfig.load_manifest().get("blueprints", {})
        return manifest.get(session.blueprint.slug) or manifest.get("default") or {}

    def _resolve_team_binding(self, session: ConversationSession) -> dict[str, Any]:
        team = (session.session_state or {}).get("bedrock_team")
        if team:
            return team
        return self._manifest_team_for(session)

    @staticmethod
    def _normalize_compliance_payload(
        compliance: dict[str, Any],
        retrieval_hints: dict[str, Any],
        citations: list[dict[str, Any]],
        raw_text: str,
    ) -> dict[str, Any]:
        normalized = dict(compliance or {})
        normalized.setdefault("approved", None)

        if retrieval_hints["question_type"] != "factual_documental":
            normalized.setdefault("evidence_status", "not_required")
            normalized.setdefault("confidence", "training")
            return normalized

        raw_lower = (raw_text or "").lower()
        tool_unavailable = "tool 'consultation' is not available" in raw_lower or "ferramenta de consulta" in raw_lower
        if citations:
            normalized["evidence_status"] = "supported"
            normalized.setdefault("confidence", "high")
        elif tool_unavailable:
            normalized["evidence_status"] = "unsupported"
            normalized.setdefault("confidence", "blocked_by_tooling")
        else:
            normalized.setdefault("evidence_status", "unknown")
            normalized.setdefault("confidence", "undetermined")
        return normalized

    @staticmethod
    def _collect_trace_text(node: Any) -> list[str]:
        texts: list[str] = []
        if isinstance(node, dict):
            for key, value in node.items():
                texts.append(str(key))
                texts.extend(BedrockNativeSupervisorOrchestrator._collect_trace_text(value))
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                texts.extend(BedrockNativeSupervisorOrchestrator._collect_trace_text(item))
        elif node is not None:
            texts.append(str(node))
        return texts

    def _detect_agent_from_trace(self, text: str, team: dict[str, Any]) -> str | None:
        collaborators = (team.get("collaborators") or {}) if isinstance(team, dict) else {}

        patterns = {
            "consultation": ["consultation", "consulta", "consult"],
            "synthesis": ["synthesis", "sintese", "síntese", "synthesize"],
            "compliance": ["compliance"],
            "evaluation": ["evaluation", "avaliacao", "avaliação"],
            "supervisor": ["supervisor"],
        }

        for agent, tokens in patterns.items():
            collaborator = collaborators.get(agent) or {}
            ids = [
                str(collaborator.get("agent_id") or "").lower(),
                str(collaborator.get("alias_id") or "").lower(),
            ]
            searchable = [token.lower() for token in tokens] + [value for value in ids if value]
            if any(token and token in text for token in searchable):
                return agent
        return None

    def _trace_event_from_entry(self, entry: Any, team: dict[str, Any]) -> dict[str, Any] | None:
        text = " ".join(self._collect_trace_text(entry)).strip()
        if not text:
            return None

        text_lower = " ".join(text.lower().split())
        agent = self._detect_agent_from_trace(text_lower, team)
        if not agent:
            return None

        if any(token in text_lower for token in ("returncontrol", "collaborator", "delegate", "handoff", "invoke")):
            title = "Agente acionado"
            message = "O trace do Bedrock registrou o acionamento desta etapa dentro do pipeline."
        elif any(token in text_lower for token in ("retriev", "search", "knowledge", "citation", "chunk")):
            title = "Busca ou evidência registrada"
            message = "O trace do Bedrock registrou busca, recuperação ou uso de evidência nesta etapa."
        elif any(token in text_lower for token in ("output", "response", "result", "observation")):
            title = "Resultado da etapa registrado"
            message = "O trace do Bedrock registrou a saída ou observação desta etapa."
        else:
            title = "Etapa confirmada"
            message = "O trace do Bedrock confirmou a execução desta etapa no pipeline."

        return {
            "agent": agent,
            "title": title,
            "message": message,
            "status": "done",
            "timestamp": self._iso_now(),
        }

    def _trace_timeline(self, traces: list[dict[str, Any]], team: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for entry in traces or []:
            event = self._trace_event_from_entry(entry, team)
            if not event:
                continue
            fingerprint = (event["agent"], event["title"])
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            events.append(event)

        return events[:6]

    def _build_timeline(
        self,
        retrieval_hints: dict[str, Any],
        compliance: dict[str, Any],
        final_reply: str,
        traces: list[dict[str, Any]],
        team: dict[str, Any],
        citations: list[dict[str, Any]],
        evaluation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        question_type = retrieval_hints["question_type"]
        timeline = [
            {
                "agent": "supervisor",
                "title": "Classificação do turno",
                "message": (
                    "Pergunta classificada como factual/documental."
                    if question_type == "factual_documental"
                    else "Pergunta classificada como treinamento orientado."
                ),
                "status": "done",
                "timestamp": self._iso_now(),
            }
        ]

        trace_events = self._trace_timeline(traces, team)
        timeline.extend(trace_events)

        if question_type == "factual_documental":
            evidence_status = compliance.get("evidence_status") or ("supported" if citations else "unknown")
            if evidence_status == "supported":
                timeline.append(
                    {
                        "agent": "consultation",
                        "title": "Evidência factual confirmada",
                        "message": "O backend recebeu evidências suficientes para sustentar a resposta factual deste turno.",
                        "status": "done",
                        "timestamp": self._iso_now(),
                    }
                )
            else:
                timeline.append(
                    {
                        "agent": "consultation",
                        "title": "Evidência factual insuficiente",
                        "message": "Nao houve suporte factual suficiente para confirmar o dado solicitado neste turno.",
                        "status": "error",
                        "timestamp": self._iso_now(),
                    }
                )
        else:
            timeline.append(
                {
                    "agent": "synthesis",
                    "title": "Resposta de treinamento consolidada",
                    "message": "O turno seguiu o fluxo didático principal, voltado a treinamento e abordagem.",
                    "status": "done",
                    "timestamp": self._iso_now(),
                }
            )

        if compliance:
            evidence_status = compliance.get("evidence_status", "unknown")
            evidence_message = {
                "supported": "O parecer de compliance confirmou suporte factual suficiente para a saída.",
                "unsupported": "O parecer de compliance bloqueou a confirmação factual por falta de evidência suficiente.",
                "not_required": "O parecer de compliance indicou que evidência factual estrita não era obrigatória neste turno.",
                "unknown": "O parecer de compliance permaneceu inconclusivo quanto à evidência factual.",
            }.get(evidence_status, "O parecer de compliance foi processado.")
            timeline.append(
                {
                    "agent": "compliance",
                    "title": "Parecer de compliance",
                    "message": evidence_message,
                    "status": "done" if evidence_status != "unsupported" else "error",
                    "timestamp": self._iso_now(),
                }
            )

        if evaluation:
            timeline.append(
                {
                    "agent": "evaluation",
                    "title": "Avaliação incremental atualizada",
                    "message": "Score global e dimensões da conversa foram atualizados para o turno.",
                    "status": "done",
                    "timestamp": self._iso_now(),
                }
            )

        return timeline

    def _build_training_fallback(self, context: AgentContext, latest_user_message: str) -> str:
        specialty = context.prompt_bundle.get("specialty", {}).get("title") or "a especialidade"
        persona = context.prompt_bundle.get("persona", {}).get("title") or "o médico"
        scenario = context.prompt_bundle.get("scenario", {}).get("title") or "o contexto clínico atual"
        return (
            f"Para falar com um médico de {specialty}, comece reconhecendo a rotina clínica e conecte sua abordagem ao cenário '{scenario}'. "
            f"Com a persona '{persona}', priorize uma abertura objetiva, com linguagem técnica adequada, relevância clínica e uma pergunta que convide o médico a expor como ele maneja o tema na prática.\n\n"
            "Estruture a conversa em quatro movimentos: 1) contextualize o problema clínico e o perfil do paciente; "
            "2) conecte o tema ao impacto prático na tomada de decisão; 3) apresente o medicamento ou conceito com benefício claro, sem exagero promocional; "
            "4) feche com uma pergunta específica que leve o médico a comentar objeções, critérios de uso ou experiência clínica.\n\n"
            "Exemplo de abertura: 'Doutor, na sua rotina, quando o paciente chega com sinais de suspeita diagnóstica ou dificuldade de controle, quais critérios mais pesam na sua decisão terapêutica?'. "
            "A partir daí, desenvolva a conversa com foco em valor clínico, segurança e adequação ao perfil do paciente."
        )

    def process_turn(self, session: ConversationSession, latest_user_message: str) -> dict[str, Any]:
        context = self.build_context(session, latest_user_message)
        team = self._resolve_team_binding(session)
        supervisor = team.get("supervisor") or {}
        if not supervisor.get("agent_id") or not supervisor.get("alias_id"):
            raise RuntimeError(
                f"Supervisor Bedrock nao configurado para o blueprint '{context.blueprint_slug}'."
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
            "- Para perguntas de treinamento, nao devolva apenas uma pergunta de follow-up; entregue orientacao pratica completa no mesmo turno.\n"
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
        compliance = self._normalize_compliance_payload(
            parsed.get("compliance") or {},
            retrieval_hints,
            invoked.citations,
            invoked.text,
        )
        team_summary = parsed.get("team_summary") or []

        if isinstance(final_reply, str):
            lower = final_reply.lower()
            tool_unavailable = (
                "tool 'consultation' is not available" in lower
                or "a ferramenta de consulta nao esta disponivel" in lower
                or "a ferramenta de consulta não está disponível" in lower
            )

            if retrieval_hints["question_type"] == "factual_documental" and compliance.get("evidence_status") != "supported":
                final_reply = (
                    "Nao consegui confirmar esse dado especifico com evidencia suficiente da base neste turno. "
                    "Posso seguir te ajudando de forma segura explicando o contexto clinico do tema, como apresentar esse assunto ao medico "
                    "e como formular a pergunta certa para buscar esse campo documental sem assumir um fato nao confirmado."
                )
            elif retrieval_hints["question_type"] != "factual_documental" and tool_unavailable:
                final_reply = self._build_training_fallback(context, latest_user_message)
            elif retrieval_hints["question_type"] != "factual_documental" and "quer que eu explique" in lower:
                final_reply = self._build_training_fallback(context, latest_user_message)

        timeline = self._build_timeline(
            retrieval_hints=retrieval_hints,
            compliance=compliance,
            final_reply=final_reply,
            traces=invoked.traces,
            team=team,
            citations=invoked.citations,
            evaluation=evaluation,
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
            "timeline": timeline,
        }
