#!/usr/bin/env python3
"""
Gera um Markdown estruturado de bula a partir de um TXT bruto.

Uso:
  python generate_bula_md.py Somalgin-Cardio.txt --drug-name "Somalgin Cardio" --outdir ./saida
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path


SECTION_ORDER = [
    ("identificacao_do_medicamento", "Identificação do medicamento"),
    ("forma_farmaceutica_e_apresentacao", "Forma farmacêutica e apresentação"),
    ("composicao", "Composição"),
    ("indicacoes_terapeuticas", "Indicações terapêuticas (Para que serve)"),
    ("mecanismo_de_acao", "Mecanismo de ação"),
    ("contraindicacoes", "Contraindicações"),
    ("advertencias_e_precaucoes", "Advertências e precauções"),
    ("interacoes_medicamentosas", "Interações medicamentosas"),
    ("armazenamento", "Armazenamento"),
    ("posologia", "Posologia (Como usar)"),
    ("esquecimento_de_dose", "Esquecimento de dose"),
    ("reacoes_adversas", "Reações adversas"),
    ("superdose", "Superdose"),
    ("responsavel_tecnico_e_fabricante", "Responsável técnico e fabricante"),
]

HEADERS = [
    ("identificacao_do_medicamento", [
        r"IDENTIFICA[CÇ][AÃ]O DO MEDICAMENTO",
    ]),
    ("forma_farmaceutica_e_apresentacao", [
        r"FORMA FARMAC[ÊE]UTICA E APRESENTA[CÇ][AÃ]O",
    ]),
    ("composicao", [
        r"COMPOSI[CÇ][AÃ]O",
    ]),
    ("indicacoes_terapeuticas", [
        r"PARA QUE ESTE MEDICAMENTO [ÉE] INDICADO\?",
        r"PARA QUE SERVE\?",
        r"INDICA[CÇ][OÕ]ES TERAP[ÊE]UTICAS",
    ]),
    ("mecanismo_de_acao", [
        r"COMO ESTE MEDICAMENTO FUNCIONA\?",
        r"MECANISMO DE A[CÇ][AÃ]O",
    ]),
    ("contraindicacoes", [
        r"QUANDO N[ÃA]O DEVO USAR ESTE MEDICAMENTO\?",
        r"CONTRAINDICA[CÇ][OÕ]ES",
    ]),
    ("advertencias_e_precaucoes", [
        r"O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO\?",
        r"ADVERT[ÊE]NCIAS E PRECAU[CÇ][OÕ]ES",
    ]),
    ("interacoes_medicamentosas", [
        r"INTERA[CÇ][OÕ]ES MEDICAMENTOSAS",
        r"INTERA[CÇ][AÃ]O MEDICAMENTO",
    ]),
    ("armazenamento", [
        r"ONDE, COMO E POR QUANTO TEMPO POSSO GUARDAR ESTE MEDICAMENTO\?",
        r"CUIDADOS DE CONSERVA[CÇ][AÃ]O",
    ]),
    ("posologia", [
        r"COMO DEVO USAR ESTE MEDICAMENTO\?",
        r"POSOLOGIA",
        r"MODO DE USAR",
    ]),
    ("esquecimento_de_dose", [
        r"O QUE DEVO FAZER QUANDO EU ME ESQUECER DE USAR ESTE MEDICAMENTO\?",
        r"ESQUECIMENTO DE DOSE",
    ]),
    ("reacoes_adversas", [
        r"QUAIS OS MALES QUE ESTE MEDICAMENTO PODE ME CAUSAR\?",
        r"REA[CÇ][OÕ]ES ADVERSAS",
        r"EVENTOS ADVERSOS",
    ]),
    ("superdose", [
        r"O QUE FAZER SE ALGU[ÉE]M USAR UMA QUANTIDADE MAIOR DO QUE A INDICADA DESTE MEDICAMENTO\?",
        r"SUPERDOSE",
    ]),
    ("responsavel_tecnico_e_fabricante", [
        r"DIZERES LEGAIS",
        r"FARM\. RESP\.",
        r"REGISTRADO POR:",
        r"FABRICADO POR:",
    ]),
]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return ascii_only or "bula"


def infer_drug_name(text: str, fallback: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if clean and 1 < len(clean.split()) <= 5 and not clean.endswith(":"):
            if re.search(r"[A-Za-zÀ-ÿ]", clean):
                return clean
    return fallback


def find_headers(text: str) -> list[tuple[int, str, str]]:
    hits = []
    for key, patterns in HEADERS:
        for pattern in patterns:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                hits.append((m.start(), key, m.group(0)))
    dedup = {}
    for pos, key, header in hits:
        dedup[(pos, key)] = (pos, key, header)
    return sorted(dedup.values(), key=lambda x: x[0])


def split_sections(text: str) -> dict[str, str]:
    headers = find_headers(text)
    if not headers:
        return {"conteudo_integral": text}

    sections: dict[str, str] = {}
    first_pos = headers[0][0]
    preface = text[:first_pos].strip()
    if preface:
        sections["prefacio"] = preface

    for i, (pos, key, header) in enumerate(headers):
        start = pos + len(header)
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        if key in sections:
            sections[key] = (sections[key] + "\n\n" + body).strip()
        else:
            sections[key] = body
    return sections


def clean_section_content(key: str, content: str) -> str:
    content = content.strip()
    if key == "forma_farmaceutica_e_apresentacao":
        content = content.replace("USO ORAL", "\n\nUso oral")
        content = content.replace("USO ADULTO E PEDIATRICO", "\nUso adulto e pediátrico")
        content = content.replace("USO ADULTO E PEDIÁTRICO", "\nUso adulto e pediátrico")
    if key == "responsavel_tecnico_e_fabricante":
        content = content.replace("REGISTRADO POR:", "\nRegistrado por:\n")
        content = content.replace("FABRICADO POR:", "\nFabricado por:\n")
    return content.strip()


def build_md(drug_name: str, source_name: str, sections: dict[str, str]) -> str:
    lines = []
    lines.append(f"# {drug_name}")
    lines.append("")
    lines.append("## Metadados")
    lines.append("")
    lines.append(f"- Medicamento: {drug_name}")
    lines.append(f"- Fonte original: {source_name}")
    lines.append("- Tipo: bula estruturada para RAG")
    lines.append("")

    if "prefacio" in sections:
        lines.append("## Prefácio")
        lines.append("")
        lines.append(sections["prefacio"])
        lines.append("")

    for key, title in SECTION_ORDER:
        content = sections.get(key)
        if not content:
            continue
        lines.append(f"## {title}")
        lines.append("")
        lines.append(clean_section_content(key, content))
        lines.append("")

    if "conteudo_integral" in sections:
        lines.append("## Conteúdo integral")
        lines.append("")
        lines.append(sections["conteudo_integral"])
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--drug-name", type=str, default="")
    parser.add_argument("--outdir", type=Path, default=Path("saida_md"))
    args = parser.parse_args()

    raw = normalize_text(args.input_file.read_text(encoding="utf-8"))
    drug_name = args.drug_name.strip() or infer_drug_name(raw, args.input_file.stem)
    sections = split_sections(raw)

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_path = args.outdir / f"{slugify(drug_name)}.md"
    out_path.write_text(build_md(drug_name, args.input_file.name, sections), encoding="utf-8")

    print(out_path)


if __name__ == "__main__":
    main()
