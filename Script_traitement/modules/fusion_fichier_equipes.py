#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

# Entetes cibles dans l'ordre demande.
OUTPUT_HEADERS = [
    "Equipe",
    "Saison",
    "Num_match",
    "Competition",
    "dom_ext",
    "Gagne_perdu",
    "Adversaire",
    "Capitaine",
    "Starter/bench",
    "Joueur",
    "Minutes",
    "Secondes",
    "Secondes(minutes)",
    "Tps_jeu_decimal",
    "Tirs_marques",
    "Tirs_tentes",
    "%Tirs",
    "2pts_marques",
    "2pts_tentes",
    "%2pts",
    "3pts_marques",
    "3pts_tentes",
    "%3pts",
    "LF_marques",
    "LF_tentes",
    "%LF",
    "Pts_apres_balles_perdues",
    "Points_int",
    "Point_2eme_chance",
    "Points_CA",
    "Points_banc",
    "Ecart_max",
    "Serie_max",
    "Pts",
    "RO",
    "RD",
    "RT",
    "PD",
    "BP",
    "INT",
    "CT",
    "CTS",
    "F",
    "FPR",
    "+/-",
    "EVAL",
    "N ",
    "JOUEUR",
]

# Synonymes connus dans les fichiers source.
HEADER_ALIASES = {
    "Adveresaire": "Adversaire",
    "Adversaire": "Adversaire",
    "N\u00b0": "N ",
    "N\ufffd": "N ",
    "N": "N ",
}


def normalize_header(name: str) -> str:
    clean = (name or "").strip()
    return HEADER_ALIASES.get(clean, clean)


def open_csv_with_fallback(csv_path: Path):
    encodings = ["utf-8-sig", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            handle = csv_path.open("r", encoding=enc, newline="")
            # On force une lecture minimale pour valider le decodage.
            handle.read(2048)
            handle.seek(0)
            return handle
        except UnicodeDecodeError:
            handle.close()
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Impossible de lire {csv_path}")


def build_output_row(raw_row: dict[str, str], team_name: str) -> dict[str, str]:
    normalized_row = {}
    for key, value in raw_row.items():
        if key is None:
            continue
        normalized_key = normalize_header(key)
        normalized_row[normalized_key] = (value or "").strip()

    output = {header: "" for header in OUTPUT_HEADERS}
    output["Equipe"] = team_name
    for header in OUTPUT_HEADERS:
        if header == "Equipe":
            continue
        output[header] = normalized_row.get(header, "")
    return output


def merge_team_csvs(source_dir: Path, output_csv: Path) -> None:
    csv_files = sorted(source_dir.glob("*.csv"), key=lambda p: p.name.lower())
    if not csv_files:
        raise FileNotFoundError(f"Aucun CSV trouve dans {source_dir}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as out_handle:
        writer = csv.DictWriter(out_handle, fieldnames=OUTPUT_HEADERS, delimiter=";")
        writer.writeheader()

        for csv_file in csv_files:
            team_name = csv_file.stem
            with open_csv_with_fallback(csv_file) as in_handle:
                reader = csv.DictReader(in_handle, delimiter=";")
                for row in reader:
                    # Ignore les lignes totalement vides.
                    if not row or not any((val or "").strip() for val in row.values() if val is not None):
                        continue
                    writer.writerow(build_output_row(row, team_name))


def main(output_path: Path) -> None:
    source_dir = Path(__file__).resolve().parent.parent.parent / "donnée prof" / "Fichier Equipe"
    merge_team_csvs(source_dir, output_path)
    print(f"[modules/fusion_fichier_equipes.py] Fusion terminee: {output_path}")


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent.parent
    output_csv = script_dir / "data_intermediaire" / "equipes_fusionnees.csv"
    main(output_csv)
