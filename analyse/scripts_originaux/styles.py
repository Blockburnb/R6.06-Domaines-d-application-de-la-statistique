"""
Styles d'equipes & confrontations de styles - LFB
=================================================
S1. Profil de chaque equipe-saison via le cadre canonique du basket :
    - Four Factors offensifs (Dean Oliver) : eFG%, taux de pertes (TOV%),
      taux de rebond offensif (ORB%), acces aux lancers (FTr).
    - Four Factors defensifs (ce que l'equipe IMPOSE a l'adversaire).
    - Rythme (possessions/match), dependance au 3pts, a la star.
    - Ratings : ORtg (pts pour 100 poss), DRtg (pts encaisses /100 poss).
S2. Clustering (k-means) -> archetypes de jeu.
S3. Confrontations : matrice archetype A vs archetype B (qui bat qui),
    + tests d'interaction (l'effet d'un style depend-il du style adverse ?).

Saisons completes uniquement (23-24, 24-25). Championnat.
Usage : python analyse/styles.py
Sorties: analyse/sorties_styles/*.txt et *.csv
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_styles"
os.makedirs(OUT, exist_ok=True)
COMPET = "Championat de France"
SAISONS_OK = ["23-24", "24-25"]


def sa(x):
    if not isinstance(x, str):
        return ""
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().strip()


def canon(name):
    s = sa(name)
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
# Chargement : equipe x match, avec stats de l'adversaire attachees
# ----------------------------------------------------------------------------
def charger():
    df = pd.read_csv("data/equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    num = ["Tps_jeu_decimal", "Tirs_marques", "Tirs_tentes", "3pts_marques",
           "3pts_tentes", "LF_marques", "LF_tentes", "Pts", "RO", "RD", "PD",
           "BP", "INT", "CT"]
    for c in num:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False),
                              errors="coerce")
    df = df[(df["Competition"] == COMPET) & (df["Saison"].isin(SAISONS_OK))].copy()
    df["eq"] = df["Equipe"].map(canon)
    df["adv"] = df["Adversaire"].map(canon)
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]
    t = df.groupby(keys, as_index=False)[num].sum()
    t = t.merge(df.groupby(keys, as_index=False)["Gagne_perdu"].first(), on=keys)

    # dependance a la star (part de points de la meilleure marqueuse)
    star = (df.groupby(keys)["Pts"].max() / df.groupby(keys)["Pts"].sum()
            ).rename("dep_star").reset_index()
    t = t.merge(star, on=keys)
    t["Victoire"] = t["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)

    # appariement adversaire (match_id unique en championnat)
    dom = np.where(t["dom_ext"] == "Domicile", t["eq"], t["adv"])
    ext = np.where(t["dom_ext"] == "Domicile", t["adv"], t["eq"])
    t["match_id"] = t["Saison"] + " | " + dom + " vs " + ext
    cols = num + ["Pts", "RO", "RD", "Tirs_tentes", "LF_tentes", "BP", "dep_star"]
    cols = list(dict.fromkeys(cols))  # uniques
    base = t[["match_id", "eq", "Saison", "dom_ext", "Victoire"] + cols].copy()
    opp = base.rename(columns={c: c + "_o" for c in cols}).rename(
        columns={"eq": "eq_o", "Saison": "s_o", "dom_ext": "d_o", "Victoire": "v_o"})
    m = base.merge(opp, on="match_id")
    m = m[m["eq"] != m["eq_o"]].copy()
    return m


# ----------------------------------------------------------------------------
# S1. Profil style par equipe-saison
# ----------------------------------------------------------------------------
def profils(m):
    eps = 1e-9
    g = m.groupby(["eq", "Saison"])
    a = g.agg(
        matchs=("Victoire", "size"), wr=("Victoire", "mean"),
        FGM=("Tirs_marques", "sum"), FGA=("Tirs_tentes", "sum"),
        TPM=("3pts_marques", "sum"), TPA=("3pts_tentes", "sum"),
        FTA=("LF_tentes", "sum"), PTS=("Pts", "sum"),
        ORB=("RO", "sum"), DRB=("RD", "sum"), TOV=("BP", "sum"),
        # adversaire
        oFGM=("Tirs_marques_o", "sum"), oFGA=("Tirs_tentes_o", "sum"),
        oTPM=("3pts_marques_o", "sum"),
        oFTA=("LF_tentes_o", "sum"), oPTS=("Pts_o", "sum"),
        oORB=("RO_o", "sum"), oDRB=("RD_o", "sum"), oTOV=("BP_o", "sum"),
        dep_star=("dep_star", "mean"),
    ).reset_index()

    # possessions (formule Oliver) cote equipe et cote adversaire
    a["poss"] = a["FGA"] - a["ORB"] + a["TOV"] + 0.44 * a["FTA"]
    a["opos"] = a["oFGA"] - a["oORB"] + a["oTOV"] + 0.44 * a["oFTA"]

    # ---- Four Factors OFFENSIFS ----
    a["eFG"] = (a["FGM"] + 0.5 * a["TPM"]) / (a["FGA"] + eps)
    a["TOVpct"] = a["TOV"] / (a["poss"] + eps)
    a["ORBpct"] = a["ORB"] / (a["ORB"] + a["oDRB"] + eps)
    a["FTr"] = a["FTA"] / (a["FGA"] + eps)
    # ---- Four Factors DEFENSIFS (ce qu'on impose) ----
    a["eFG_def"] = (a["oFGM"] + 0.5 * a["oTPM"]) / (a["oFGA"] + eps)
    a["TOVpct_for"] = a["oTOV"] / (a["opos"] + eps)   # pertes forcees
    a["DRBpct"] = a["DRB"] / (a["DRB"] + a["oORB"] + eps)
    # ---- style ----
    a["TPAr"] = a["TPA"] / (a["FGA"] + eps)            # part de tirs a 3pts
    a["pace"] = a["poss"] / a["matchs"]                # rythme
    # ---- ratings ----
    a["ORtg"] = 100 * a["PTS"] / (a["poss"] + eps)
    a["DRtg"] = 100 * a["oPTS"] / (a["opos"] + eps)
    a["NetRtg"] = a["ORtg"] - a["DRtg"]

    cols = ["eq", "Saison", "matchs", "wr", "eFG", "TOVpct", "ORBpct", "FTr",
            "eFG_def", "TOVpct_for", "DRBpct", "TPAr", "pace", "dep_star",
            "ORtg", "DRtg", "NetRtg"]
    a = a[cols]
    a.to_csv(f"{OUT}/profils_equipe_saison.csv", index=False)
    return a


# ----------------------------------------------------------------------------
# S2. Clustering en archetypes
# ----------------------------------------------------------------------------
def clusteriser(a, k=4):
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    feats = ["eFG", "TOVpct", "ORBpct", "FTr", "eFG_def", "TOVpct_for",
             "DRBpct", "TPAr", "pace", "dep_star"]
    X = StandardScaler().fit_transform(a[feats].values)
    km = KMeans(n_clusters=k, n_init=20, random_state=0)
    a = a.copy()
    a["cluster"] = km.fit_predict(X)

    # caracteriser chaque cluster par ses traits saillants (z-score interne)
    z = (a[feats] - a[feats].mean()) / a[feats].std()
    libelles = {}
    for c in sorted(a["cluster"].unique()):
        idx = a["cluster"] == c
        moy = z[idx].mean().sort_values(ascending=False)
        hauts = [f"{k_}(+{v:.1f})" for k_, v in moy.items() if v >= 0.6][:3]
        bas = [f"{k_}({v:.1f})" for k_, v in moy.items() if v <= -0.6][-2:]
        libelles[c] = (hauts, bas, a[idx]["wr"].mean())
    return a, libelles, feats


# ----------------------------------------------------------------------------
# S3. Confrontations de styles
# ----------------------------------------------------------------------------
def confrontations(m, a):
    f = open(f"{OUT}/confrontations.txt", "w", encoding="utf-8")
    def p(*a_): print(*a_, file=f)

    # cluster par (eq,saison)
    key = a.set_index(["eq", "Saison"])["cluster"].to_dict()
    m = m.copy()
    m["cl"] = list(zip(m["eq"], m["Saison"]))
    m["cl"] = m["cl"].map(key)
    m["cl_o"] = list(zip(m["eq_o"], m["Saison"]))
    m["cl_o"] = m["cl_o"].map(key)
    mm = m.dropna(subset=["cl", "cl_o"])

    p("=== MATRICE DE CONFRONTATION : taux de victoire archetype L vs archetype C ===\n")
    piv = mm.pivot_table(index="cl", columns="cl_o", values="Victoire",
                         aggfunc="mean")
    cnt = mm.pivot_table(index="cl", columns="cl_o", values="Victoire",
                         aggfunc="size")
    p("Taux de victoire (lignes = mon archetype, colonnes = archetype adverse) :")
    p((piv * 100).round(0).to_string())
    p("\nNombre de confrontations :")
    p(cnt.fillna(0).astype(int).to_string())
    piv.to_csv(f"{OUT}/matrice_winrate.csv")
    cnt.to_csv(f"{OUT}/matrice_n.csv")
    f.close()
    return mm


# ----------------------------------------------------------------------------
# S3b. Tests d'interaction de styles (effet conditionnel)
# ----------------------------------------------------------------------------
def interactions(m):
    """Construit le differentiel par match et teste si l'effet d'un facteur
    depend du profil adverse, via des termes d'interaction en reg. logistique."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    f = open(f"{OUT}/interactions.txt", "w", encoding="utf-8")
    def p(*a_): print(*a_, file=f)
    p("=== TESTS D'INTERACTION DE STYLES ===")
    p("Question : l'avantage tire d'un style depend-il du style adverse ?\n")

    eps = 1e-9
    d = m.copy()
    # taux par match
    d["eFG"] = (d["Tirs_marques"] + 0.5 * d["3pts_marques"]) / (d["Tirs_tentes"] + eps)
    d["TPAr"] = d["3pts_tentes"] / (d["Tirs_tentes"] + eps)
    d["pace"] = d["Tirs_tentes"] - d["RO"] + d["BP"] + 0.44 * d["LF_tentes"]
    d["press"] = d["INT"] + d["CT"]
    # cote adversaire
    d["DRB_o"] = d["RD_o"]
    d["dep_star_o"] = d["dep_star_o"]
    d["pace_o"] = d["Tirs_tentes_o"] - d["RO_o"] + d["BP_o"] + 0.44 * d["LF_tentes_o"]

    tests = [
        ("Mon adresse 3pts (3pts_marques) x rebond def. adverse",
         "3pts_marques", "DRB_o",
         "Le rebond defensif adverse annule-t-il mon adresse exterieure ?"),
        ("Mon pressing (INT) x dependance star adverse",
         "INT", "dep_star_o",
         "Le pressing est-il plus payant face a une equipe dependante d'une star ?"),
        ("Mon rythme (pace) x rythme adverse",
         "pace", "pace_o",
         "Imposer un rythme eleve face a une equipe lente, ca paie ?"),
    ]
    for titre, va, vb, q in tests:
        sub = d.dropna(subset=[va, vb, "Victoire"]).copy()
        X = sub[[va, vb]].copy()
        X["inter"] = sub[va] * sub[vb]
        Xs = StandardScaler().fit_transform(X.values)
        y = sub["Victoire"].values
        clf = LogisticRegression(max_iter=2000).fit(Xs, y)
        coef_inter = clf.coef_[0][2]
        p(f">> {titre}")
        p(f"   {q}")
        p(f"   coef interaction (standardise) = {coef_inter:+.3f}  "
          f"({'effet conditionnel notable' if abs(coef_inter) >= 0.15 else 'effet faible/nul'})")
        p("")
    p("Lecture : un coef d'interaction proche de 0 = les deux styles agissent")
    p("independamment ; non nul = l'un attenue ou amplifie l'autre.")
    f.close()


def main():
    m = charger()
    print(f"charge: {len(m)} confrontations (2 lignes/match)")

    a = profils(m)
    print(f"profils: {len(a)} equipe-saisons")

    a, lib, feats = clusteriser(a, k=4)
    a.to_csv(f"{OUT}/profils_avec_cluster.csv", index=False)

    fp = open(f"{OUT}/styles.txt", "w", encoding="utf-8")
    def p(*x): print(*x, file=fp)
    p("=== S1-S2. ARCHETYPES DE JEU (k-means, 4 groupes) ===\n")
    p("Four Factors offensifs+defensifs, rythme, 3pts, dependance star.\n")
    for c in sorted(a["cluster"].unique()):
        hauts, bas, wr = lib[c]
        membres = a[a["cluster"] == c].sort_values("wr", ascending=False)
        p(f"--- Archetype {c} (taux victoire moyen {wr*100:.0f}%) ---")
        p(f"    traits forts : {', '.join(hauts) or '-'}")
        p(f"    traits faibles: {', '.join(bas) or '-'}")
        for _, r in membres.iterrows():
            p(f"      {r['eq']:16s} {r['Saison']}  wr {r['wr']*100:3.0f}%  "
              f"NetRtg {r['NetRtg']:+5.1f}  ORtg {r['ORtg']:.0f} DRtg {r['DRtg']:.0f}")
        p("")
    fp.close()

    confrontations(m, a)
    interactions(m)

    for nm in ["styles", "confrontations", "interactions"]:
        print("\n" + "#" * 72)
        print(open(f"{OUT}/{nm}.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
