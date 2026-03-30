from __future__ import annotations

import json
import re
from typing import Any

from core.config import AppConfig
from apps.agents.bedrock import BedrockAgentPlatformClient
from apps.agents.prompting import PromptComposer
from apps.agents.schemas import AgentContext, AgentDecision
from apps.conversations.models import ConversationSession


class BedrockNativeSupervisorOrchestrator:
    def __init__(self, bedrock: BedrockAgentPlatformClient | None = None) -> None:
        self.bedrock = bedrock or BedrockAgentPlatformClient()

    def build_context(self, session: ConversationSession, latest_user_message: str) -> AgentContext:
        history = []
        for t in session.turns.order_by("sequence"):
            history.append(
                {
                    "role": t.role,
                    "content": t.content,
                    "output_payload": getattr(t, "output_payload", None),
                }
            )
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
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        if not text:
            return None
        candidates = [text.strip()]
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            candidates.append(fence_match.group(1).strip())
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start:end + 1].strip())
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
        return None

    @classmethod
    def _safe_json(cls, text: str) -> dict[str, Any]:
        parsed = cls._extract_json_object(text)
        if parsed is not None:
            return parsed
        return {
            "final_reply": "",
            "evaluation": {},
            "compliance": {"approved": None},
            "citations": [],
            "team_summary": [],
            "_raw_text": text,
        }

    @staticmethod
    def _classify_question(text: str) -> str:
        t = (text or "").lower().strip()
        hard_factual_terms = [
            "dosagem", "dose", "mg", "posologia", "bula", "indicacao", "indicação",
            "para que serve", "forma farmaceutica", "forma farmacêutica",
            "apresentacao", "apresentação", "mecanismo", "efeito", "efeitos",
            "composicao", "composição", "contraindicacao", "contraindicação",
            "base de conhecimento", "documento", "guideline", "estudo", "protocolo",
            "responsavel tecnico", "responsável técnico", "farmaceutico responsável", "farmacêutico responsável",
        ]
        if any(term in t for term in hard_factual_terms):
            return "factual_documental"
        training_terms = [
            "como conversar", "como abordar", "como explicar", "como apresentar",
            "como falar", "simule", "simular", "treinar", "treino", "explique", "resuma",
        ]
        if any(term in t for term in training_terms):
            return "treinamento_orientado"
        return "treinamento_orientado"

    @staticmethod
    def _normalize_entity(raw: str) -> str:
        text = (raw or "").strip(" ?.,;:\"'“”")
        text = re.sub(r"^(consulte?\s+na\s+(?:sua\s+)?base(?:\s+de\s+conhecimento(?:s)?)?\s+)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(consulta\s+na\s+(?:sua\s+)?base(?:\s+de\s+conhecimento(?:s)?)?\s+)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(para\s+que\s+serve\s+(?:o|a)?\s*)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(qual\s+a\s+posologia\s+)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(quem\s+e\s+o\s+responsavel\s+tecnico\s+pelo\s+)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(que\s+e\s+o\s+responsavel\s+tecnico\s+pelo\s+)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(o\s+que\s+diz\s+a\s+bula\s+do?\s*)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(remedio|remédio|medicamento)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" ?.,;:\"'“”")
        return text

    @classmethod
    def _extract_entity(cls, text: str) -> str:
        txt = (text or "").strip()
        product_match = re.search(r"(somalgin\s+cardio)", txt, flags=re.IGNORECASE)
        if product_match:
            return cls._normalize_entity(product_match.group(1))
        patterns = [
            r"(?:no documento de|na bula de|no artigo de|no estudo de|sobre)\s+(.+?)(?:,|\?|$)",
            r"(?:do|da|de)\s+(.+?)(?:,|\?|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, txt, flags=re.IGNORECASE)
            if m:
                return cls._normalize_entity(m.group(1))
        return cls._normalize_entity(txt)

    @staticmethod
    def _extract_attribute(text: str) -> str:
        txt = (text or "").lower()
        if any(term in txt for term in ["farmaceutico responsavel", "farmacêutico responsável", "responsavel tecnico", "responsável técnico", "dr. adriano pinheiro coelho"]):
            return "responsavel_tecnico"
        if any(term in txt for term in ["posologia", "dose", "dosagem", "mg"]):
            return "posologia"
        if any(term in txt for term in ["para que serve", "indicacao", "indicação", "uso indicado", "indicações terapêuticas"]):
            return "indicacao"
        if any(term in txt for term in ["forma farmacêutica", "forma farmaceutica", "apresentação", "apresentacao"]):
            return "forma_farmaceutica"
        return "assunto_principal"

    @staticmethod
    def _attribute_synonyms(attribute_key: str) -> list[str]:
        return {
            "responsavel_tecnico": ["responsavel tecnico", "responsável técnico", "farmaceutico responsavel", "farmacêutico responsável", "farm. resp", "dr. adriano pinheiro coelho"],
            "indicacao": ["indicacao", "indicação", "uso indicado", "para que serve", "indicações terapêuticas", "finalidade terapêutica"],
            "posologia": ["posologia", "dose", "dosagem", "regime posologico", "quantos mg"],
            "forma_farmaceutica": ["forma farmacêutica", "forma farmaceutica", "apresentação", "apresentacao"],
            "assunto_principal": ["resumo", "tema principal", "assunto"],
        }.get(attribute_key, [attribute_key])

    @classmethod
    def _build_retrieval_hints(cls, latest_user_message: str) -> dict[str, Any]:
        question_type = cls._classify_question(latest_user_message)
        entity = cls._extract_entity(latest_user_message)
        attribute_key = cls._extract_attribute(latest_user_message)
        synonyms = cls._attribute_synonyms(attribute_key)
        section_hints = {
            "indicacao": ["indicacoes", "indicacoes terapeuticas", "para que serve"],
            "posologia": ["posologia", "como usar", "dose recomendada"],
            "forma_farmaceutica": ["forma farmaceutica", "apresentacao"],
            "responsavel_tecnico": ["responsavel tecnico", "farmaceutico responsavel", "farm. resp"],
        }.get(attribute_key, [])

        queries = []
        if latest_user_message:
            queries.append(latest_user_message.strip())
        if entity:
            queries.extend([entity, f'"{entity}"'])
        for syn in synonyms:
            if entity:
                queries.extend([
                    f"{entity} {syn}",
                    f'"{entity}" {syn}',
                    f"{entity} bula {syn}",
                    f"{entity} documento {syn}",
                ])
        for section in section_hints:
            if entity:
                queries.extend([f"{entity} {section}", f'"{entity}" {section}', f"{entity} bula {section}"])

        deduped, seen = [], set()
        for q in queries:
            key = q.strip().lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(q.strip())

        return {
            "question_type": question_type,
            "entity": entity,
            "attribute_key": attribute_key,
            "attribute_synonyms": synonyms,
            "section_hints": section_hints,
            "retrieval_queries": deduped[:16],
        }

    @staticmethod
    def _flatten_any(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            return " ".join(BedrockNativeSupervisorOrchestrator._flatten_any(v) for v in value.values())
        if isinstance(value, list):
            return " ".join(BedrockNativeSupervisorOrchestrator._flatten_any(v) for v in value)
        return str(value)

    @classmethod
    def _summarize_traces(cls, traces: list[dict[str, Any]] | None) -> dict[str, Any]:
        flat = cls._flatten_any(traces or [])
        lower = flat.lower()
        consultation_seen = any(token in lower for token in [
            "consultation", "consulta", "mlp8gvtsyx", "consulta-kb-v4", "gtp5hlthjf"
        ])
        retrieval_seen = any(token in lower for token in [
            "retrieval", "retrieved", "retrieve", "knowledgebase", "knowledge base",
            "vector", "chunk", "citation", "citations", "source", "s3://", "somalgin_cardio",
            "x-amz-bedrock-kb-chunk-id", "indicações terapêuticas", "posologia", "dr. adriano pinheiro coelho"
        ])
        failure_seen = any(token in lower for token in [
            "not available", "resource not found", "access denied", "validationexception",
            "exception", "failure", "erro", "error"
        ])
        return {
            "consultation_seen": consultation_seen,
            "retrieval_seen": retrieval_seen,
            "failure_seen": failure_seen,
            "raw_excerpt": flat[:1500],
        }

    @staticmethod
    def _looks_like_human_answer(text: str) -> bool:
        if not text:
            return False
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return False
        if "nao consegui confirmar esse dado especifico" in stripped.lower():
            return False
        return len(stripped) > 20

    @staticmethod
    def _normalize_compliance_payload(
        compliance: dict[str, Any],
        retrieval_hints: dict[str, Any],
        citations: list[dict[str, Any]],
        raw_text: str,
        trace_summary: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(compliance or {})
        normalized.setdefault("approved", None)

        if retrieval_hints["question_type"] != "factual_documental":
            normalized.setdefault("evidence_status", "not_required")
            normalized.setdefault("confidence", "training")
            return normalized

        tool_unavailable = "tool 'consultation' is not available" in (raw_text or "").lower()
        supported_by_trace = bool(trace_summary.get("consultation_seen") and trace_summary.get("retrieval_seen") and not trace_summary.get("failure_seen"))

        if citations:
            normalized["evidence_status"] = "supported"
            normalized.setdefault("confidence", "high")
        elif supported_by_trace:
            normalized["evidence_status"] = "supported_by_trace"
            normalized.setdefault("confidence", "medium")
        elif tool_unavailable:
            normalized["evidence_status"] = "unsupported"
            normalized.setdefault("confidence", "blocked_by_tooling")
        else:
            normalized.setdefault("evidence_status", "uncertain")
            normalized.setdefault("confidence", "low")
        return normalized

    def _resolve_team_binding(self, session: ConversationSession) -> dict[str, Any]:
        team = (session.session_state or {}).get("bedrock_team")
        if team:
            return team
        manifest = AppConfig.load_manifest().get("blueprints", {})
        fallback = manifest.get(session.blueprint.slug) or manifest.get("default") or {}
        if fallback:
            session_state = dict(session.session_state or {})
            session_state["bedrock_team"] = fallback
            session.session_state = session_state
            try:
                session.save(update_fields=["session_state", "updated_at"])
            except Exception:
                pass
        return fallback

    def _build_training_fallback(self, context: AgentContext) -> str:
        specialty = context.prompt_bundle.get("specialty", {}).get("title") or "a especialidade"
        return (
            f"Para abordar um médico em {specialty}, faça uma abertura objetiva, contextualize o problema clínico, "
            "conecte o tema ao benefício prático e feche com uma pergunta que convide objeções ou critérios de uso."
        )

    def _build_contextual_followup(self, context: AgentContext) -> str:
        return self._build_training_fallback(context)

    def _build_structured_timeline(
        self,
        retrieval_hints: dict[str, Any],
        compliance: dict[str, Any],
        final_reply: str,
        citations: list[dict[str, Any]],
        parsed: dict[str, Any],
        prompt_header: str,
        trace_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        qtype = retrieval_hints["question_type"]
        items = [
            {
                "agent": "supervisor",
                "title": "Classificação do turno",
                "message": "Pergunta classificada como factual/documental." if qtype == "factual_documental" else "Pergunta classificada como treinamento orientado.",
                "status": "done",
                "input_payload": {"question_type": qtype, "retrieval_hints": retrieval_hints},
                "output_payload": {"decision": qtype},
            }
        ]

        if qtype == "factual_documental":
            items.append(
                {
                    "agent": "consultation",
                    "title": "Consulta factual executada",
                    "message": "O supervisor exigiu consulta à base por entidade, sinônimos e seções prováveis.",
                    "status": "done",
                    "input_payload": {
                        "entity": retrieval_hints.get("entity"),
                        "queries": retrieval_hints.get("retrieval_queries"),
                        "section_hints": retrieval_hints.get("section_hints"),
                    },
                    "output_payload": {
                        "citations_count": len(citations),
                        "trace_summary": trace_summary,
                    },
                }
            )
            items.append(
                {
                    "agent": "consultation",
                    "title": "Resultado da evidência",
                    "message": (
                        "O backend recebeu evidência factual suficiente para confirmar o dado solicitado."
                        if compliance.get("evidence_status") in {"supported", "supported_by_trace"}
                        else "Não houve suporte factual suficiente para confirmar o dado solicitado neste turno."
                    ),
                    "status": "done" if compliance.get("evidence_status") in {"supported", "supported_by_trace"} else "error",
                    "input_payload": {"evidence_threshold": "supported"},
                    "output_payload": {"citations": citations, "trace_summary": trace_summary},
                }
            )

        estatus = compliance.get("evidence_status") or "uncertain"
        items.append(
            {
                "agent": "compliance",
                "title": "Parecer de compliance",
                "message": {
                    "supported": "O parecer de compliance confirmou que havia suporte factual suficiente para a resposta.",
                    "supported_by_trace": "O parecer de compliance aceitou a evidência observada nos traces do colaborador de consulta.",
                    "unsupported": "O parecer de compliance rejeitou a confirmação factual por falta de evidência suficiente.",
                    "uncertain": "O parecer de compliance indicou evidência insuficiente para confirmar o dado com segurança.",
                    "not_required": "O parecer de compliance indicou que evidência factual estrita não era obrigatória neste turno de treinamento.",
                }.get(estatus, "O parecer de compliance foi processado para este turno."),
                "status": "done" if estatus in {"supported", "supported_by_trace", "not_required"} else "error",
                "input_payload": {"citations_count": len(citations), "question_type": qtype},
                "output_payload": compliance,
            }
        )

        items.append(
            {
                "agent": "supervisor",
                "title": "Resposta final entregue",
                "message": final_reply[:180] + ("…" if len(final_reply) > 180 else ""),
                "status": "done",
                "input_payload": {"prompt_header": prompt_header},
                "output_payload": {"parsed": parsed, "final_reply": final_reply},
            }
        )
        return items

    def process_turn(self, session: ConversationSession, latest_user_message: str) -> dict[str, Any]:
        context = self.build_context(session, latest_user_message)
        team = self._resolve_team_binding(session)
        supervisor = team.get("supervisor") or {}
        if not supervisor.get("agent_id") or not supervisor.get("alias_id"):
            raise RuntimeError(
                f"Supervisor Bedrock nao configurado para o blueprint '{context.blueprint_slug}'. Binding resolvido: {team}"
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
            "- Para perguntas factuais/documentais, acione consultation e responda com o dado factual quando houver evidência suficiente.\n"
            "- Se a pergunta for factual e a consulta trouxer suporte, nao substitua o resultado por fallback de treinamento.\n"
            "- Para perguntas de treinamento, resposta didatica e util.\n\n"
            "ULTIMA MENSAGEM DO USUARIO\n"
            f"{latest_user_message}\n\n"
            "HISTORICO RECENTE\n"
            f"{PromptComposer._pretty(context.conversation_history[-12:])}\n\n"
            "PLANO DE RECUPERACAO\n"
            f"{PromptComposer._pretty(retrieval_hints)}\n\n"
            "INSTRUCOES DE SAIDA\n"
            "- Devolva JSON quando possivel no contrato esperado.\n"
            "- Se nao devolver JSON, ao menos devolva uma resposta final direta e factual quando houver suporte.\n"
            "- Nao invente fatos.\n"
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
        raw_text = parsed.get("_raw_text") or invoked.text or ""
        trace_summary = self._summarize_traces(invoked.traces)
        compliance = self._normalize_compliance_payload(
            parsed.get("compliance") or {},
            retrieval_hints,
            invoked.citations,
            raw_text,
            trace_summary,
        )

        final_reply = parsed.get("final_reply") or ""
        if not isinstance(final_reply, str):
            final_reply = str(final_reply)

        if not final_reply.strip() and self._looks_like_human_answer(raw_text):
            final_reply = raw_text.strip()

        lower = (final_reply or "").lower()
        tool_unavailable = any(
            msg in lower for msg in [
                "tool 'consultation' is not available",
                "a ferramenta de consulta nao esta disponivel",
                "a ferramenta de consulta não está disponível",
            ]
        )

        if retrieval_hints["question_type"] == "factual_documental":
            if compliance.get("evidence_status") in {"supported", "supported_by_trace"}:
                if not final_reply.strip() and self._looks_like_human_answer(raw_text):
                    final_reply = raw_text.strip()
                if not final_reply.strip():
                    final_reply = (
                        "A consulta factual foi executada com suporte na base, mas a resposta final não veio estruturada. "
                        "Refaça a pergunta para eu tentar novamente com o mesmo conteúdo recuperado."
                    )
            else:
                final_reply = (
                    "Nao consegui confirmar esse dado especifico com evidencia suficiente da base neste turno. "
                    "Posso seguir te ajudando de forma segura explicando o contexto clinico do tema, como apresentar esse assunto ao medico e como formular a pergunta certa para buscar esse campo documental sem assumir um fato nao confirmado."
                )
        elif tool_unavailable or '"final_reply"' in final_reply or final_reply.strip().startswith("{"):
            final_reply = self._build_training_fallback(context)
        elif not final_reply.strip():
            final_reply = self._build_contextual_followup(context)

        timeline = self._build_structured_timeline(
            retrieval_hints=retrieval_hints,
            compliance=compliance,
            final_reply=final_reply,
            citations=invoked.citations,
            parsed=parsed,
            prompt_header=prompt_header,
            trace_summary=trace_summary,
        )

        factual_guard = {
            "entity": retrieval_hints.get("entity"),
            "attribute_key": retrieval_hints.get("attribute_key"),
            "question_type": retrieval_hints.get("question_type"),
            "evidence_status": compliance.get("evidence_status"),
            "citations_count": len(invoked.citations),
            "trace_summary": trace_summary,
        }

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
                    "trace_summary": trace_summary,
                },
                telemetry={"latency_ms": invoked.latency_ms, "status": "completed"},
            ),
            "final_reply": final_reply,
            "evaluation": parsed.get("evaluation") or {},
            "compliance": compliance,
            "citations": invoked.citations,
            "traces": invoked.traces,
            "team_summary": parsed.get("team_summary") or [],
            "timeline": timeline,
            "factual_guard": factual_guard,
        }
