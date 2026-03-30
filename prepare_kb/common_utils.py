#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return ascii_only or "documento"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def ordered_dict_from_pairs(pairs: list[tuple[str, str]]) -> OrderedDict[str, str]:
    data: OrderedDict[str, str] = OrderedDict()
    for key, value in pairs:
        value = value.strip()
        if not value:
            continue
        if key in data:
            data[key] = (data[key] + "\n\n" + value).strip()
        else:
            data[key] = value
    return data
