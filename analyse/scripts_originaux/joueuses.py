"""
TYPOLOGIE DES JOUEUSES (PCA + clustering) - LFB
===============================================
Objectif : regrouper les joueuses par PROFIL DE JEU (pas par niveau).
Echantillon large (~300 joueuses-saisons) -> le clustering a du sens ici.

Demarche :
  J1. Profil par joueuse-saison, en stats PAR MINUTE (neutralise le temps de jeu)
      + taille. -> decrit le ROLE, pas le volume.
  J2. PCA pour visualiser/comprendre les axes (interieur<->exterieur, etc.).
  J3. k-means (k valide par silhouette) -> archetypes de joueuses.
  J4. Description de chaque archetype + exemples + lien avec la taille/poste.

Filtre : joueuses avec assez de minutes (>= 8 matchs, >= 10 min/match) pour
que les stats par minute soient stables. Championnat, saisons 23-24 + 24-25.

Usage : python analyse/joueuses.py
Sorties: analyse/sorties_joueuses/*
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_joueuses"
os.makedirs(OUT, exist_ok=True)
COMPET = "Championat de France"
SAISONS_OK = ["23-24", "24-25"]


def sa(x):
    if not isinstance(x, str):
        return ""
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().strip()


def key_nom(s):
    return "".join(c for c in sa(s) if c.isalpha())


def _taille(x):
    if not isinstance(x, str):
        return np.nan
    return pd.to_numeric(x.lower().replace("m", ".").replace(" ", ""), errors="coerce")


def tailles():
    xl = pd.ExcelFile("donnée prof/liste joueuses multi annee.xlsm")
    fr = []
    for sh in xl.sheet_names:
        if "liste joueuses" not in sh:
            continue
        d = pd.read_excel(xl, sh, dtype=str, header=0)
        d.columns = [str(c).strip() for c in d.columns]
        sais = sh.split()[-1]
        sc = sais[2:4] + "-" + sais[7:9]
        nomcol = "Nom_condense" if "Nom_condense" in d.columns else "Nom_complet"
        fr.append(pd.DataFrame({"cle": d[nomcol].map(key_nom), "Saison": sc,
                                "taille": d["Taille"].map(_taille)}))
    return pd.concat(fr, ignore_index=True).dropna(subset=["taille"]).drop_duplicates(["cle", "Saison"])


def construire():
    df = pd.read_csv("data/equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    num = ["Tps_jeu_decimal", "Tirs_tentes", "2pts_tentes", "3pts_tentes", "3pts_marques",
           "LF_tentes", "Pts", "RO", "RD", "PD", "BP", "INT", "CT", "FPR", "EVAL"]
    for c in num:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df = df[(df["Competition"] == COMPET) & (df["Saison"].isin(SAISONS_OK))].copy()
    df = df[df["Joueur"] != "TOTAUX EQUIPE"].copy()
    df["cle"] = df["Joueur"].map(key_nom)

    g = df.groupby(["cle", "Saison"]).agg(
        matchs=("Pts", "size"), min_tot=("Tps_jeu_decimal", "sum"),
        min_moy=("Tps_jeu_decimal", "mean"),
        FGA=("Tirs_tentes", "sum"), T2A=("2pts_tentes", "sum"),
        T3A=("3pts_tentes", "sum"), T3M=("3pts_marques", "sum"),
        FTA=("LF_tentes", "sum"), PTS=("Pts", "sum"),
        RO=("RO", "sum"), RD=("RD", "sum"), PD=("PD", "sum"),
        BP=("BP", "sum"), INT=("INT", "sum"), CT=("CT", "sum"),
        FPR=("FPR", "sum"), EVAL=("EVAL", "sum")).reset_index()
    g = g[(g["matchs"] >= 8) & (g["min_moy"] >= 10)].copy()

    mn = g["min_tot"] + 1e-9
    # profil PAR MINUTE = role, pas volume
    prof = pd.DataFrame({"cle": g["cle"], "Saison": g["Saison"],
                         "matchs": g["matchs"], "min_moy": g["min_moy"]})
    prof["pts_min"] = g["PTS"] / mn
    prof["tirs_min"] = g["FGA"] / mn               # volume de tir (usage)
    prof["part_3pts"] = g["T3A"] / (g["FGA"] + 1e-9)  # exterieur vs interieur
    prof["pd_min"] = g["PD"] / mn                   # creation (meneuse)
    prof["reb_off_min"] = g["RO"] / mn              # presence raquette
    prof["reb_def_min"] = g["RD"] / mn
    prof["int_min"] = g["INT"] / mn                 # defense perimetre
    prof["ct_min"] = g["CT"] / mn                   # protection cercle (interieure)
    prof["bp_min"] = g["BP"] / mn                   # ballons portes/perdus
    prof["fta_rate"] = g["FTA"] / (g["FGA"] + 1e-9)  # agressivite/contact
    prof["eval_min"] = g["EVAL"] / mn               # niveau (pour DECRIRE, pas clusteriser)

    prof = prof.merge(tailles(), on=["cle", "Saison"], how="left")
    return prof


def main():
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    prof = construire()
    f = open(f"{OUT}/joueuses.txt", "w", encoding="utf-8")
    def p(*x): print(*x, file=f)
    p("TYPOLOGIE DES JOUEUSES - LFB (championnat 23-24 + 24-25)")
    p(f"{len(prof)} joueuses-saisons (>=8 matchs, >=10 min/match)\n")

    # variables de ROLE (par minute, hors niveau/EVAL)
    role = ["tirs_min", "part_3pts", "pd_min", "reb_off_min", "reb_def_min",
            "int_min", "ct_min", "fta_rate", "taille"]
    d = prof.dropna(subset=role).copy()
    X = StandardScaler().fit_transform(d[role].values)
    p(f"{len(d)} joueuses avec taille connue, sur {len(role)} variables de role.\n")

    # J2. PCA
    pca = PCA(n_components=4).fit(X)
    p("=== J2. AXES PRINCIPAUX (PCA) ===")
    p(f"variance expliquee : {np.round(pca.explained_variance_ratio_*100,1)} "
      f"(cumul {pca.explained_variance_ratio_[:2].sum()*100:.0f}% sur 2 axes)\n")
    comp = pd.DataFrame(pca.components_[:2].T, index=role, columns=["axe1", "axe2"])
    p("Contribution des variables aux 2 premiers axes :")
    p(comp.round(2).to_string())
    p("\n  (axe1 : ce qui oppose le + les joueuses ; axe2 : 2e opposition)\n")

    # J3. k par silhouette
    p("=== J3. NOMBRE D'ARCHETYPES (silhouette) ===")
    best_k, best_s = None, -1
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=25, random_state=0).fit(X)
        s = silhouette_score(X, km.labels_)
        p(f"   k={k} : silhouette = {s:.3f}")
        if s > best_s:
            best_k, best_s = k, s
    # on respecte la silhouette (pas de choix arbitraire)
    K = best_k
    p(f"   -> k retenu (meilleure silhouette) = {K}\n")

    km = KMeans(n_clusters=K, n_init=30, random_state=0).fit(X)
    d["arch"] = km.labels_
    z = (d[role] - d[role].mean()) / d[role].std()

    p(f"=== J4. ARCHETYPES DE JOUEUSES (k={K}) ===\n")
    noms = {}
    for c in sorted(d["arch"].unique()):
        idx = d["arch"] == c
        moy = z[idx].mean().sort_values(ascending=False)
        hauts = [f"{k_}(+{v:.1f})" for k_, v in moy.items() if v >= 0.5][:4]
        bas = [f"{k_}({v:.1f})" for k_, v in moy.items() if v <= -0.5][-3:]
        taille_moy = d[idx]["taille"].mean()
        eval_moy = d[idx]["eval_min"].mean()
        p(f"--- Archetype {c}  (n={idx.sum()}, taille moy {taille_moy:.2f}m, "
          f"impact/min {eval_moy:.2f}) ---")
        p(f"    marqueurs +: {', '.join(hauts) or '-'}")
        p(f"    marqueurs -: {', '.join(bas) or '-'}")
        # 5 exemples les plus representatifs (impact eleve)
        ex = d[idx].sort_values("eval_min", ascending=False).head(6)
        noms_ex = ", ".join(f"{r['cle']}({r['Saison']})" for _, r in ex.iterrows())
        p(f"    exemples (fort impact): {noms_ex}")
        p("")

    d.to_csv(f"{OUT}/joueuses_archetypes.csv", index=False)
    p("Lecture : les archetypes opposent surtout INTERIEURES (taille, contres,")
    p("rebonds, lancers) <-> EXTERIEURES (3pts, passes, interceptions). Le role est")
    p("independant du niveau (impact/min varie a l'interieur de chaque groupe).")
    f.close()
    print(open(f"{OUT}/joueuses.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
