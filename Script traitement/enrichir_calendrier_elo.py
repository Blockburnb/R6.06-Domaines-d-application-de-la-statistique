#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


WORKBOOK_NAME = "Classement ELO LFB.xlsx"
INPUT_CSV_NAME = "calendrier_resultat_fusionne.csv"
OUTPUT_CSV_NAME = "calendrier_resultat_fusionne_elo.csv"

BASE_HEADERS = [
    "Saison",
    "Journee",
    "Domicile",
    "Exterieur",
    "Score domicile",
    "Score Exterieur",
    "Derby",
]

ELO_HEADERS = [
    "ELO domicile avant match",
    "ELO extérieur avant match",
    "ELO domicile après match",
    "ELO extérieur après match",
]

OUTPUT_HEADERS = BASE_HEADERS + ELO_HEADERS

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def normalize_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def column_index_from_ref(cell_ref: str) -> int:
    match = re.match(r"[A-Z]+", cell_ref or "")
    if not match:
        return 0

    index = 0
    for char in match.group(0):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("a:si", NS):
        parts = [node.text or "" for node in item.iterfind(".//a:t", NS)]
        values.append("".join(parts))
    return values


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        text_node = cell.find("a:is/a:t", NS)
        return "" if text_node is None else (text_node.text or "")

    value_node = cell.find("a:v", NS)
    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""

    return value


def read_sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(zf.read(sheet_path))
    rows: list[list[str]] = []

    for row in root.findall(".//a:sheetData/a:row", NS):
        values: list[str] = []
        for cell in row.findall("a:c", NS):
            index = column_index_from_ref(cell.attrib.get("r", ""))
            if index <= 0:
                continue
            while len(values) < index:
                values.append("")
            values[index - 1] = read_cell_value(cell, shared_strings).strip()
        rows.append(values)

    return rows


def load_elo_rankings(workbook_path: Path) -> dict[str, str]:
    if not workbook_path.exists():
        raise FileNotFoundError(f"Classeur ELO introuvable: {workbook_path}")

    with zipfile.ZipFile(workbook_path) as zf:
        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}
        shared_strings = load_shared_strings(zf)

        sheets_node = workbook_root.find("a:sheets", NS)
        if sheets_node is None or len(sheets_node) == 0:
            raise ValueError("Aucune feuille trouvee dans le classeur ELO")

        first_sheet = sheets_node[0]
        sheet_rel_id = first_sheet.attrib[f"{{{NS['r']}}}id"]
        sheet_target = rel_map[sheet_rel_id]
        rows = read_sheet_rows(zf, f"xl/{sheet_target.lstrip('/')}", shared_strings)

    if not rows:
        raise ValueError("La feuille ELO est vide")

    header = [normalize_token(value) for value in rows[0]]
    try:
        team_index = header.index("equipe")
        elo_index = header.index("elo")
    except ValueError as exc:
        raise ValueError(
            "Les colonnes Equipe et ELO sont introuvables dans le classeur ELO"
        ) from exc

    rankings: dict[str, str] = {}
    for row in rows[1:]:
        if not row or not any(value.strip() for value in row):
            continue
        if team_index >= len(row) or elo_index >= len(row):
            continue
        team_name = row[team_index].strip()
        elo_value = row[elo_index].strip()
        if elo_value:
            try:
                elo_value = str(int(float(elo_value)))
            except ValueError:
                pass
        if team_name:
            rankings[normalize_token(team_name)] = elo_value

    return rankings


def load_calendar_rows(calendar_csv: Path) -> list[dict[str, str]]:
    if not calendar_csv.exists():
        raise FileNotFoundError(f"CSV calendrier introuvable: {calendar_csv}")

    with calendar_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        headers = reader.fieldnames or []
        if headers != BASE_HEADERS:
            raise ValueError(
                "Entetes invalides dans le calendrier fusionne.\n"
                f"Attendu: {BASE_HEADERS}\n"
                f"Recu:    {headers}"
            )

        rows: list[dict[str, str]] = []
        for row in reader:
            if not row or not any((value or "").strip() for value in row.values() if value is not None):
                continue
            rows.append({key: (value or "").strip() for key, value in row.items() if key is not None})

    return rows


def enrich_calendar_rows(rows: list[dict[str, str]], rankings: dict[str, str]) -> tuple[list[dict[str, str]], set[str]]:
    seen_teams: set[str] = set()
    seeded_teams: set[str] = set()
    enriched_rows: list[dict[str, str]] = []

    for row in rows:
        enriched = {header: row.get(header, "") for header in BASE_HEADERS}
        for header in ELO_HEADERS:
            enriched[header] = ""

        if row.get("Saison") == "24-25":
            home_key = normalize_token(row.get("Domicile", ""))
            away_key = normalize_token(row.get("Exterieur", ""))

            if home_key not in seen_teams:
                if home_key not in rankings:
                    raise KeyError(f"ELO introuvable pour l'equipe domicile: {row.get('Domicile', '')}")
                enriched["ELO domicile avant match"] = rankings[home_key]
                seen_teams.add(home_key)
                seeded_teams.add(home_key)

            if away_key not in seen_teams:
                if away_key not in rankings:
                    raise KeyError(f"ELO introuvable pour l'equipe exterieur: {row.get('Exterieur', '')}")
                enriched["ELO extérieur avant match"] = rankings[away_key]
                seen_teams.add(away_key)
                seeded_teams.add(away_key)

        enriched_rows.append(enriched)

    return enriched_rows, seeded_teams


def write_enriched_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temp_csv = output_csv.with_suffix(output_csv.suffix + ".tmp")

    with temp_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    temp_csv.replace(output_csv)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    workbook_path = script_dir.parent / "donnée prof" / WORKBOOK_NAME
    input_csv = script_dir / INPUT_CSV_NAME
    output_csv = script_dir / OUTPUT_CSV_NAME

    rankings = load_elo_rankings(workbook_path)
    calendar_rows = load_calendar_rows(input_csv)
    enriched_rows, seeded_teams = enrich_calendar_rows(calendar_rows, rankings)
    write_enriched_csv(output_csv, enriched_rows)

    print(f"Fusion ELO terminee: {output_csv}")
    print(f"- Equipes initialisées en 24-25: {len(seeded_teams)}")


if __name__ == "__main__":
    main()