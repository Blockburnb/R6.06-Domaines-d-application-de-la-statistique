#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


WORKBOOK_NAME = "Calendrier et resultat.xlsx"
OUTPUT_NAME = "calendrier_resultat_fusionne.csv"

OUTPUT_HEADERS = [
    "Saison",
    "Journee",
    "Domicile",
    "Exterieur",
    "Score domicile",
    "Score Exterieur",
    "Derby",
]

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip().casefold().replace(" ", "")


def column_index_from_ref(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref or "")
    if not letters:
        return 0

    index = 0
    for char in letters.group(0):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index


def extract_sheet_season(sheet_name: str) -> str:
    match = re.search(r"(\d{2}-\d{2})", sheet_name)
    if not match:
        raise ValueError(f"Impossible de determiner la saison depuis la feuille: {sheet_name}")
    return match.group(1)


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("a:si", NS):
        parts = [node.text or "" for node in item.iterfind(".//a:t", NS)]
        shared_strings.append("".join(parts))
    return shared_strings


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        text_node = cell.find("a:is/a:t", NS)
        return (text_node.text or "") if text_node is not None else ""

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


def merge_calendar_workbook(workbook_path: Path, output_csv: Path) -> None:
    if not workbook_path.exists():
        raise FileNotFoundError(f"Classeur introuvable: {workbook_path}")

    with zipfile.ZipFile(workbook_path) as zf:
        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}
        shared_strings = load_shared_strings(zf)

        output_csv.parent.mkdir(parents=True, exist_ok=True)

        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS, delimiter=";")
            writer.writeheader()

            sheets_node = workbook_root.find("a:sheets", NS)
            if sheets_node is None:
                raise ValueError("Aucune feuille trouvee dans le classeur")

            for sheet in sheets_node:
                sheet_name = sheet.attrib["name"]
                sheet_rel_id = sheet.attrib[f"{{{NS['r']}}}id"]
                sheet_target = rel_map[sheet_rel_id]
                sheet_path = f"xl/{sheet_target.lstrip('/')}"
                season = extract_sheet_season(sheet_name)

                rows = read_sheet_rows(zf, sheet_path, shared_strings)
                if not rows:
                    continue

                header_row = [normalize_text(value) for value in rows[0]]
                header_index = {name: idx for idx, name in enumerate(header_row)}

                required = {
                    "journee": "Journee",
                    "domicile": "Domicile",
                    "exterieur": "Exterieur",
                    "scoredomicile": "Score domicile",
                    "scoreexterieur": "Score Exterieur",
                    "derby": "Derby",
                }

                missing = [label for label in required if label not in header_index]
                if missing:
                    raise ValueError(
                        f"Entetes manquantes dans la feuille {sheet_name}: {', '.join(missing)}"
                    )

                for raw_row in rows[1:]:
                    if not raw_row or not any(value.strip() for value in raw_row):
                        continue

                    output_row = {
                        "Saison": season,
                        "Journee": raw_row[header_index["journee"]] if header_index["journee"] < len(raw_row) else "",
                        "Domicile": raw_row[header_index["domicile"]] if header_index["domicile"] < len(raw_row) else "",
                        "Exterieur": raw_row[header_index["exterieur"]] if header_index["exterieur"] < len(raw_row) else "",
                        "Score domicile": raw_row[header_index["scoredomicile"]] if header_index["scoredomicile"] < len(raw_row) else "",
                        "Score Exterieur": raw_row[header_index["scoreexterieur"]] if header_index["scoreexterieur"] < len(raw_row) else "",
                        "Derby": raw_row[header_index["derby"]] if header_index["derby"] < len(raw_row) else "",
                    }
                    writer.writerow(output_row)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    workbook_path = script_dir.parent / "donnée prof" / WORKBOOK_NAME
    output_csv = script_dir / OUTPUT_NAME

    merge_calendar_workbook(workbook_path, output_csv)
    print(f"Fusion terminee: {output_csv}")


if __name__ == "__main__":
    main()