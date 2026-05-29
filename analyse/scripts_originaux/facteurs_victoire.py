"""
Data mining : quels facteurs pesent le plus pour gagner un match (LFB) ?

Demarche
--------
1. equipes_fusionnees.csv = 1 ligne par JOUEUSE x match.
2. Agregation au niveau EQUIPE x match (somme des stats des joueuses).
3. Indicateurs avances (eFG%, taux de pertes, apport du banc, dependance star...).
4. Reconstruction de chaque match en DIFFERENTIEL equipe - adversaire :
   un facteur ne fait gagner que s'il est meilleur que celui d'en face.
5. Trois lectures complementaires de l'importance des facteurs :
     A. UNIVARIE   : chaque facteur seul -> effet "+1 ecart-type => +X%" + AUC.
                     (interpretable, insensible a la colinearite)
     B. MULTIVARIE : regression logistique sur un jeu de facteurs NON redondants
                     -> coefficients aux signes coherents.
     C. RANDOM FOREST : importance non lineaire, en contre-verification.
6. Profil de style par equipe (descriptif).

Usage  : python analyse/facteurs_victoire.py
Sorties: analyse/sorties/*.csv  et  *.png
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SRC = "data/equipes_fusionnees.csv"
OUT = "analyse/sorties"
os.makedirs(OUT, exist_ok=True)

COMPET = "Championat de France"   # orthographe d'origine dans les donnees (sic)

# Libelles lisibles pour l'affichage
LABELS = {
    "d_eFG": "Efficacite au tir (eFG%)",
    "d_pct_tirs": "% de tirs reussis",
    "d_pct_3pts": "% a 3 points",
    "d_taux_pertes": "Taux de pertes de balle",
    "d_RD": "Rebonds defensifs",
    "d_RO": "Rebonds offensifs",
    "d_RT": "Rebonds totaux",
    "d_PD": "Passes decisives",
    "d_pression_def": "Pression def. (INT+CT)",
    "d_INT": "Interceptions",
    "d_CT": "Contres",
    "d_pts_par_poss": "Points par possession",
    "d_ratio_pd_bp": "Ratio passes/pertes",
    "d_part_3pts": "Part de tirs a 3pts (style)",
    "d_part_banc": "Apport du banc (style)",
    "d_dep_star": "Dependance a la star (style)",
    "d_profondeur_rotation": "Profondeur de rotation",
    "domicile": "Avantage du terrain",
}


def canon(name):
    """Nom d'equipe canonique : colonnes Equipe et Adversaire ont des libelles
    differents (Lyon vs Lyon Asvel Feminin, Montpellier vs Lattes Montpellier...)."""
    if not isinstance(name, str):
        return name
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
    for cle, val in [
        ("angers", "angers"), ("landes", "basket landes"), ("bourges", "bourges"),
        ("charleville", "charleville"), ("chartres", "chartres"), ("charnay", "charnay"),
        ("landerneau", "landerneau"), ("lyon", "lyon"), ("montpellier", "montpellier"),
        ("lattes", "montpellier"), ("roche", "roche vendee"), ("toulouse", "toulouse"),
        ("ascq", "villeneuve ascq"), ("villeneuve", "villeneuve ascq"),
        ("saint-amand", "saint-amand"), ("strasbourg", "strasbourg"), ("tarbes", "tarbes"),
    ]:
        if cle in s:
            return val
    return s


# ----------------------------------------------------------------------------
# 1-2. Chargement + agregation joueuse -> equipe x match
# ----------------------------------------------------------------------------
def charger_et_agreger():
    df = pd.read_csv(SRC, sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    num_cols = ["Tps_jeu_decimal", "Tirs_marques", "Tirs_tentes",
                "2pts_marques", "2pts_tentes", "3pts_marques", "3pts_tentes",
                "LF_marques", "LF_tentes", "Points_banc", "Pts",
                "RO", "RD", "RT", "PD", "BP", "INT", "CT", "CTS", "F", "FPR"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False),
                              errors="coerce")

    df = df[df["Competition"] == COMPET].copy()
    df["eq"] = df["Equipe"].map(canon)
    df["adv"] = df["Adversaire"].map(canon)
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]

    agg = df.groupby(keys, as_index=False)[num_cols].sum()
    agg = agg.merge(df.groupby(keys, as_index=False)["Gagne_perdu"].first(), on=keys)

    star = (df.groupby(keys)["Pts"].max() /
            df.groupby(keys)["Pts"].sum()).rename("dep_star").reset_index()
    agg = agg.merge(star, on=keys)

    rot = (df[df["Tps_jeu_decimal"] > 10].groupby(keys).size()
           .rename("profondeur_rotation").reset_index())
    agg = agg.merge(rot, on=keys, how="left")
    agg["profondeur_rotation"] = agg["profondeur_rotation"].fillna(0)

    agg["Victoire"] = agg["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)
    return agg


def construire_indicateurs(t):
    eps = 1e-9
    t["possessions"] = t["Tirs_tentes"] - t["RO"] + t["BP"] + 0.44 * t["LF_tentes"]
    t["eFG"] = (t["Tirs_marques"] + 0.5 * t["3pts_marques"]) / (t["Tirs_tentes"] + eps)
    t["pct_tirs"] = t["Tirs_marques"] / (t["Tirs_tentes"] + eps)
    t["pct_3pts"] = t["3pts_marques"] / (t["3pts_tentes"] + eps)
    t["part_3pts"] = t["3pts_tentes"] / (t["Tirs_tentes"] + eps)
    t["pts_par_poss"] = t["Pts"] / (t["possessions"] + eps)
    t["taux_pertes"] = t["BP"] / (t["possessions"] + eps)       # pertes pour 1 possession
    t["ratio_pd_bp"] = t["PD"] / (t["BP"] + eps)
    t["pression_def"] = t["INT"] + t["CT"]
    t["part_banc"] = t["Points_banc"] / (t["Pts"] + eps)
    return t


# ----------------------------------------------------------------------------
# 4. Differentiel equipe - adversaire
# ----------------------------------------------------------------------------
def construire_differentiel(t):
    dom = np.where(t["dom_ext"] == "Domicile", t["eq"], t["adv"])
    ext = np.where(t["dom_ext"] == "Domicile", t["adv"], t["eq"])
    t["match_id"] = t["Saison"] + " | " + dom + " vs " + ext   # unique en championnat

    stats = ["eFG", "pct_tirs", "pct_3pts", "part_3pts", "pts_par_poss",
             "taux_pertes", "ratio_pd_bp", "RO", "RD", "RT", "PD",
             "INT", "CT", "pression_def", "part_banc", "dep_star",
             "profondeur_rotation"]
    base = t[["match_id", "eq", "dom_ext", "Victoire"] + stats].copy()
    opp = base.rename(columns={c: c + "_opp" for c in stats}).rename(
        columns={"eq": "eq_opp", "dom_ext": "d2", "Victoire": "v2"})
    m = base.merge(opp, on="match_id")
    m = m[m["eq"] != m["eq_opp"]].copy()
    for c in stats:
        m["d_" + c] = m[c] - m[c + "_opp"]
    m["domicile"] = (m["dom_ext"] == "Domicile").astype(int)
    return m, ["d_" + c for c in stats]


# ----------------------------------------------------------------------------
# 5A. Importance UNIVARIEE (chaque facteur seul)
# ----------------------------------------------------------------------------
def importance_univariee(m, cols):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    y = m["Victoire"].values
    lignes = []
    for c in cols + ["domicile"]:
        d = m.dropna(subset=[c])
        x = d[[c]].values
        yy = d["Victoire"].values
        if c == "domicile":
            xs = x.astype(float)
        else:
            xs = StandardScaler().fit_transform(x)
        clf = LogisticRegression(max_iter=2000).fit(xs, yy)
        coef = clf.coef_[0][0]
        auc = roc_auc_score(yy, clf.predict_proba(xs)[:, 1])
        lignes.append({
            "facteur": LABELS.get(c, c), "code": c,
            "coef_std": coef,
            "effet_proba_pct_a_50": coef * 0.25 * 100,
            "auc_seul": auc,
            "importance": abs(coef),
        })
    return (pd.DataFrame(lignes)
            .sort_values("importance", ascending=False).reset_index(drop=True))


# ----------------------------------------------------------------------------
# 5B. Modele MULTIVARIE sur facteurs NON redondants
# ----------------------------------------------------------------------------
def modele_multivarie(m):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    # un seul representant par concept -> signes interpretables
    feats = ["d_eFG", "d_pct_3pts", "d_taux_pertes", "d_RD", "d_RO",
             "d_PD", "d_pression_def", "domicile"]
    d = m.dropna(subset=feats + ["Victoire"]).copy()
    X = StandardScaler().fit_transform(d[feats].values)
    y = d["Victoire"].values
    clf = LogisticRegression(max_iter=2000).fit(X, y)
    res = pd.DataFrame({
        "facteur": [LABELS.get(f, f) for f in feats],
        "code": feats,
        "coef_std": clf.coef_[0],
        "odds_ratio": np.exp(clf.coef_[0]),
        "effet_proba_pct_a_50": clf.coef_[0] * 0.25 * 100,
        "importance": np.abs(clf.coef_[0]),
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    auc = cross_val_score(clf, X, y, cv=5, scoring="roc_auc").mean()
    acc = cross_val_score(clf, X, y, cv=5, scoring="accuracy").mean()
    return res, auc, acc, len(d)


# ----------------------------------------------------------------------------
# 5C. Random Forest (contre-verification non lineaire)
# ----------------------------------------------------------------------------
def importance_rf(m, cols):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    feats = cols + ["domicile"]
    d = m.dropna(subset=feats + ["Victoire"]).copy()
    X, y = d[feats].values, d["Victoire"].values
    rf = RandomForestClassifier(n_estimators=400, max_depth=6,
                                min_samples_leaf=5, random_state=0)
    rf.fit(X, y)
    auc = cross_val_score(rf, X, y, cv=5, scoring="roc_auc").mean()
    res = pd.DataFrame({
        "facteur": [LABELS.get(f, f) for f in feats],
        "code": feats,
        "importance_rf": rf.feature_importances_,
    }).sort_values("importance_rf", ascending=False).reset_index(drop=True)
    return res, auc


# ----------------------------------------------------------------------------
# 6. Profil de style par equipe
# ----------------------------------------------------------------------------
def profil_equipes(t):
    style = ["eFG", "pct_3pts", "part_3pts", "pts_par_poss", "taux_pertes",
             "RO", "RD", "PD", "INT", "CT", "pression_def", "part_banc",
             "dep_star", "profondeur_rotation"]
    prof = t.groupby("eq")[style].mean()
    z = (prof - prof.mean()) / prof.std()
    return prof, z


def main():
    print("=" * 72)
    print("FACTEURS DE VICTOIRE - LFB (championnat)")
    print("=" * 72)

    t = construire_indicateurs(charger_et_agreger())
    print(f"\n{len(t)} obs equipe x match ({t['Victoire'].sum()} victoires)")
    m, diff_cols = construire_differentiel(t)
    print(f"{len(m)} matchs apparies equipe-vs-adversaire")

    # facteurs "de jeu" pour l'univarie/RF (on exclut pts_par_poss ~ le score brut,
    # et RT redondant avec RO+RD)
    jeu = [c for c in diff_cols if c not in ("d_pts_par_poss", "d_RT")]

    uni = importance_univariee(m, jeu)
    uni.to_csv(f"{OUT}/importance_univariee.csv", index=False)
    print("\n--- A. IMPORTANCE UNIVARIEE (chaque facteur seul) ---")
    print("effet = +pts de proba de victoire pour +1 ecart-type d'avantage / adversaire")
    print(uni[["facteur", "effet_proba_pct_a_50", "auc_seul"]]
          .round(2).to_string(index=False))

    multi, auc_m, acc_m, n = modele_multivarie(m)
    multi.to_csv(f"{OUT}/modele_multivarie.csv", index=False)
    print(f"\n--- B. MODELE MULTIVARIE (facteurs non redondants) ---")
    print(f"{n} matchs | AUC={auc_m:.3f} | accuracy={acc_m:.3f} (CV 5-fold)")
    print(multi[["facteur", "coef_std", "odds_ratio", "effet_proba_pct_a_50"]]
          .round(3).to_string(index=False))

    rf, auc_rf = importance_rf(m, jeu)
    rf.to_csv(f"{OUT}/importance_rf.csv", index=False)
    print(f"\n--- C. RANDOM FOREST (contre-verification) | AUC={auc_rf:.3f} ---")
    print(rf.head(10)[["facteur", "importance_rf"]].round(3).to_string(index=False))

    prof, z = profil_equipes(t)
    prof.round(3).to_csv(f"{OUT}/profil_equipes.csv")
    z.round(2).to_csv(f"{OUT}/profil_equipes_zscore.csv")
    print("\n--- STYLE PAR EQUIPE (z-score vs ligue ; |z|>=1 = se demarque) ---")
    for eq in z.index:
        s = z.loc[eq].sort_values(ascending=False)
        plus = [f"{k}(+{v:.1f})" for k, v in s.items() if v >= 1][:3]
        moins = [f"{k}({v:.1f})" for k, v in s.items() if v <= -1][-3:]
        print(f"  {eq:16s} +: {', '.join(plus) or '-':40s} -: {', '.join(moins) or '-'}")

    # graphique : univarie (top 12)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        top = uni.head(12).iloc[::-1]
        plt.figure(figsize=(9, 6))
        col = ["#2c7fb8" if v > 0 else "#cb4b16" for v in top["effet_proba_pct_a_50"]]
        plt.barh(top["facteur"], top["effet_proba_pct_a_50"], color=col)
        plt.axvline(0, color="black", lw=0.8)
        plt.title("Facteurs de victoire LFB - effet univarie\n"
                  "(+pts de proba pour +1 ecart-type d'avantage sur l'adversaire)")
        plt.xlabel("<- defaite        victoire ->")
        plt.tight_layout()
        plt.savefig(f"{OUT}/facteurs_victoire.png", dpi=130)
        print(f"\nGraphique : {OUT}/facteurs_victoire.png")
    except Exception as e:
        print("graph non genere:", e)

    print(f"\nCSV ecrits dans {OUT}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
