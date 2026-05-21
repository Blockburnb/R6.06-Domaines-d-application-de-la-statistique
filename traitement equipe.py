from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ROOT = Path(".").resolve()
OUTPUT_DIR = ROOT / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Chemin modèle fourni
MODEL_REL = Path("donnée prof") / "Fichier Equipe" / "Toulouse.csv"
MODEL_PATH = (ROOT / MODEL_REL).resolve()

# Si le chemin exact n'existe pas, on tente une recherche récursive de "Toulouse.csv"
if not MODEL_PATH.exists():
    logging.warning(f"Modèle non trouvé à {MODEL_PATH}. Recherche récursive de 'Toulouse.csv'...")
    candidates = list(ROOT.rglob("Toulouse.csv"))
    MODEL_PATH = candidates[0].resolve() if candidates else None

if not MODEL_PATH or not Path(MODEL_PATH).exists():
    logging.error("Fichier modèle 'Toulouse.csv' introuvable. Placez-le dans 'donnée prof\\Fichier Equipe\\Toulouse.csv' ou à la racine puis relancez.")
    raise SystemExit(1)

logging.info(f"Modèle utilisé : {MODEL_PATH}")

def read_csv_try(path):
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    raise

template = read_csv_try(MODEL_PATH)
template_cols = [c.strip() for c in template.columns]
template_lower_map = {c.lower(): c for c in template_cols}

# Tous les CSV du projet sauf le modèle et le futur combined.csv
all_csvs = [p for p in ROOT.rglob("*.csv")]
all_csvs = [p for p in all_csvs if p.resolve() != Path(MODEL_PATH).resolve()]
all_csvs = [p for p in all_csvs if p.name.lower() != "combined.csv"]

if not all_csvs:
    logging.warning("Aucun CSV trouvé à combiner.")
    raise SystemExit(0)

frames = []
for p in sorted(all_csvs):
    try:
        logging.info(f"Lecture : {p}")
        df = read_csv_try(p)
    except Exception as e:
        logging.warning(f"Impossible de lire {p}: {e}. Ignoré.")
        continue

    # Alignement des colonnes par correspondance insensible à la casse et suppression d'espaces
    df_cols_lower = {c.lower().strip(): c for c in df.columns}
    aligned = {}
    for tmpl_lower, tmpl_orig in template_lower_map.items():
        if tmpl_lower in df_cols_lower:
            aligned[tmpl_orig] = df[df_cols_lower[tmpl_lower]]
        else:
            aligned[tmpl_orig] = pd.NA

    aligned_df = pd.DataFrame(aligned, index=df.index)
    # ajout de la colonne 'team' avec le nom du fichier (sans extension)
    aligned_df["team"] = p.stem
    frames.append(aligned_df)

if not frames:
    logging.error("Aucune donnée importée après traitement.")
    raise SystemExit(1)

combined = pd.concat(frames, ignore_index=True)
out_path = OUTPUT_DIR / "combined.csv"
combined.to_csv(out_path, index=False, encoding="utf-8")
logging.info(f"Fichier combiné écrit : {out_path} (lignes: {len(combined)})")