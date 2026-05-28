#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import sys

# Ajouter le répertoire parent au path pour accéder aux modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modules"))

from enrichir_calendrier_elo import (
    BASE_HEADERS,
    ELO_HEADERS,
    WORKBOOK_NAME,
    enrich_calendar_rows,
    load_calendar_rows,
    load_elo_rankings,
    normalize_token,
)


def row_to_tuple(row: dict[str, str]) -> tuple[str, ...]:
    return tuple((row.get(header, "") or "").strip() for header in BASE_HEADERS + ELO_HEADERS)


def load_actual_rows(enriched_csv: Path) -> tuple[Counter[tuple[str, ...]], Counter[str], int]:
    actual_rows: Counter[tuple[str, ...]] = Counter()
    seeded_per_team: Counter[str] = Counter()
    total_rows = 0

    with enriched_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        headers = reader.fieldnames or []
        if headers != BASE_HEADERS + ELO_HEADERS:
            raise ValueError(
                "Entetes invalides dans le CSV enrichi.\n"
                f"Attendu: {BASE_HEADERS + ELO_HEADERS}\n"
                f"Recu:    {headers}"
            )

        for row in reader:
            if not row or not any((value or "").strip() for value in row.values() if value is not None):
                continue

            actual_rows[row_to_tuple(row)] += 1
            if row.get("ELO domicile avant match"):
                seeded_per_team[normalize_token(row.get("Domicile", ""))] += 1
            if row.get("ELO extérieur avant match"):
                seeded_per_team[normalize_token(row.get("Exterieur", ""))] += 1
            total_rows += 1

    return actual_rows, seeded_per_team, total_rows


def print_counter_diff(expected: Counter, actual: Counter, label: str, max_items: int = 5) -> None:
    missing = expected - actual
    extra = actual - expected

    print(f"{label}:")
    print(f"- Lignes manquantes: {sum(missing.values())}")
    print(f"- Lignes en trop:    {sum(extra.values())}")

    if missing:
        print("\nExemples de lignes manquantes:")
        for index, (row_tuple, count) in enumerate(missing.items(), start=1):
            print(f"- x{count} | {';'.join(row_tuple)}")
            if index >= max_items:
                break

    if extra:
        print("\nExemples de lignes en trop:")
        for index, (row_tuple, count) in enumerate(extra.items(), start=1):
            print(f"- x{count} | {';'.join(row_tuple)}")
            if index >= max_items:
                break


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workbook_path = script_dir.parent.parent / "donnée prof" / WORKBOOK_NAME
    input_csv = script_dir.parent / "data_intermediaire" / "calendrier_resultat_fusionne.csv"
    enriched_csv = script_dir.parent / "data_intermediaire" / "calendrier_resultat_fusionne_elo.csv"

    if not enriched_csv.exists():
        print(f"ERREUR: fichier enrichi introuvable: {enriched_csv}")
        print("Lance d'abord le pipeline pour generer le fichier.")
        return 1

    rankings = load_elo_rankings(workbook_path)
    calendar_rows = load_calendar_rows(input_csv)
    expected_enriched_rows, expected_seeded_teams = enrich_calendar_rows(calendar_rows, rankings)

    expected_counter = Counter(row_to_tuple(row) for row in expected_enriched_rows)
    actual_counter, actual_seeded_teams, actual_total = load_actual_rows(enriched_csv)

    print("Verification de l'enrichissement ELO")
    print(f"- Total source:  {len(calendar_rows)}")
    print(f"- Total enrichi: {actual_total}")
    print("- Equipes initialisées en 24-25:")

    teams = sorted(set(expected_seeded_teams) | set(actual_seeded_teams), key=str.lower)
    for team in teams:
        src = 1 if team in expected_seeded_teams else 0
        dst = 1 if team in actual_seeded_teams else 0
        status = "OK" if src == dst else "KO"
        print(f"  {status} | {team}: source={src}, enrichi={dst}")

    if expected_counter == actual_counter:
        print("\nRESULTAT: OK - aucune ligne sautee, aucune degradation detectee.")
        return 0

    print("\nRESULTAT: KO - des ecarts ont ete detectes.")
    print_counter_diff(expected_counter, actual_counter, "Detail des ecarts")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
