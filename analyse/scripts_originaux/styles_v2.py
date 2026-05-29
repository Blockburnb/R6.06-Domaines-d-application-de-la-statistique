"""
STYLE DE JEU (v2) - corrige les defauts de la v1
=================================================
Critique de la v1 : elle clusterisait sur eFG/rebond = des mesures de QUALITE,
donc "les forts vs les faibles". Ici on separe explicitement :

  NIVEAU  = a quel point une equipe est forte  (NetRtg, ELO)  -> on le CONTROLE
  STYLE   = COMMENT elle joue, independamment du niveau         -> on le MESURE

Variables de STYLE (idealement non correlees au niveau) :
  - pct_raquette   : part des points marques dans la raquette (jeu interieur)
  - pct_3pts_pts   : part des points venant du 3pts
  - pct_CA         : part des points en contre-attaque (jeu rapide)
  - pct_2e_chance  : part des points de seconde chance (rebond offensif)
  - pct_banc       : part des points du banc (profondeur)
  - pace           : possessions/match (rythme)
  - taille_moy     : taille moyenne ponderee par les minutes (grand vs petit)
  - dep_star       : concentration sur la meilleure marqueuse
  - gambling_def   : interceptions / possessions adverses (defense agressive)

Demarche :
  E1. Construire ces variables par equipe-saison.
  E2. VERIFIER qu'elles sont peu liees au niveau (corr avec NetRtg).
       -> on garde comme "style pur" celles a |r| faible.
  E3. Choisir k par silhouette (pas arbitraire). Clusteriser sur le style pur.
  E4. TEST DECISIF : a ecart d'ELO controle, le style ajoute-t-il de la
       prediction ? (regression hierarchique : ELO seul vs ELO + style).

Usage : python analyse/styles_v2.py
Sorties: analyse/sorties_styles_v2/*
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_styles_v2"
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


def _taille(x):
    if not isinstance(x, str):
        return np.nan
    return pd.to_numeric(x.lower().replace("m", ".").replace(" ", ""), errors="coerce")


# ----------------------------------------------------------------------------
# Tailles moyennes ponderees par les minutes (depuis liste joueuses + minutes)
# ----------------------------------------------------------------------------
def tailles_par_equipe():
    xl = pd.ExcelFile("donnée prof/liste joueuses multi annee.xlsm")
    frames = []
    for sh in xl.sheet_names:
        if "liste joueuses" not in sh:
            continue
        d = pd.read_excel(xl, sh, dtype=str, header=0)
        d.columns = [str(c).strip() for c in d.columns]
        sais = sh.split()[-1]
        sc = sais[2:4] + "-" + sais[7:9]
        key = lambda s: "".join(c for c in sa(s) if c.isalpha())
        nomcol = "Nom_condense" if "Nom_condense" in d.columns else "Nom_complet"
        frames.append(pd.DataFrame({
            "cle": d[nomcol].map(key), "Saison": sc,
            "taille": d["Taille"].map(_taille)}))
    return pd.concat(frames, ignore_index=True).dropna(subset=["taille"])


# ----------------------------------------------------------------------------
# E1. Variables de style par equipe-saison
# ----------------------------------------------------------------------------
def construire(m_dummy=None):
    df = pd.read_csv("data/equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    numbase = ["Tps_jeu_decimal", "Tirs_tentes", "3pts_tentes", "3pts_marques",
               "LF_tentes", "Pts", "RO", "RD", "BP", "INT"]
    for c in numbase:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False),
                              errors="coerce")
    df = df[(df["Competition"] == COMPET) & (df["Saison"].isin(SAISONS_OK))].copy()
    df["eq"] = df["Equipe"].map(canon)
    df["adv"] = df["Adversaire"].map(canon)

    # --- taille moyenne ponderee minutes (joueuses, hors ligne TOTAUX) ---
    tj = df[df["Joueur"] != "TOTAUX EQUIPE"].copy()
    tj["cle"] = tj["Joueur"].map(lambda s: "".join(c for c in sa(s) if c.isalpha()))
    tail = tailles_par_equipe()
    tj = tj.merge(tail, on=["cle", "Saison"], how="left")
    tj["mt"] = tj["Tps_jeu_decimal"] * tj["taille"]
    th = tj.groupby(["eq", "Saison"]).apply(
        lambda g: g["mt"].sum() / g.loc[g["taille"].notna(), "Tps_jeu_decimal"].sum()
    ).rename("taille_moy").reset_index()

    # --- repartition des points : ligne TOTAUX EQUIPE ---
    tot = df[df["Joueur"] == "TOTAUX EQUIPE"].copy()
    for c in ["Points_int", "Point_2eme_chance", "Points_CA", "Points_banc"]:
        tot[c] = pd.to_numeric(tot[c].astype(str).str.replace(",", ".", regex=False),
                               errors="coerce")
    rep = tot.groupby(["eq", "Saison"]).agg(
        PTS=("Pts", "sum"), Pint=("Points_int", "sum"),
        P2c=("Point_2eme_chance", "sum"), PCA=("Points_CA", "sum"),
        Pbanc=("Points_banc", "sum")).reset_index()

    # --- volumes pour pace / 3pts / gambling / dep_star (toutes lignes joueuses) ---
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]
    tm = df[df["Joueur"] != "TOTAUX EQUIPE"].groupby(keys, as_index=False).agg(
        FGA=("Tirs_tentes", "sum"), TPA=("3pts_tentes", "sum"),
        FTA=("LF_tentes", "sum"), RO=("RO", "sum"), BP=("BP", "sum"),
        INT=("INT", "sum"), PTS=("Pts", "sum"))
    star = (df[df["Joueur"] != "TOTAUX EQUIPE"].groupby(keys)["Pts"].max() /
            df[df["Joueur"] != "TOTAUX EQUIPE"].groupby(keys)["Pts"].sum()
            ).rename("dep").reset_index()
    tm = tm.merge(star, on=keys)
    tm["poss"] = tm["FGA"] - tm["RO"] + tm["BP"] + 0.44 * tm["FTA"]
    # resultat du match
    res = df[df["Joueur"] != "TOTAUX EQUIPE"].groupby(keys)["Gagne_perdu"].first().reset_index()
    res["v"] = res["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)
    tm = tm.merge(res, on=keys)

    agg = tm.groupby(["eq", "Saison"]).agg(
        matchs=("v", "size"), wr=("v", "mean"),
        FGA=("FGA", "sum"), TPA=("TPA", "sum"), poss=("poss", "sum"),
        INT=("INT", "sum"), dep_star=("dep", "mean"),
        pace=("poss", "mean")).reset_index()

    a = (agg.merge(rep, on=["eq", "Saison"]).merge(th, on=["eq", "Saison"]))
    eps = 1e-9
    a["pct_raquette"] = a["Pint"] / (a["PTS"] + eps)
    # part des points venant du 3pts : 3 * 3pts_marques / Pts
    df["3pts_marques"] = pd.to_numeric(
        df["3pts_marques"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    tpm = df[df["Joueur"] != "TOTAUX EQUIPE"].groupby(["eq", "Saison"])["3pts_marques"].sum()
    a = a.merge(tpm.rename("TPM").reset_index(), on=["eq", "Saison"])
    a["pct_3pts_pts"] = 3 * a["TPM"] / (a["PTS"] + eps)
    a["pct_CA"] = a["PCA"] / (a["PTS"] + eps)
    a["pct_2e_chance"] = a["P2c"] / (a["PTS"] + eps)
    a["pct_banc"] = a["Pbanc"] / (a["PTS"] + eps)
    a["part_3pts_tirs"] = a["TPA"] / (a["FGA"] + eps)
    a["gambling_def"] = a["INT"] / (a["poss"] + eps)
    return a


def pd_safe(a, col):
    return a[col] if col in a.columns else 0


def main():
    a = construire()
    print(f"{len(a)} equipe-saisons")

    style_vars = ["pct_raquette", "pct_3pts_pts", "pct_CA", "pct_2e_chance",
                  "pct_banc", "part_3pts_tirs", "pace", "taille_moy",
                  "dep_star", "gambling_def"]

    # besoin du NIVEAU pour le controle : NetRtg approx via wr (et ELO plus bas)
    # NetRtg propre : on le recalcule simplement comme proxy = wr (z) ici,
    # mais le vrai controle de niveau se fait avec l'ELO dans le test E4.

    f = open(f"{OUT}/style.txt", "w", encoding="utf-8")
    def p(*x): print(*x, file=f)

    # ---- E2 : le style est-il "pur" (non correle au niveau=wr) ? ----
    p("=== E2. LE STYLE EST-IL INDEPENDANT DU NIVEAU ? ===")
    p("corr de chaque variable de style avec le taux de victoire (= proxy niveau).")
    p("|r| faible => vraie variable de STYLE ; |r| fort => contaminee par le niveau.\n")
    corr_niveau = {}
    for v in style_vars:
        r = a[v].corr(a["wr"])
        corr_niveau[v] = r
        tag = "STYLE pur" if abs(r) < 0.35 else ("mixte" if abs(r) < 0.55 else "NIVEAU")
        p(f"   {v:16s} r(wr) = {r:+.2f}   [{tag}]")
    style_pur = [v for v in style_vars if abs(corr_niveau[v]) < 0.45]
    p(f"\n   -> variables de style retenues (|r|<0.45) : {style_pur}\n")

    # ---- E3 : choisir k par silhouette ----
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    X = StandardScaler().fit_transform(a[style_pur].values)
    p("=== E3. NOMBRE DE CLUSTERS (silhouette, plus haut = mieux) ===")
    best_k, best_s = None, -1
    for k in range(2, 6):
        km = KMeans(n_clusters=k, n_init=25, random_state=0).fit(X)
        s = silhouette_score(X, km.labels_)
        p(f"   k={k} : silhouette = {s:.3f}")
        if s > best_s:
            best_k, best_s = k, s
    p(f"   -> k retenu = {best_k}\n")

    km = KMeans(n_clusters=best_k, n_init=25, random_state=0).fit(X)
    a["style_cluster"] = km.labels_
    z = (a[style_pur] - a[style_pur].mean()) / a[style_pur].std()
    p(f"=== ARCHETYPES DE STYLE (k={best_k}) ===\n")
    for c in sorted(a["style_cluster"].unique()):
        idx = a["style_cluster"] == c
        moy = z[idx].mean().sort_values(ascending=False)
        hauts = [f"{k_}(+{v:.1f})" for k_, v in moy.items() if v >= 0.5][:3]
        bas = [f"{k_}({v:.1f})" for k_, v in moy.items() if v <= -0.5][-3:]
        p(f"--- Style {c} : wr moyen {a[idx]['wr'].mean()*100:.0f}% "
          f"(de {a[idx]['wr'].min()*100:.0f}% a {a[idx]['wr'].max()*100:.0f}%) ---")
        p(f"    marqueurs +: {', '.join(hauts) or '-'}")
        p(f"    marqueurs -: {', '.join(bas) or '-'}")
        for _, r in a[idx].sort_values("wr", ascending=False).iterrows():
            p(f"      {r['eq']:16s} {r['Saison']}  wr {r['wr']*100:3.0f}%  "
              f"raquette {r['pct_raquette']*100:2.0f}% 3pts {r['pct_3pts_pts']*100:2.0f}% "
              f"CA {r['pct_CA']*100:2.0f}% taille {r['taille_moy']:.2f}")
        p("")
    p("CLE : wr tres variable a l'interieur d'un style => le style n'est PAS le niveau.")
    p("     wr quasi constant => le 'style' capture en fait la force (a eviter).\n")
    a.to_csv(f"{OUT}/profils_style.csv", index=False)

    # ---- E4 : test decisif - le style ajoute-t-il a l'ELO ? ----
    test_E4(a, style_pur, p)
    f.close()
    print(open(f"{OUT}/style.txt", encoding="utf-8").read())


# ----------------------------------------------------------------------------
# E4. A ecart d'ELO controle, le style change-t-il le resultat du match ?
# ----------------------------------------------------------------------------
def test_E4(a, style_pur, p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score

    p("=== E4. TEST DECISIF : LE STYLE AJOUTE-T-IL A L'ELO ? ===")
    p("On predit chaque match. Modele 1 = ecart d'ELO seul (le NIVEAU).")
    p("Modele 2 = ecart d'ELO + differentiel de style. Si l'AUC ne bouge pas,")
    p("le style n'apporte rien une fois le niveau connu.\n")

    cal = pd.read_csv("data/calendrier_resultat_fusionne_elo_calcule.csv", sep=";", dtype=str)
    cal.columns = [c.strip() for c in cal.columns]
    cal = cal[cal["Saison"].isin(SAISONS_OK)].copy()

    def fc(*subs):
        for c in cal.columns:
            if all(s in sa(c) for s in subs):
                return c
    ED, EE = fc("elo", "domicile", "avant"), fc("elo", "exterieur", "avant")
    SD, SE = fc("score", "domicile"), fc("score", "exterieur")
    for c in [ED, EE, SD, SE]:
        cal[c] = pd.to_numeric(cal[c].astype(str).str.replace(",", "."), errors="coerce")
    cal["dom"] = cal["Domicile"].map(canon)
    cal["ext"] = cal["Exterieur"].map(canon)
    cal["home_win"] = (cal[SD] > cal[SE]).astype(int)
    cal["d_elo"] = cal[ED] - cal[EE]

    # differentiel de style domicile - exterieur (style de la saison du match)
    st = a.set_index(["eq", "Saison"])[style_pur]
    rows = []
    for _, r in cal.iterrows():
        kd, ke = (r["dom"], r["Saison"]), (r["ext"], r["Saison"])
        if kd in st.index and ke in st.index:
            d = (st.loc[kd] - st.loc[ke]).to_dict()
            d.update(d_elo=r["d_elo"], home_win=r["home_win"])
            rows.append(d)
    D = pd.DataFrame(rows).dropna()
    p(f"{len(D)} matchs exploitables.\n")

    y = D["home_win"].values
    X1 = StandardScaler().fit_transform(D[["d_elo"]].values)
    X2 = StandardScaler().fit_transform(D[["d_elo"] + style_pur].values)
    clf = LogisticRegression(max_iter=2000)
    auc1 = cross_val_score(clf, X1, y, cv=5, scoring="roc_auc").mean()
    auc2 = cross_val_score(clf, X2, y, cv=5, scoring="roc_auc").mean()
    p(f"   Modele 1 (ELO seul)        : AUC = {auc1:.3f}")
    p(f"   Modele 2 (ELO + style)     : AUC = {auc2:.3f}")
    p(f"   gain du style              : {auc2 - auc1:+.3f}")
    p("")
    # quels styles pesent le plus une fois l'ELO inclus ?
    clf.fit(X2, y)
    co = pd.Series(clf.coef_[0], index=["d_elo"] + style_pur).sort_values(key=abs, ascending=False)
    p("   Poids (standardises) dans le modele ELO+style :")
    for k_, v in co.items():
        p(f"      {k_:16s} {v:+.3f}")
    p("")
    if auc2 - auc1 < 0.01:
        p("   VERDICT : le style n'ajoute quasi RIEN a l'ELO. Le resultat d'un match")
        p("   se joue sur le NIVEAU, pas sur le style. (Le style sert a DECRIRE une")
        p("   equipe / le recrutement, pas a predire qui gagne.)")
    else:
        p("   VERDICT : le style apporte un gain reel au-dela du niveau (ELO).")
        p("   Les variables de style ci-dessus a coef non nul sont les leviers.")


if __name__ == "__main__":
    main()
