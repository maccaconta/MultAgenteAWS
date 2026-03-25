from __future__ import annotations

from apps.catalog.seed_data import seed_default_catalog


def run_seed() -> None:
    seed_default_catalog()
