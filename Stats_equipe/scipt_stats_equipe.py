from pathlib import Path
import pandas as pd

def main():
    repo_root = Path(__file__).resolve().parent.parent
    csv_path = repo_root / "data" / "equipes_fusionnees.csv"
    out_path = Path(__file__).resolve().parent / "stats_par_equipe.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {csv_path}")

    df = pd.read_csv(csv_path, sep=";", decimal=",", encoding="utf-8", na_values=["", "NA"])
    df.columns = [c.strip() for c in df.columns]

    # noms des colonnes souhaitées
    desired = {"%Tirs": "%Tirs", "PD": "PD", "BP": "BP", "3pts_marques": "3pts_marques"}

    # détecter lignes "TOTAUX EQUIPE"
    joueur_col = next((c for c in ("JOUEUR", "Joueur") if c in df.columns), None)
    if joueur_col:
        totals_mask = df[joueur_col].astype(str).str.strip().str.upper() == "TOTAUX EQUIPE"
    else:
        totals_mask = df.isin(["TOTAUX EQUIPE"]).any(axis=1)
    totals = df[totals_mask].copy()

    def ensure_numeric(frame, cols):
        for c in cols:
            if c in frame.columns:
                frame[c] = pd.to_numeric(frame[c], errors="coerce")
        return frame

    if not totals.empty:
        # utiliser TOTAUX EQUIPE (déjà par match) et calculer moyenne des colonnes choisies
        totals = ensure_numeric(totals, list(desired.values()))
        # n_matchs = nombre de totaux par équipe
        n_matchs = totals.groupby("Equipe").size().rename("n_matchs")
        means = totals.groupby("Equipe")[[c for c in desired.values() if c in totals.columns]].mean()
    else:
        # pas de totaux : agréger par Equipe+Num_match à partir des lignes joueurs
        if "Equipe" not in df.columns or "Num_match" not in df.columns:
            raise KeyError("Colonnes 'Equipe' et 'Num_match' requises pour l'agrégation.")
        # forcer conversion numérique pour colonnes demandées
        df = ensure_numeric(df, list(desired.values()))
        per_match = df.groupby(["Equipe", "Num_match"], dropna=False)[[c for c in desired.values() if c in df.columns]].sum()
        n_matchs = per_match.groupby(level=0).size().rename("n_matchs")
        means = per_match.groupby(level=0).mean()

    # construire tableau final : garder n_matchs + moyennes (renommer colonnes avec suffixe _mean)
    if means.empty:
        # créer colonnes vides si manquantes
        means = pd.DataFrame(index=n_matchs.index)

    out = pd.concat([n_matchs, means], axis=1).reset_index().rename(columns={"index": "Equipe"})
    # renommer colonnes pour indiquer moyenne
    for col in list(means.columns):
        out = out.rename(columns={col: f"{col}_mean"})

    # s'assurer que toutes les colonnes demandées sont présentes (même si absentes dans les données)
    for src in desired.values():
        cname = f"{src}_mean"
        if cname not in out.columns:
            out[cname] = pd.NA

    # ordre des colonnes
    cols_order = ["Equipe", "n_matchs"] + [f"{src}_mean" for src in desired.values()]
    out = out[cols_order]

    out.to_csv(out_path, index=False, sep=";", decimal=",", encoding="utf-8")
    print(f"Stats simplifiées par équipe écrites dans : {out_path} ({out.shape[0]} équipes)")

if __name__ == "__main__":
    main()