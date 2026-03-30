#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common_utils import normalize_text, ordered_dict_from_pairs, slugify, write_json, write_markdown


SECTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("titulo_e_identificacao", [r"^\s*t[ií]tulo\b", r"^\s*title\b"]),
    ("resumo", [r"^\s*resumo\b", r"^\s*abstract\b"]),
    ("introducao", [r"^\s*introdu[cç][aã]o\b", r"^\s*introduction\b"]),
    ("objetivo", [r"^\s*objetivos?\b", r"^\s*objective[s]?\b"]),
    ("metodos", [r"^\s*m[eé]todos?\b", r"^\s*methods?\b"]),
    ("resultados", [r"^\s*resultados?\b", r"^\s*results?\b"]),
    ("discussao", [r"^\s*discuss[aã]o\b", r"^\s*discussion\b"]),
    ("conclusao", [r"^\s*conclus[aã]o\b", r"^\s*conclusion[s]?\b"]),
    ("referencias", [r"^\s*refer[eê]ncias\b", r"^\s*references\b"]),
]


def infer_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if clean and len(clean) > 12:
            return clean
    return fallback


def split_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        for key, patterns in SECTION_PATTERNS:
            if any(re.search(p, line, flags=re.IGNORECASE) for p in patterns):
                hits.append((idx, key))
                break

    if not hits:
        return {"conteudo_integral": text}

    pairs: list[tuple[str, str]] = []
    first_idx = hits[0][0]
    if first_idx > 0:
        pairs.append(("prefacio", "\n".join(lines[:first_idx]).strip()))

    for i, (idx, key) in enumerate(hits):
        next_idx = hits[i + 1][0] if i + 1 < len(hits) else len(lines)
        body = "\n".join(lines[idx + 1:next_idx]).strip()
        if body:
            pairs.append((key, body))
    return ordered_dict_from_pairs(pairs)


def build_markdown(title: str, source_name: str, sections: dict[str, str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Metadados",
        "",
        f"- Documento: {title}",
        f"- Fonte original: {source_name}",
        "- Tipo: artigo/tese estruturado para RAG",
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
    parser.add_argument("--outdir", type=Path, default=Path("saida_artigo"))
    parser.add_argument("--title", type=str, default="")
    args = parser.parse_args()

    raw = normalize_text(args.input_file.read_text(encoding="utf-8"))
    title = args.title.strip() or infer_title(raw, args.input_file.stem)
    sections = split_sections(raw)

    args.outdir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    md_path = args.outdir / f"{slug}_structured.md"
    json_path = args.outdir / f"{slug}_structured.json"

    write_markdown(md_path, build_markdown(title, args.input_file.name, sections))
    write_json(json_path, {
        "document_type": "artigo_ou_tese",
        "titulo": title,
        "fonte_original": args.input_file.name,
        "secoes": sections,
    })

    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()
