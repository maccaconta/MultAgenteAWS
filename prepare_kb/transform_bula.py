#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from common_utils import normalize_text, ordered_dict_from_pairs, slugify, write_json, write_markdown


SECTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("identificacao_do_medicamento", [r"\bidentifica[cç][aã]o\s+do\s+medicamento\b"]),
    ("apresentacoes", [r"\bapresenta[cç][oõ]es\b", r"\bapresenta[cç][aã]o\b", r"\bforma\s+farmac[eê]utica\s+e\s+apresenta[cç][aã]o\b"]),
    ("composicao", [r"\bcomposi[cç][aã]o\b"]),
    ("para_que_serve", [r"\bpara\s+que\s+serve\b", r"\bindica[cç][oõ]es?\s+terap[eê]uticas\b", r"\bindica[cç][aã]o\b", r"\buso\s+indicado\b"]),
    ("como_funciona", [r"\bcomo\s+funciona\b", r"\bmecanismo\s+de\s+a[cç][aã]o\b"]),
    ("quando_nao_devo_usar", [r"\bcontraindica[cç][oõ]es\b", r"\bcontraindica[cç][aã]o\b"]),
    ("o_que_devo_saber_antes_de_usar", [r"\badvert[eê]ncias\s+e\s+precau[cç][oõ]es\b", r"\badvert[eê]ncias\b", r"\bprecau[cç][oõ]es\b"]),
    ("como_devo_usar", [r"\bposologia\b", r"\bmodo\s+de\s+usar\b", r"\bdose\s+recomendada\b"]),
    ("o_que_fazer_se_esquecer", [r"\besquecimento\s+de\s+dose\b"]),
    ("quais_os_males", [r"\brea[cç][oõ]es?\s+adversas\b", r"\beventos?\s+adversos?\b"]),
    ("superdose", [r"\bsuperdose\b", r"\buso\s+em\s+excesso\b"]),
    ("armazenamento", [r"\bconserva[cç][aã]o\b", r"\bcuidados\s+de\s+armazenamento\b"]),
    ("responsavel_tecnico", [r"\brespons[aá]vel\s+t[eé]cnico\b", r"\bfarmac[eê]utico\s+respons[aá]vel\b"]),
]


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return normalized.encode("ascii", "ignore").decode("ascii")


def infer_drug_name(text: str, fallback: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:12]:
        if 2 <= len(line.split()) <= 6 and not line.endswith(":"):
            if re.search(r"[A-Za-z]", line):
                return line
    return fallback


def iter_line_spans(text: str) -> Iterable[tuple[int, int, str]]:
    pos = 0
    for line in text.splitlines(True):
        yield pos, pos + len(line), line.rstrip("\n")
        pos += len(line)


def find_section_hits(raw_text: str) -> list[tuple[int, int, str]]:
    folded = fold_text(raw_text)
    hits: list[tuple[int, int, str]] = []

    for key, patterns in SECTION_PATTERNS:
        for pattern in patterns:
            folded_pattern = fold_text(pattern)
            for match in re.finditer(folded_pattern, folded, flags=re.IGNORECASE):
                hits.append((match.start(), match.end(), key))

    for start, end, line in iter_line_spans(raw_text):
        clean = line.strip()
        if clean and clean.isupper() and 4 <= len(clean) <= 120:
            f = fold_text(clean)
            for key, patterns in SECTION_PATTERNS:
                tokens = re.findall(r"[a-z]{4,}", fold_text(" ".join(patterns)))
                if tokens and any(tok in f for tok in tokens):
                    hits.append((start, end, key))
                    break

    unique = {(s, k): (s, e, k) for s, e, k in hits}
    return sorted(unique.values(), key=lambda x: x[0])


def segment_sections(text: str) -> dict[str, str]:
    hits = find_section_hits(text)
    if not hits:
        return {"conteudo_integral": text.strip()}

    pairs: list[tuple[str, str]] = []
    first_start = hits[0][0]
    preface = text[:first_start].strip()
    if preface:
        pairs.append(("prefacio", preface))

    for idx, (_, end, key) in enumerate(hits):
        next_start = hits[idx + 1][0] if idx + 1 < len(hits) else len(text)
        body = text[end:next_start].strip()
        if body:
            pairs.append((key, body))
    return ordered_dict_from_pairs(pairs)


def build_markdown(drug_name: str, source_name: str, sections: dict[str, str]) -> str:
    lines = [
        f"# {drug_name}",
        "",
        "## Metadados",
        "",
        f"- Medicamento: {drug_name}",
        f"- Fonte original: {source_name}",
        "- Tipo: bula estruturada para RAG",
        "",
    ]
    for key, content in sections.items():
        lines.append(f"## {key.replace('_', ' ').title()}")
        lines.append("")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("saida_bula"))
    parser.add_argument("--drug-name", type=str, default="")
    args = parser.parse_args()

    raw = normalize_text(args.input_file.read_text(encoding="utf-8"))
    drug_name = args.drug_name.strip() or infer_drug_name(raw, args.input_file.stem)
    sections = segment_sections(raw)

    args.outdir.mkdir(parents=True, exist_ok=True)
    slug = slugify(drug_name)
    md_path = args.outdir / f"{slug}_structured.md"
    json_path = args.outdir / f"{slug}_structured.json"

    write_markdown(md_path, build_markdown(drug_name, args.input_file.name, sections))
    write_json(json_path, {
        "document_type": "bula",
        "medicamento": drug_name,
        "fonte_original": args.input_file.name,
        "secoes": sections,
    })

    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()
