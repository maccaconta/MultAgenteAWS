#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from common_utils import normalize_text, slugify, write_json, write_markdown


def parse_txt_table(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        parts = [p.strip() for p in re.split(r"\s{2,}|\t|;", clean) if p.strip()]
        if len(parts) >= 2:
            row = {"campo_1": parts[0], "campo_2": parts[1]}
            for idx, value in enumerate(parts[2:], start=3):
                row[f"campo_{idx}"] = value
            rows.append(row)
    return rows


def parse_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def build_markdown(table_name: str, source_name: str, rows: list[dict[str, str]]) -> str:
    lines = [
        f"# {table_name}",
        "",
        "## Metadados",
        "",
        f"- Tabela: {table_name}",
        f"- Fonte original: {source_name}",
        "- Tipo: tabela de preço estruturada para RAG",
        "",
        "## Registros",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"### Registro {idx}")
        lines.append("")
        for key, value in row.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("saida_preco"))
    parser.add_argument("--table-name", type=str, default="")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    table_name = args.table_name.strip() or args.input_file.stem

    if args.input_file.suffix.lower() == ".csv":
        rows = parse_csv(args.input_file)
    else:
        rows = parse_txt_table(normalize_text(args.input_file.read_text(encoding="utf-8")))

    slug = slugify(table_name)
    md_path = args.outdir / f"{slug}_structured.md"
    json_path = args.outdir / f"{slug}_structured.json"

    write_markdown(md_path, build_markdown(table_name, args.input_file.name, rows))
    write_json(json_path, {
        "document_type": "tabela_preco",
        "nome_tabela": table_name,
        "fonte_original": args.input_file.name,
        "registros": rows,
    })

    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()
