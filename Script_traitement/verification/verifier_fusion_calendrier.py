#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

# Ajouter le répertoire parent au path pour accéder aux modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modules"))

from fusion_calendrier_resultat import (
    OUTPUT_HEADERS,
    WORKBOOK_NAME,
    extract_sheet_season,
    load_shared_strings,
    normalize_text,
    read_sheet_rows,
)

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def row_to_tuple(row: dict[str, str]) -> tuple[str, ...]:
    return tuple((row.get(header, "") or "").strip() for header in OUTPUT_HEADERS)


def load_expected_rows(workbook_path: Path) -> tuple[Counter[tuple[str, ...]], Counter[str], int]:
    expected_rows: Counter[tuple[str, ...]] = Counter()
    expected_per_season: Counter[str] = Counter()
    total_rows = 0

    with zipfile.ZipFile(workbook_path) as zf:
        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}
        shared_strings = load_shared_strings(zf)

        sheets_node = workbook_root.find("a:sheets", NS)
        if sheets_node is None:
            raise ValueError("Aucune feuille trouvee dans le classeur")

        for sheet in sheets_node:
            sheet_name = sheet.attrib["name"]
            season = extract_sheet_season(sheet_name)
            sheet_rel_id = sheet.attrib[f"{{{NS['r']}}}id"]
            sheet_target = rel_map[sheet_rel_id]
            sheet_path = f"xl/{sheet_target.lstrip('/')}"

            rows = read_sheet_rows(zf, sheet_path, shared_strings)
            if not rows:
                continue

            header_row = [normalize_text(value) for value in rows[0]]
            header_index = {name: idx for idx, name in enumerate(header_row)}

            required = ["journee", "domicile", "exterieur", "scoredomicile", "scoreexterieur", "derby"]
            missing = [label for label in required if label not in header_index]
            if missing:
                raise ValueError(
                    f"Entetes manquantes dans la feuille {sheet_name}: {', '.join(missing)}"
                )

            for raw_row in rows[1:]:
                if not raw_row or not any(value.strip() for value in raw_row):
                    continue

                expected_row = {
                    "Saison": season,
                    "Journee": raw_row[header_index["journee"]] if header_index["journee"] < len(raw_row) else "",
                    "Domicile": raw_row[header_index["domicile"]] if header_index["domicile"] < len(raw_row) else "",
                    "Exterieur": raw_row[header_index["exterieur"]] if header_index["exterieur"] < len(raw_row) else "",
                    "Score domicile": raw_row[header_index["scoredomicile"]] if header_index["scoredomicile"] < len(raw_row) else "",
                    "Score Exterieur": raw_row[header_index["scoreexterieur"]] if header_index["scoreexterieur"] < len(raw_row) else "",
                    "Derby": raw_row[header_index["derby"]] if header_index["derby"] < len(raw_row) else "",
                }
                expected_rows[row_to_tuple(expected_row)] += 1
                expected_per_season[season] += 1
                total_rows += 1

    return expected_rows, expected_per_season, total_rows


def load_actual_rows(merged_csv: Path) -> tuple[Counter[tuple[str, ...]], Counter[str], int]:
    actual_rows: Counter[tuple[str, ...]] = Counter()
    actual_per_season: Counter[str] = Counter()
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

            actual_rows[row_to_tuple(row)] += 1
            actual_per_season[(row.get("Saison", "") or "").strip()] += 1
            total_rows += 1

    return actual_rows, actual_per_season, total_rows


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
    merged_csv = script_dir.parent / "data_intermediaire" / "calendrier_resultat_fusionne.csv"

    if not merged_csv.exists():
        print(f"ERREUR: fichier fusionne introuvable: {merged_csv}")
        print("Lance d'abord le pipeline pour generer le fichier.")
        return 1

    expected_rows, expected_per_season, expected_total = load_expected_rows(workbook_path)
    actual_rows, actual_per_season, actual_total = load_actual_rows(merged_csv)

    print("Verification de la fusion du calendrier")
    print(f"- Total source:  {expected_total}")
    print(f"- Total fusion:  {actual_total}")
    print("- Controle par saison:")

    seasons = sorted(set(expected_per_season) | set(actual_per_season), key=str.lower)
    for season in seasons:
        src = expected_per_season.get(season, 0)
        dst = actual_per_season.get(season, 0)
        status = "OK" if src == dst else "KO"
        print(f"  {status} | {season}: source={src}, fusion={dst}")

    if expected_rows == actual_rows:
        print("\nRESULTAT: OK - aucune ligne sautee, aucune degradation detectee.")
        return 0

    print("\nRESULTAT: KO - des ecarts ont ete detectes.")
    print_counter_diff(expected_rows, actual_rows, "Detail des ecarts")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
