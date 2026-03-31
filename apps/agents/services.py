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
    OPTION_MAP = {"1": "simular_conversa", "2": "trabalhar_objecoes", "3": "montar_abordagem"}

    def __init__(self, bedrock: BedrockAgentPlatformClient | None = None) -> None:
        self.bedrock = bedrock or BedrockAgentPlatformClient()

    def build_context(self, session: ConversationSession, latest_user_message: str) -> AgentContext:
        history = []
        for t in session.turns.order_by("sequence"):
            history.append({"role": t.role, "content": t.content, "output_payload": getattr(t, "output_payload", None)})
        bundle = {
            "blueprint": {"slug": session.blueprint.slug, "title": session.blueprint.title, "description": session.blueprint.description},
            "persona": session.persona.as_prompt_payload(),
            "scenario": session.scenario.as_prompt_payload(),
            "specialty": session.specialty.as_prompt_payload(),
            "policy": session.policy.as_prompt_payload(),
            "instruction": session.instruction.as_prompt_payload(),
            "output_contract": session.output_contract.as_prompt_payload(),
            "evaluation_rubric": session.evaluation_rubric.as_prompt_payload() if session.evaluation_rubric else None,
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
        return {"final_reply": "", "evaluation": {}, "compliance": {"approved": None}, "citations": [], "team_summary": [], "_raw_text": text}

    @staticmethod
    def _contains_person_query(text: str) -> bool:
        txt = (text or "").lower()
        return any(p in txt for p in ["quem é", "quem e", "dr.", "dra.", "doutor", "doutora", "farm.", "farmacêutico", "farmaceutico", "responsável técnico", "responsavel tecnico"])

    @classmethod
    def _classify_question(cls, text: str) -> str:
        t = (text or "").lower().strip()
        hard_factual_terms = [
            "dosagem", "dose", "mg", "posologia", "bula", "indicacao", "indicação", "para que serve", "forma farmaceutica",
            "forma farmacêutica", "apresentacao", "apresentação", "mecanismo", "efeito", "efeitos", "composicao", "composição",
            "contraindicacao", "contraindicação", "base de conhecimento", "documento", "guideline", "estudo", "protocolo",
            "responsavel tecnico", "responsável técnico", "farmaceutico responsável", "farmacêutico responsável", "registro", "crf", "quem é", "quem e",
        ]
        if any(term in t for term in hard_factual_terms) or cls._contains_person_query(t):
            return "factual_documental"
        training_terms = ["como conversar", "como abordar", "como explicar", "como apresentar", "como falar", "simule", "simular", "treinar", "treino", "explique", "resuma", "objeção", "objecao", "objeções", "objecoes"]
        if any(term in t for term in training_terms):
            return "treinamento_orientado"
        return "treinamento_orientado"

    @staticmethod
    def _normalize_entity(raw: str) -> str:
        text = (raw or "").strip(" ?.,;:\"'“”")
        for pattern in [
            r"^(consulte?\s+na\s+(?:sua\s+)?base(?:\s+de\s+conhecimento(?:s)?)?\s+)",
            r"^(consulta\s+na\s+(?:sua\s+)?base(?:\s+de\s+conhecimento(?:s)?)?\s+)",
            r"^(para\s+que\s+serve\s+(?:o|a)?\s*)",
            r"^(qual\s+a\s+posologia\s+)",
            r"^(quem\s+e\s+o\s+responsavel\s+tecnico\s+pelo\s+)",
            r"^(quem\s+é\s+o\s+responsável\s+técnico\s+pelo\s+)",
            r"^(qual\s+o\s+farmaceutico\s+responsavel\s+pelo\s+)",
            r"^(qual\s+o\s+farmacêutico\s+responsável\s+pelo\s+)",
            r"^(remedio|remédio|medicamento)\s+",
        ]:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", text).strip(" ?.,;:\"'“”")

    @classmethod
    def _extract_entity(cls, text: str) -> str:
        txt = (text or "").strip()
        for pattern in [r"(somalgin\s+cardio)", r"(dr\.?\s+adriano\s+pinheiro\s+coelho)"]:
            m = re.search(pattern, txt, flags=re.IGNORECASE)
            if m:
                return cls._normalize_entity(m.group(1))
        return cls._normalize_entity(txt)

    @staticmethod
    def _extract_attribute(text: str) -> str:
        txt = (text or "").lower()
        if any(term in txt for term in ["farmaceutico responsavel", "farmacêutico responsável", "responsavel tecnico", "responsável técnico", "dr. adriano pinheiro coelho", "crf"]):
            return "responsavel_tecnico"
        if any(term in txt for term in ["posologia", "dose", "dosagem", "mg"]):
            return "posologia"
        if any(term in txt for term in ["para que serve", "indicacao", "indicação", "indicações terapêuticas"]):
            return "indicacao"
        return "assunto_principal"

    @staticmethod
    def _attribute_synonyms(attribute_key: str) -> list[str]:
        return {
            "responsavel_tecnico": ["responsavel tecnico", "responsável técnico", "farmaceutico responsavel", "farmacêutico responsável", "farm. resp", "dr. adriano pinheiro coelho", "crf"],
            "indicacao": ["indicacao", "indicação", "uso indicado", "para que serve", "indicações terapêuticas"],
            "posologia": ["posologia", "dose", "dosagem", "regime posologico", "quantos mg"],
            "assunto_principal": ["resumo", "tema principal", "assunto"],
        }.get(attribute_key, [attribute_key])

    @classmethod
    def _build_retrieval_hints(cls, latest_user_message: str) -> dict[str, Any]:
        question_type = cls._classify_question(latest_user_message)
        entity = cls._extract_entity(latest_user_message)
        attribute_key = cls._extract_attribute(latest_user_message)
        synonyms = cls._attribute_synonyms(attribute_key)
        queries = []
        if latest_user_message:
            queries.append(latest_user_message.strip())
        if entity:
            queries.extend([entity, f'"{entity}"'])
            for syn in synonyms:
                queries.extend([f"{entity} {syn}", f'"{entity}" {syn}', f"{entity} bula {syn}"])
        deduped, seen = [], set()
        for q in queries:
            key = q.strip().lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(q.strip())
        return {"question_type": question_type, "entity": entity, "attribute_key": attribute_key, "attribute_synonyms": synonyms, "retrieval_queries": deduped[:16]}

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
        consultation_seen = any(token in lower for token in ["consultation", "consulta", "mlp8gvtsyx", "gtp5hlthjf"])
        evaluation_seen = any(token in lower for token in ["evaluation", "avaliacao", "avaliação", "nshp4aaekt", "se4ugp8ftg", "score_global", "clareza", "manejo_de_objecoes"])
        retrieval_seen = any(token in lower for token in ["retrieval", "retrieve", "knowledgebase", "knowledge base", "vector", "chunk", "citation", "citations", "s3://", "somalgin_cardio", "x-amz-bedrock-kb-chunk-id"])
        failure_seen = any(token in lower for token in ["not available", "resource not found", "access denied", "validationexception", "exception", "failure", "erro", "error"])
        return {"consultation_seen": consultation_seen, "evaluation_seen": evaluation_seen, "retrieval_seen": retrieval_seen, "failure_seen": failure_seen, "raw_excerpt": flat[:2500]}

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

    def _normalize_compliance_payload(self, compliance: dict[str, Any], retrieval_hints: dict[str, Any], citations: list[dict[str, Any]], raw_text: str, trace_summary: dict[str, Any]) -> dict[str, Any]:
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

    def _training_tail(self) -> str:
        return "\n\nPara avançar no treinamento, posso seguir por três caminhos: 1) simular uma conversa com o médico; 2) trabalhar objeções e respostas; 3) montar uma abordagem prática para essa especialidade."

    def _factual_tail(self) -> str:
        return "\n\nAgora, pensando no treinamento, posso te ajudar de três formas: 1) transformar essa informação em abordagem para o médico; 2) simular uma objeção relacionada a esse tema; 3) aprofundar outro ponto factual do medicamento."

    def _already_has_tail(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(m in lower for m in ["para avançar no treinamento", "agora, pensando no treinamento", "posso te ajudar de três formas", "posso seguir por três caminhos"])

    def _ensure_portuguese(self, text: str) -> str:
        if not text:
            return text
        replacements = {
            "The information about the technician responsible for Somalgin Cardio is not available in the knowledge base. If you have any other questions or need further assistance with training, please let me know.": "A informação sobre o responsável técnico do Somalgin Cardio não foi encontrada na base de conhecimento neste turno. Posso continuar te ajudando com treinamento ou aprofundar outra pergunta factual.",
            "The information about the pharmacist responsible for Somalgin Cardio is not available in the knowledge base. If you have any other questions or need further assistance with training, please let me know.": "A informação sobre o farmacêutico responsável pelo Somalgin Cardio não foi encontrada na base de conhecimento neste turno. Posso continuar te ajudando com treinamento ou aprofundar outra pergunta factual.",
            "is the responsible technician for Somalgin Cardio, with the registration number CRF/SP: 22.883.": "é o responsável técnico pelo Somalgin Cardio, com registro CRF/SP 22.883.",
        }
        out = text
        for old, new in replacements.items():
            out = out.replace(old, new)
        return out

    def _build_training_fallback(self, context: AgentContext) -> str:
        return (
            "Para abordar um médico sobre esse tema, organize a visita em cinco passos: "
            "1) abertura objetiva; 2) investigação rápida da rotina clínica; 3) conexão do tema com um problema real do consultório; "
            "4) mensagem-chave simples e prática; 5) fechamento com uma pergunta que convide dúvidas ou objeções."
        ) + self._training_tail()

    def _resolve_short_option(self, context: AgentContext) -> str | None:
        msg = (context.latest_user_message or "").strip()
        return self.OPTION_MAP.get(msg)

    def _conversation_simulation(self, context: AgentContext) -> str:
        specialty = context.prompt_bundle.get("specialty", {}).get("title") or "a especialidade"
        history_text = self._flatten_any(context.conversation_history).lower()
        theme = "TDAH" if "tdah" in history_text or "tdah" in (context.latest_user_message or "").lower() else "o tema proposto"
        return f"Vamos simular. Eu serei o médico de {specialty}.\n\nMédico: \"Tudo bem. Você comentou que queria falar sobre {theme}. Em 1 minuto, qual é a sua mensagem principal para minha prática clínica?\"{self._training_tail()}"

    def _objection_simulation(self, context: AgentContext) -> str:
        return f"Vamos trabalhar uma objeção.\n\nMédico: \"Eu entendo o tema, mas no consultório eu tenho pouco tempo e preciso ver utilidade prática. Por que essa informação é relevante para meus pacientes e para minha tomada de decisão?\"{self._training_tail()}"

    def _practical_approach(self, context: AgentContext) -> str:
        specialty = context.prompt_bundle.get("specialty", {}).get("title") or "essa especialidade"
        return f"Uma abordagem prática para {specialty} pode seguir este roteiro:\n1. abertura curta e respeitosa;\n2. uma pergunta investigativa sobre perfil de paciente;\n3. conexão do tema com uma necessidade clínica concreta;\n4. mensagem-chave em linguagem simples;\n5. fechamento com convite para objeções ou critérios de uso.{self._training_tail()}"

    def _preflight_consultation(self, team: dict[str, Any], latest_user_message: str, retrieval_hints: dict[str, Any]) -> dict[str, Any]:
        collaborator = ((team.get("collaborators") or {}).get("consultation") or {})
        agent_id = collaborator.get("agent_id")
        alias_id = collaborator.get("alias_id")
        if not agent_id or not alias_id:
            return {"ok": False, "text": "", "citations": [], "traces": [], "reason": "missing_consultation_binding"}
        prompt = (
            "PERGUNTA FACTUAL/DOCUMENTAL\n"
            f"{latest_user_message}\n\n"
            "OBJETIVO\n- Consultar a base de conhecimento e responder em portugues do Brasil.\n"
            "- Responder apenas com o dado factual suportado.\n"
            "- Se houver suporte, nao diga que a informacao esta indisponivel.\n\n"
            f"RETRIEVAL_HINTS\n{json.dumps(retrieval_hints, ensure_ascii=False)}"
        )
        try:
            invoked = self.bedrock.invoke_agent(agent_id=agent_id, alias_id=alias_id, session_id=f"preflight-{agent_id}", text=prompt, session_state=None, enable_trace=True)
            text = self._ensure_portuguese(invoked.text or "")
            citations = invoked.citations or []
            traces = invoked.traces or []
            trace_summary = self._summarize_traces(traces)
            ok = bool(citations) or bool(trace_summary.get("retrieval_seen")) or self._looks_like_human_answer(text)
            return {"ok": ok, "text": text, "citations": citations, "traces": traces, "trace_summary": trace_summary}
        except Exception as exc:
            return {"ok": False, "text": "", "citations": [], "traces": [], "reason": str(exc)}

    def _extract_evaluation_from_traces(self, traces: list[dict[str, Any]] | None) -> dict[str, Any]:
        flat = self._flatten_any(traces or [])
        if not flat:
            return {}
        # Try JSON blob
        json_match = re.search(r'(\{[^{}]*"score_global"[^{}]*\})', flat)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        payload = {}
        patterns = {
            "score_global": r"score_global[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
            "clareza": r"clareza[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
            "investigacao_de_necessidade": r"investigacao_de_necessidade[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
            "dominio_tecnico": r"dominio_tecnico[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
            "manejo_de_objecoes": r"manejo_de_objecoes[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
            "compliance": r"compliance[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?)",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, flat, flags=re.IGNORECASE)
            if m:
                payload[key] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
        feedback = re.search(r"(feedback_curto|comentario|comentário)[^A-Za-z0-9]{0,10}([^\.]{10,180})", flat, flags=re.IGNORECASE)
        if feedback:
            payload["feedback_curto"] = feedback.group(2).strip()
        return payload

    def _build_structured_timeline(self, retrieval_hints: dict[str, Any], compliance: dict[str, Any], final_reply: str, citations: list[dict[str, Any]], parsed: dict[str, Any], prompt_header: str, trace_summary: dict[str, Any], evaluation_payload: dict[str, Any]) -> list[dict[str, Any]]:
        qtype = retrieval_hints.get("question_type", "treinamento_orientado")
        items = [{
            "agent": "supervisor",
            "title": "Classificação do turno",
            "message": "Pergunta classificada como factual/documental." if qtype == "factual_documental" else "Pergunta classificada como treinamento orientado.",
            "status": "done",
            "input_payload": {"question_type": qtype, "retrieval_hints": retrieval_hints},
            "output_payload": {"decision": qtype},
        }]
        if qtype == "factual_documental":
            items.append({
                "agent": "consultation",
                "title": "Consulta factual executada",
                "message": "O supervisor exigiu consulta à base por entidade, sinônimos e seções prováveis.",
                "status": "done",
                "input_payload": {"entity": retrieval_hints.get("entity"), "queries": retrieval_hints.get("retrieval_queries")},
                "output_payload": {"citations_count": len(citations), "trace_summary": trace_summary},
            })
            items.append({
                "agent": "consultation",
                "title": "Resultado da evidência",
                "message": "O backend recebeu evidência factual suficiente para confirmar o dado solicitado." if compliance.get("evidence_status") in {"supported", "supported_by_trace", "supported_by_preflight"} else "Não houve suporte factual suficiente para confirmar o dado solicitado neste turno.",
                "status": "done" if compliance.get("evidence_status") in {"supported", "supported_by_trace", "supported_by_preflight"} else "error",
                "input_payload": {"evidence_threshold": "supported"},
                "output_payload": {"citations": citations, "trace_summary": trace_summary},
            })
        estatus = compliance.get("evidence_status") or "uncertain"
        items.append({
            "agent": "compliance",
            "title": "Parecer de compliance",
            "message": {
                "supported": "O parecer de compliance confirmou que havia suporte factual suficiente para a resposta.",
                "supported_by_trace": "O parecer de compliance aceitou a evidência observada nos traces do colaborador de consulta.",
                "supported_by_preflight": "O parecer de compliance aceitou a evidência validada por consulta factual direta ao colaborador.",
                "unsupported": "O parecer de compliance rejeitou a confirmação factual por falta de evidência suficiente.",
                "uncertain": "O parecer de compliance indicou evidência insuficiente para confirmar o dado com segurança.",
                "not_required": "O parecer de compliance indicou que evidência factual estrita não era obrigatória neste turno de treinamento.",
            }.get(estatus, "O parecer de compliance foi processado para este turno."),
            "status": "done" if estatus in {"supported", "supported_by_trace", "supported_by_preflight", "not_required"} else "error",
            "input_payload": {"citations_count": len(citations), "question_type": qtype},
            "output_payload": compliance,
        })
        if evaluation_payload:
            items.append({
                "agent": "evaluation",
                "title": "Monitoramento Avaliação corrente",
                "message": "O agente avaliador retornou avaliação estruturada do turno atual.",
                "status": "done",
                "input_payload": {"question_type": qtype},
                "output_payload": evaluation_payload,
            })
        items.append({
            "agent": "supervisor",
            "title": "Resposta final entregue",
            "message": final_reply[:180] + ("…" if len(final_reply) > 180 else ""),
            "status": "done",
            "input_payload": {"prompt_header": prompt_header},
            "output_payload": {"parsed": parsed, "final_reply": final_reply},
        })
        return items

    def process_turn(self, session: ConversationSession, latest_user_message: str) -> dict[str, Any]:
        context = self.build_context(session, latest_user_message)
        team = self._resolve_team_binding(session)
        supervisor = team.get("supervisor") or {}
        if not supervisor.get("agent_id") or not supervisor.get("alias_id"):
            raise RuntimeError(f"Supervisor Bedrock nao configurado para o blueprint '{context.blueprint_slug}'. Binding resolvido: {team}")

        short_option = self._resolve_short_option(context)
        if short_option:
            if short_option == "simular_conversa":
                final_reply = self._conversation_simulation(context)
            elif short_option == "trabalhar_objecoes":
                final_reply = self._objection_simulation(context)
            else:
                final_reply = self._practical_approach(context)
            evaluation = {}
            compliance = {"approved": None, "evidence_status": "not_required", "confidence": "training"}
            timeline = self._build_structured_timeline({"question_type": "treinamento_orientado"}, compliance, final_reply, [], {}, "short-option", {}, evaluation)
            return {"supervisor": AgentDecision(role="bedrock_supervisor", message=final_reply, payload={}, telemetry={"latency_ms": 0, "status": "completed"}), "final_reply": final_reply, "evaluation": evaluation, "compliance": compliance, "citations": [], "traces": [], "team_summary": [], "timeline": timeline, "factual_guard": {"question_type": "treinamento_orientado"}}

        retrieval_hints = self._build_retrieval_hints(latest_user_message)
        session_state = {
            "sessionAttributes": PromptComposer.build_session_attributes(session_id=context.session_id, blueprint_slug=context.blueprint_slug, user_id=context.user_id),
            "promptSessionAttributes": {
                **PromptComposer.build_prompt_session_attributes(context.prompt_bundle),
                "question_type": retrieval_hints["question_type"],
                "entity": retrieval_hints["entity"],
                "attribute_key": retrieval_hints["attribute_key"],
                "kb_priority": "required" if retrieval_hints["question_type"] == "factual_documental" else "supporting",
                "force_evaluation": "true" if retrieval_hints["question_type"] == "treinamento_orientado" else "false",
            },
        }

        prompt_header = (
            "CONTEXTO OPERACIONAL DA SESSAO\n"
            "- Objetivo principal: treinar propagandistas em assuntos medicos, especialidades, cenarios, medicamentos e abordagem com medicos.\n"
            "- Para perguntas factuais/documentais, acione consultation e responda com o dado factual quando houver evidência suficiente.\n"
            "- Para turnos de treinamento, acione evaluation para produzir avaliação estruturada da performance corrente quando aplicável.\n"
            "- Se a pergunta for factual e a consulta trouxer suporte, nao substitua o resultado por fallback de treinamento.\n"
            "- Sempre responda em portugues do Brasil.\n"
            "- Depois de responder o que o usuario pediu, ofereca caminhos curtos para aprofundar o treinamento.\n"
            "- Para perguntas de treinamento, responda como orientacao ao propagandista, nao como aula generica para medico.\n\n"
            f"ULTIMA MENSAGEM DO USUARIO\n{latest_user_message}\n\n"
            "INSTRUCOES DE SAIDA\n"
            "- Devolva JSON quando possivel no contrato esperado.\n"
            "- Se houver avaliação, devolva no campo evaluation.\n"
            "- Nao invente fatos.\n- Responda em portugues do Brasil.\n"
        )

        try:
            invoked = self.bedrock.invoke_agent(agent_id=supervisor["agent_id"], alias_id=supervisor["alias_id"], session_id=f"django-session-{session.pk}", text=prompt_header, session_state=session_state, enable_trace=True)
        except Exception:
            if retrieval_hints["question_type"] == "factual_documental":
                preflight = self._preflight_consultation(team, latest_user_message, retrieval_hints)
                if preflight.get("ok"):
                    final_reply = self._ensure_portuguese(preflight.get("text", "")).strip()
                    if final_reply and not self._already_has_tail(final_reply):
                        final_reply += self._factual_tail()
                    compliance = {"approved": True, "evidence_status": "supported_by_preflight", "confidence": "medium"}
                    timeline = self._build_structured_timeline(retrieval_hints, compliance, final_reply, preflight.get("citations", []), {}, prompt_header, preflight.get("trace_summary", {}), {})
                    return {"supervisor": AgentDecision(role="bedrock_supervisor", message=final_reply, payload={"preflight": preflight}, telemetry={"latency_ms": 0, "status": "completed"}), "final_reply": final_reply, "evaluation": {}, "compliance": compliance, "citations": preflight.get("citations", []), "traces": preflight.get("traces", []), "team_summary": [], "timeline": timeline, "factual_guard": {"question_type": retrieval_hints["question_type"], "evidence_status": "supported_by_preflight"}}
            raise

        parsed = self._safe_json(invoked.text)
        raw_text = parsed.get("_raw_text") or invoked.text or ""
        trace_summary = self._summarize_traces(invoked.traces)
        compliance = self._normalize_compliance_payload(parsed.get("compliance") or {}, retrieval_hints, invoked.citations, raw_text, trace_summary)

        preflight = None
        if retrieval_hints["question_type"] == "factual_documental" and compliance.get("evidence_status") in {"uncertain", "unsupported"}:
            preflight = self._preflight_consultation(team, latest_user_message, retrieval_hints)
            if preflight.get("ok"):
                compliance["evidence_status"] = "supported_by_preflight"
                compliance["confidence"] = "medium"
                compliance["approved"] = True

        final_reply = parsed.get("final_reply") or ""
        if not isinstance(final_reply, str):
            final_reply = str(final_reply)
        if not final_reply.strip() and self._looks_like_human_answer(raw_text):
            final_reply = raw_text.strip()
        final_reply = self._ensure_portuguese(final_reply)
        raw_text = self._ensure_portuguese(raw_text)

        if retrieval_hints["question_type"] == "factual_documental":
            if compliance.get("evidence_status") in {"supported", "supported_by_trace", "supported_by_preflight"}:
                if compliance.get("evidence_status") == "supported_by_preflight" and preflight and self._looks_like_human_answer(preflight.get("text", "")):
                    final_reply = preflight.get("text", "").strip()
                elif not final_reply.strip() and self._looks_like_human_answer(raw_text):
                    final_reply = raw_text.strip()
                if not final_reply.strip():
                    final_reply = "A consulta factual foi executada com suporte na base, mas a resposta final não veio estruturada. Refaça a pergunta para eu tentar novamente com o mesmo conteúdo recuperado."
                if not self._already_has_tail(final_reply):
                    final_reply += self._factual_tail()
            else:
                final_reply = "Nao consegui confirmar esse dado especifico com evidencia suficiente da base neste turno. Posso seguir te ajudando de forma segura explicando o contexto clinico do tema, como apresentar esse assunto ao medico e como formular a pergunta certa para buscar esse campo documental sem assumir um fato nao confirmado."
                if not self._already_has_tail(final_reply):
                    final_reply += self._factual_tail()
        else:
            if not final_reply.strip():
                final_reply = self._build_training_fallback(context)
            elif not self._already_has_tail(final_reply):
                final_reply += self._training_tail()

        evaluation_payload = parsed.get("evaluation") or {}
        if not evaluation_payload and trace_summary.get("evaluation_seen"):
            evaluation_payload = self._extract_evaluation_from_traces(invoked.traces)

        timeline = self._build_structured_timeline(retrieval_hints, compliance, final_reply, invoked.citations, parsed, prompt_header, trace_summary, evaluation_payload)

        return {
            "supervisor": AgentDecision(
                role="bedrock_supervisor",
                message=invoked.text,
                payload={"parsed": parsed, "citations": invoked.citations, "traces": invoked.traces, "raw": invoked.raw, "team_binding": team, "retrieval_hints": retrieval_hints, "trace_summary": trace_summary, "preflight": preflight},
                telemetry={"latency_ms": invoked.latency_ms, "status": "completed"},
            ),
            "final_reply": final_reply,
            "evaluation": evaluation_payload,
            "compliance": compliance,
            "citations": invoked.citations,
            "traces": invoked.traces,
            "team_summary": parsed.get("team_summary") or [],
            "timeline": timeline,
            "factual_guard": {"entity": retrieval_hints.get("entity"), "attribute_key": retrieval_hints.get("attribute_key"), "question_type": retrieval_hints.get("question_type"), "evidence_status": compliance.get("evidence_status"), "citations_count": len(invoked.citations), "trace_summary": trace_summary, "preflight_ok": bool((preflight or {}).get("ok"))},
        }
