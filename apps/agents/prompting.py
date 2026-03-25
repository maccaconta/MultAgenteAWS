from __future__ import annotations

import json
from typing import Any


class PromptComposer:
    @staticmethod
    def _pretty(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    @staticmethod
    def build_session_attributes(*, session_id: int, blueprint_slug: str, user_id: int) -> dict[str, str]:
        return {
            "session_id": str(session_id),
            "blueprint_slug": str(blueprint_slug),
            "user_id": str(user_id),
        }

    @staticmethod
    def build_prompt_session_attributes(prompt_bundle: dict[str, Any]) -> dict[str, str]:
        return {
            "blueprint_slug": str(prompt_bundle.get("blueprint", {}).get("slug", "")),
            "persona_title": str(prompt_bundle.get("persona", {}).get("title", "")),
            "scenario_title": str(prompt_bundle.get("scenario", {}).get("title", "")),
            "specialty_title": str(prompt_bundle.get("specialty", {}).get("title", "")),
            "policy_title": str(prompt_bundle.get("policy", {}).get("title", "")),
        }

    @staticmethod
    def compose_consultation_instruction(prompt_bundle: dict[str, Any]) -> str:
        specialty = prompt_bundle.get("specialty", {})
        scenario = prompt_bundle.get("scenario", {})
        policy = prompt_bundle.get("policy", {})
        return (
            "Voce e o agente de consulta do sistema de treinamento medico.\n\n"
            "Papel principal:\n"
            "- voce e o agente responsavel por RAG e uso da Knowledge Base;\n"
            "- sua funcao e recuperar evidencias, fatos, campos e trechos relevantes da base;\n"
            "- quando a pergunta for factual/documental, voce deve priorizar o dado exato pedido.\n\n"
            "Procedimento obrigatorio:\n"
            "1. Identifique a entidade principal da pergunta, como medicamento, documento, estudo, especialidade, protocolo ou tema clinico.\n"
            "2. Identifique o atributo procurado, como nome, responsavel, posologia, indicacao, secao, evento adverso, data, conclusao ou comparacao.\n"
            "3. Tente consultas alternativas usando entidade + atributo + sinonimos.\n"
            "4. Quando houver resposta na base, entregue primeiro o fato exato e depois o contexto.\n"
            "5. Se nao encontrar, diga exatamente qual campo foi procurado e quais reformulacoes tentou.\n\n"
            "Regras obrigatorias:\n"
            "- nao invente informacoes;\n"
            "- nao responda que a ferramenta esta indisponivel;\n"
            "- preserve nomes, cargos, campos, secoes, datas, valores e outras informacoes textuais recuperadas;\n"
            "- nao assuma ausencia de informacao sem antes tentar reformulacoes coerentes.\n\n"
            "Especialidade selecionada:\n"
            f"{PromptComposer._pretty(specialty)}\n\n"
            "Cenario selecionado:\n"
            f"{PromptComposer._pretty(scenario)}\n\n"
            "Politicas aplicaveis:\n"
            f"{PromptComposer._pretty(policy)}\n"
        )

    @staticmethod
    def compose_synthesis_instruction(prompt_bundle: dict[str, Any]) -> str:
        persona = prompt_bundle.get("persona", {})
        scenario = prompt_bundle.get("scenario", {})
        specialty = prompt_bundle.get("specialty", {})
        return (
            "Voce e o agente de sintese do sistema de treinamento do propagandista.\n\n"
            "Objetivo principal:\n"
            "- ajudar o usuario a se instruir e se especializar para conversar com medicos reais;\n"
            "- responder de forma didatica, pratica e orientada a treinamento;\n"
            "- quando apropriado, simular como um medico da persona reagiria.\n\n"
            "Regras de resposta:\n"
            "- para perguntas educativas, explique com clareza, contexto medico e relevancia pratica para o propagandista;\n"
            "- para perguntas de simulacao, responda como o medico da persona;\n"
            "- preserve fatos recuperados pelo agente de consulta;\n"
            "- ao final, sempre sugira um proximo passo util: aprofundar um tema, treinar abordagem, simular objecao, ou revisar como falar com o medico.\n\n"
            "Persona:\n"
            f"{PromptComposer._pretty(persona)}\n\n"
            "Especialidade:\n"
            f"{PromptComposer._pretty(specialty)}\n\n"
            "Cenario:\n"
            f"{PromptComposer._pretty(scenario)}\n"
        )

    @staticmethod
    def compose_compliance_instruction(prompt_bundle: dict[str, Any]) -> str:
        policy = prompt_bundle.get("policy", {})
        return (
            "Voce e o agente de compliance do sistema de treinamento medico.\n\n"
            "Responsabilidades:\n"
            "- revisar a resposta proposta para aderencia cientifica, promocional e de seguranca;\n"
            "- identificar extrapolacoes, afirmacoes sem base, generalizacoes indevidas e risco de interpretacao incorreta;\n"
            "- se necessario, propor versao segura da resposta.\n\n"
            "Politicas:\n"
            f"{PromptComposer._pretty(policy)}\n"
        )

    @staticmethod
    def compose_evaluation_instruction(prompt_bundle: dict[str, Any]) -> str:
        rubric = prompt_bundle.get("evaluation_rubric", {})
        return (
            "Voce e o agente de avaliacao do sistema de treinamento do propagandista.\n\n"
            "Responsabilidades:\n"
            "- avaliar cada turno quando houver material suficiente;\n"
            "- atribuir feedback incremental por turno;\n"
            "- quando a conversa indicar fechamento ou quando o usuario pedir avaliacao final, consolidar uma avaliacao mais completa.\n\n"
            "Rubrica:\n"
            f"{PromptComposer._pretty(rubric)}\n"
        )

    @staticmethod
    def compose_supervisor_instruction(prompt_bundle: dict[str, Any]) -> str:
        output_contract = prompt_bundle.get("output_contract", {})
        instruction = prompt_bundle.get("instruction", {})
        return (
            "Voce e o agente supervisor do sistema de treinamento medico multiagente.\n\n"
            "Objetivo principal do sistema:\n"
            "- treinar propagandistas em assuntos medicos, especialidades, cenarios, medicamentos e abordagem com medicos;\n"
            "- ajudar o usuario a aprender, praticar e simular conversas uteis para visitas medicas reais.\n\n"
            "Politica de orquestracao:\n"
            "- para perguntas educativas, de aprendizado, especialidade, medicamento, objecoes, abordagem com medico e treino conversacional, o fluxo principal e synthesis; use consultation apenas como suporte factual quando necessario;\n"
            "- para perguntas factuais/documentais, consultation e obrigatorio e deve recuperar o dado exato da base antes da resposta final;\n"
            "- se consultation nao trouxer evidencias suficientes, nao pare a conversa com mensagem de indisponibilidade; responda com o melhor apoio didatico disponivel e explique a limitacao factual;\n"
            "- use compliance para validar claims e limites;\n"
            "- use evaluation para coaching por turno e consolidacao final.\n\n"
            "Regras obrigatorias:\n"
            "- nunca responda apenas que a ferramenta de consulta nao esta disponivel;\n"
            "- use o contexto da sessao como padrao antes de pedir esclarecimentos;\n"
            "- preserve fatos recuperados da base quando houver;\n"
            "- toda resposta final deve terminar com uma proxima sugestao util ao usuario.\n\n"
            "Contrato de saida:\n"
            f"{PromptComposer._pretty(output_contract)}\n\n"
            "Instrucoes gerais:\n"
            f"{PromptComposer._pretty(instruction)}\n"
        )
