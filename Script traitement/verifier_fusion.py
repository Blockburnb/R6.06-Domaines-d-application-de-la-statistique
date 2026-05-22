#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from fusion_fichier_equipes import OUTPUT_HEADERS, build_output_row, open_csv_with_fallback


def row_to_tuple(row: dict[str, str]) -> tuple[str, ...]:
    return tuple((row.get(header, "") or "").strip() for header in OUTPUT_HEADERS)


def load_expected_rows(source_dir: Path) -> tuple[Counter[tuple[str, ...]], Counter[str], int]:
    expected_rows: Counter[tuple[str, ...]] = Counter()
    expected_per_team: Counter[str] = Counter()
    total_rows = 0

    csv_files = sorted(source_dir.glob("*.csv"), key=lambda p: p.name.lower())
    if not csv_files:
        raise FileNotFoundError(f"Aucun CSV trouve dans {source_dir}")

    for csv_file in csv_files:
        team_name = csv_file.stem
        with open_csv_with_fallback(csv_file) as in_handle:
            reader = csv.DictReader(in_handle, delimiter=";")
            for row in reader:
                if not row or not any((val or "").strip() for val in row.values() if val is not None):
                    continue
                normalized = build_output_row(row, team_name)
                expected_rows[row_to_tuple(normalized)] += 1
                expected_per_team[team_name] += 1
                total_rows += 1

    return expected_rows, expected_per_team, total_rows


def load_actual_rows(merged_csv: Path) -> tuple[Counter[tuple[str, ...]], Counter[str], int]:
    actual_rows: Counter[tuple[str, ...]] = Counter()
    actual_per_team: Counter[str] = Counter()
    total_rows = 0

    with merged_csv.open("r", encoding="utf-8", newline="") as in_handle:
        reader = csv.DictReader(in_handle, delimiter=";")

        headers = reader.fieldnames or []
        if headers != OUTPUT_HEADERS:
            raise ValueError(
                "Entetes invalides dans le fichier fusionne.\n"
                f"Attendu: {OUTPUT_HEADERS}\n"
                f"Recu:    {headers}"
            )

        for row in reader:
            if not row or not any((val or "").strip() for val in row.values() if val is not None):
                continue
            row_tuple = row_to_tuple(row)
            actual_rows[row_tuple] += 1
            actual_per_team[(row.get("Equipe", "") or "").strip()] += 1
            total_rows += 1

    return actual_rows, actual_per_team, total_rows


def print_counter_diff(expected: Counter, actual: Counter, label: str, max_items: int = 5) -> None:
    missing = expected - actual
    extra = actual - expected

    print(f"{label}: ")
    print(f"- Lignes manquantes: {sum(missing.values())}")
    print(f"- Lignes en trop:    {sum(extra.values())}")

    if missing:
        print("\nExemples de lignes manquantes:")
        shown = 0
        for row_tuple, count in missing.items():
            print(f"- x{count} | {';'.join(row_tuple)}")
            shown += 1
            if shown >= max_items:
                break

    if extra:
        print("\nExemples de lignes en trop:")
        shown = 0
        for row_tuple, count in extra.items():
            print(f"- x{count} | {';'.join(row_tuple)}")
            shown += 1
            if shown >= max_items:
                break


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    source_dir = script_dir.parent / "donnée prof" / "Fichier Equipe"
    merged_csv = script_dir / "equipes_fusionnees.csv"

    if not merged_csv.exists():
        print(f"ERREUR: fichier fusionne introuvable: {merged_csv}")
        print("Lance d'abord fusion_fichier_equipes.py pour generer le fichier.")
        return 1

    expected_rows, expected_per_team, expected_total = load_expected_rows(source_dir)
    actual_rows, actual_per_team, actual_total = load_actual_rows(merged_csv)

    print("Verification de la fusion")
    print(f"- Total source:  {expected_total}")
    print(f"- Total fusion:  {actual_total}")

    teams = sorted(set(expected_per_team) | set(actual_per_team), key=str.lower)
    print("- Controle par equipe:")
    for team in teams:
        src = expected_per_team.get(team, 0)
        dst = actual_per_team.get(team, 0)
        status = "OK" if src == dst else "KO"
        print(f"  {status} | {team}: source={src}, fusion={dst}")

    if expected_rows == actual_rows:
        print("\nRESULTAT: OK - aucune ligne sautee, aucune degradation detectee.")
        return 0

    print("\nRESULTAT: KO - des ecarts ont ete detectes.")
    print_counter_diff(expected_rows, actual_rows, "Detail des ecarts")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
