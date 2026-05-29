"""
Analyse exploratoire approfondie - LFB
======================================
A. Quelles equipes sont armees pour gagner (force par equipe/saison +
   lien avantage-sur-un-facteur <-> taux de victoire).
B. Betes noires : confrontations directes ou une equipe cale anormalement.
C. Pronostics : predire la saison 24-25 avec l'info connue AVANT match
   (ELO, force de la saison 23-24). Backtest hors-echantillon.
D. Nationalite & panorama joueuses (11 saisons 2015->2026) :
   - evolution age / taille / part d'etrangeres (effet COVID ?) ;
   - profil individuel francaise vs etrangere ;
   - impact sur le collectif et les resultats de l'equipe.

IMPORTANT : la saison 25-26 est INCOMPLETE -> exclue des analyses de
resultats (A, B, C). Elle reste utilisee pour le panorama joueuses (D0).

Usage  : python analyse/exploratoire.py
Sorties: analyse/sorties_explo/*.txt et *.csv
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_explo"
os.makedirs(OUT, exist_ok=True)
COMPET = "Championat de France"
SAISONS_OK = ["23-24", "24-25"]   # saisons completes (resultats fiables)


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
        ("tango", "bourges"), ("flammes", "charleville"), ("hainaut", "villeneuve ascq"),
        ("asvel", "lyon"), ("aix", "aix"), ("calais", "calais"), ("nantes", "nantes"),
    ]:
        if cle in s:
            return val
    return s


def find_col(cols, *subs):
    for c in cols:
        cc = sa(c)
        if all(sub in cc for sub in subs):
            return c
    return None


def _key_nom(s):
    """Cle alphanumerique : 'J. Wojta'->'jwojta', 'A.Diallo'->'adiallo'."""
    return "".join(ch for ch in sa(s) if ch.isalpha())


def _parse_taille(x):
    if not isinstance(x, str):
        return np.nan
    return pd.to_numeric(x.lower().replace("m", ".").replace(" ", ""), errors="coerce")


# ----------------------------------------------------------------------------
# Chargement equipe x match + differentiel
# ----------------------------------------------------------------------------
def charger():
    df = pd.read_csv("data/equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    num = ["Tps_jeu_decimal", "Tirs_marques", "Tirs_tentes", "3pts_marques",
           "3pts_tentes", "LF_tentes", "Pts", "RO", "RD", "PD", "BP", "INT", "CT"]
    for c in num:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False),
                              errors="coerce")
    df = df[df["Competition"] == COMPET].copy()
    df["eq"] = df["Equipe"].map(canon)
    df["adv"] = df["Adversaire"].map(canon)
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]
    t = df.groupby(keys, as_index=False)[num].sum()
    t = t.merge(df.groupby(keys, as_index=False)["Gagne_perdu"].first(), on=keys)

    eps = 1e-9
    t["poss"] = t["Tirs_tentes"] - t["RO"] + t["BP"] + 0.44 * t["LF_tentes"]
    t["eFG"] = (t["Tirs_marques"] + 0.5 * t["3pts_marques"]) / (t["Tirs_tentes"] + eps)
    t["pct_3pts"] = t["3pts_marques"] / (t["3pts_tentes"] + eps)
    t["taux_pertes"] = t["BP"] / (t["poss"] + eps)
    t["pression_def"] = t["INT"] + t["CT"]
    t["Victoire"] = t["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)

    dom = np.where(t["dom_ext"] == "Domicile", t["eq"], t["adv"])
    ext = np.where(t["dom_ext"] == "Domicile", t["adv"], t["eq"])
    t["match_id"] = t["Saison"] + " | " + dom + " vs " + ext
    stats = ["eFG", "pct_3pts", "taux_pertes", "RD", "RO", "PD", "pression_def", "INT", "Pts"]
    base = t[["match_id", "eq", "Saison", "dom_ext", "Victoire"] + stats].copy()
    opp = base.rename(columns={c: c + "_opp" for c in stats}).rename(
        columns={"eq": "eq_opp", "Saison": "s2", "dom_ext": "d2", "Victoire": "v2"})
    m = base.merge(opp, on="match_id")
    m = m[m["eq"] != m["eq_opp"]].copy()
    for c in stats:
        m["d_" + c] = m[c] - m[c + "_opp"]
    m["home"] = (m["dom_ext"] == "Domicile").astype(int)
    return t, m


# ----------------------------------------------------------------------------
# A. Forces des equipes
# ----------------------------------------------------------------------------
def section_A(m):
    f = open(f"{OUT}/A_forces.txt", "w", encoding="utf-8")
    def p(*a): print(*a, file=f)
    p("=== A. QUELLES EQUIPES SONT ARMEES POUR GAGNER ===")
    p("(saisons completes uniquement : 23-24 et 24-25)\n")

    mm = m[m["Saison"].isin(SAISONS_OK)]
    g = mm.groupby(["eq", "Saison"]).agg(
        matchs=("Victoire", "size"), taux_victoire=("Victoire", "mean"),
        net_points=("d_Pts", "mean"), net_eFG=("d_eFG", "mean"),
        net_3pts=("d_pct_3pts", "mean"), net_pertes=("d_taux_pertes", "mean"),
        net_RD=("d_RD", "mean"), net_PD=("d_PD", "mean"),
        net_pressionD=("d_pression_def", "mean")).reset_index()
    g = g[g["matchs"] >= 5].copy()
    g.to_csv(f"{OUT}/A_forces_equipe_saison.csv", index=False)

    p(">> Net rating (diff. moyenne de points/match) par equipe et saison :")
    for s in sorted(g["Saison"].unique()):
        p(f"\n  Saison {s} :")
        for _, r in g[g["Saison"] == s].sort_values("net_points", ascending=False).iterrows():
            p(f"   {r['eq']:16s} netPts {r['net_points']:+6.1f} | "
              f"vict {r['taux_victoire']*100:4.0f}% | "
              f"net_eFG {r['net_eFG']*100:+5.1f} net_3pt {r['net_3pts']*100:+5.1f} "
              f"net_RD {r['net_RD']:+5.1f} net_PD {r['net_PD']:+5.1f}")

    p("\n>> Correlation (equipe x saison, n=%d) avantage-facteur <-> %% victoires :" % len(g))
    for col in ["net_points", "net_eFG", "net_3pts", "net_RD", "net_PD",
                "net_pressionD", "net_pertes"]:
        p(f"   {col:14s} r = {g[col].corr(g['taux_victoire']):+.2f}")
    p("\n  (positif = dominer ce facteur va avec gagner ; n est petit -> indicatif)")
    f.close()


# ----------------------------------------------------------------------------
# B. Betes noires
# ----------------------------------------------------------------------------
def section_B(m):
    f = open(f"{OUT}/B_betes_noires.txt", "w", encoding="utf-8")
    def p(*a): print(*a, file=f)
    p("=== B. BETES NOIRES (confrontations directes, saisons 23-24 + 24-25) ===\n")

    mm = m[m["Saison"].isin(SAISONS_OK)]
    niveau = mm.groupby("eq")["Victoire"].mean()
    pair = mm.groupby(["eq", "eq_opp"]).agg(
        n=("Victoire", "size"), vic=("Victoire", "mean"), net=("d_Pts", "mean")).reset_index()
    pair = pair[pair["n"] >= 3].copy()
    pair["niv_eq"] = pair["eq"].map(niveau)
    pair["niv_opp"] = pair["eq_opp"].map(niveau)
    pair["attendu"] = pair["niv_eq"] / (pair["niv_eq"] + pair["niv_opp"] + 1e-9)
    pair["surperf"] = pair["vic"] - pair["attendu"]
    pair = pair.sort_values("surperf").reset_index(drop=True)
    pair.to_csv(f"{OUT}/B_confrontations.csv", index=False)

    p(">> Sous-performances les plus marquees (equipe gagne bien moins qu'attendu")
    p("   vu les niveaux respectifs ; >=3 confrontations) :\n")
    for _, r in pair[pair["surperf"] <= -0.20].head(12).iterrows():
        p(f"   {r['eq']:15s} VS {r['eq_opp']:15s} : "
          f"{r['vic']*100:3.0f}% gagnes en {int(r['n'])} matchs "
          f"(attendu {r['attendu']*100:3.0f}%) | netPts {r['net']:+5.1f}")
    p("\n  ATTENTION : 3 a 4 confrontations par paire -> tendance, pas significatif.")
    f.close()


# ----------------------------------------------------------------------------
# C. Pronostics 24-25
# ----------------------------------------------------------------------------
def section_C(m):
    f = open(f"{OUT}/C_pronos.txt", "w", encoding="utf-8")
    def p(*a): print(*a, file=f)
    p("=== C. PRONOSTIQUER LA SAISON 24-25 (backtest hors-echantillon) ===\n")

    r2324 = m[m["Saison"] == "23-24"].groupby("eq")["d_Pts"].mean()
    p(f"Force 23-24 (net points) connue pour {len(r2324)} equipes "
      "(info disponible AVANT 24-25).\n")

    cal = pd.read_csv("data/calendrier_resultat_fusionne_elo_calcule.csv", sep=";", dtype=str)
    cal.columns = [c.strip() for c in cal.columns]
    cal = cal[cal["Saison"] == "24-25"].copy()
    C_SD = find_col(cal.columns, "score", "domicile")
    C_SE = find_col(cal.columns, "score", "exterieur")
    C_ED = find_col(cal.columns, "elo", "domicile", "avant")
    C_EE = find_col(cal.columns, "elo", "exterieur", "avant")
    for c in [C_SD, C_SE, C_ED, C_EE]:
        cal[c] = pd.to_numeric(cal[c].astype(str).str.replace(",", "."), errors="coerce")
    cal["dom"] = cal["Domicile"].map(canon)
    cal["ext"] = cal["Exterieur"].map(canon)
    cal["home_win"] = (cal[C_SD] > cal[C_SE]).astype(int)
    cal = cal.dropna(subset=[C_ED, C_EE])
    p(f"{len(cal)} matchs de championnat 24-25 (calendrier officiel) a pronostiquer.\n")

    def acc(pred, truth):
        pred, truth = np.array(pred, float), np.array(truth)
        ok = ~np.isnan(pred)
        return (pred[ok] == truth[ok]).mean(), int(ok.sum())

    a1, n1 = acc(np.ones(len(cal)), cal["home_win"])
    pred_elo = (cal[C_ED] > cal[C_EE]).astype(int)
    a2, n2 = acc(pred_elo, cal["home_win"])
    BONUS = 3.0
    def pred_force(row):
        rd, re_ = r2324.get(row["dom"], np.nan), r2324.get(row["ext"], np.nan)
        return np.nan if (np.isnan(rd) or np.isnan(re_)) else float((rd + BONUS) >= re_)
    a3, n3 = acc(cal.apply(pred_force, axis=1), cal["home_win"])

    p(">> Taux de bons pronostics sur la saison 24-25 :")
    p(f"   1. 'le domicile gagne' (naif)  : {a1*100:5.1f}%  ({n1} matchs)")
    p(f"   2. favori ELO (avant match)    : {a2*100:5.1f}%  ({n2} matchs)")
    p(f"   3. force de la saison 23-24    : {a3*100:5.1f}%  ({n3} matchs couverts)")
    p(f"\n  Upsets (le favori ELO perd) : {(pred_elo != cal['home_win']).mean()*100:.0f}% des matchs")
    p("\n  -> OUI on peut pronostiquer (ELO ~%.0f%%), mais ~1 match sur 3 surprend." % (a2*100))
    f.close()


# ----------------------------------------------------------------------------
# D. Nationalite & panorama (11 saisons)
# ----------------------------------------------------------------------------
def lire_liste_joueuses():
    """11 feuilles 'liste joueuses AAAA-AAAA'. Colonnes : Saison, Nom_complet,
    Date de naissance, Taille, Equipe, Nationalite, Nom, Prenom, Nom_condense."""
    xl = pd.ExcelFile("donnée prof/liste joueuses multi annee.xlsm")
    frames = []
    for sh in xl.sheet_names:
        if "liste joueuses" not in sh:
            continue
        d = pd.read_excel(xl, sh, dtype=str, header=0)
        d.columns = [str(c).strip() for c in d.columns]
        c_nom = find_col(d.columns, "nom_condense") or find_col(d.columns, "nom_complet")
        c_eq = find_col(d.columns, "equipe")
        c_nat = find_col(d.columns, "national")
        c_nais = find_col(d.columns, "naissance")
        c_tail = find_col(d.columns, "taille")
        sais = sh.split()[-1]                       # '2023-2024'
        sais_court = sais[2:4] + "-" + sais[7:9]    # '23-24'
        sub = pd.DataFrame({
            "cle": d[c_nom].map(_key_nom),
            "eq": d[c_eq].map(canon) if c_eq else None,
            "nat": d[c_nat].fillna("").map(sa) if c_nat else "",
            "nais": pd.to_datetime(d[c_nais], errors="coerce") if c_nais else pd.NaT,
            "taille_num": d[c_tail].map(_parse_taille) if c_tail else np.nan,
            "Saison": sais_court,
            "ref_year": 2000 + int(sais[2:4]),
        })
        sub = sub[sub["cle"].str.len() > 1]
        frames.append(sub)
    L = pd.concat(frames, ignore_index=True)
    L["francaise"] = L["nat"].str.contains("franc").astype(int)
    L["age_num"] = L["ref_year"] - L["nais"].dt.year
    return L


def section_D():
    f = open(f"{OUT}/D_nationalite.txt", "w", encoding="utf-8")
    def p(*a): print(*a, file=f)
    p("=== D. NATIONALITE & PANORAMA DES JOUEUSES (2015 -> 2026) ===\n")

    L = lire_liste_joueuses()
    p(f"{len(L)} lignes joueuse-saison sur {L['Saison'].nunique()} saisons.\n")

    # D0 : panorama / evolution
    p(">> Evolution du championnat par saison (toutes equipes) :")
    p(f"   {'saison':8s} {'nb joueuses':>11s} {'%etrangeres':>11s} {'age moyen':>9s} {'taille':>8s}")
    ev = L.groupby("Saison").agg(
        n=("cle", "size"), pct_etr=("francaise", lambda s: (1 - s.mean()) * 100),
        age=("age_num", "mean"), taille=("taille_num", "mean")).reset_index()
    ev["ordre"] = ev["Saison"].str[:2].astype(int)
    for _, r in ev.sort_values("ordre").iterrows():
        tl = f"{r['taille']:.2f}m" if pd.notna(r['taille']) else "  -  "
        p(f"   {r['Saison']:8s} {int(r['n']):>11d} {r['pct_etr']:>10.0f}% "
          f"{r['age']:>8.1f}a {tl:>8s}")
    ev.sort_values("ordre").drop(columns="ordre").to_csv(f"{OUT}/D_evolution_saison.csv", index=False)
    p("\n   (COVID = saisons 19-20 / 20-21)\n")

    # appariement aux stats (saisons completes)
    nat = L[["cle", "Saison", "francaise"]].drop_duplicates(["cle", "Saison"])
    df = pd.read_csv("data/equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in ["Tps_jeu_decimal", "Pts", "PD", "RT", "INT", "BP", "EVAL"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df = df[(df["Competition"] == COMPET) & (df["Saison"].isin(SAISONS_OK))].copy()
    df["cle"] = df["Joueur"].map(_key_nom)
    df["eq"] = df["Equipe"].map(canon)
    df = df.merge(nat, on=["cle", "Saison"], how="left")
    p(f">> Appariement nationalite <-> stats (23-24,24-25) : "
      f"{df['francaise'].notna().mean()*100:.0f}% des lignes\n")

    # D1 : profil individuel
    j = df.dropna(subset=["francaise"]).groupby(["cle", "Saison", "francaise"]).agg(
        matchs=("Pts", "size"), minutes=("Tps_jeu_decimal", "mean"), pts=("Pts", "mean"),
        pd_=("PD", "mean"), rt=("RT", "mean"), int_=("INT", "mean"),
        bp=("BP", "mean"), eval_=("EVAL", "mean")).reset_index()
    j = j[j["matchs"] >= 5]
    grp = j.groupby("francaise").agg(
        nb=("pts", "size"), minutes=("minutes", "mean"), points=("pts", "mean"),
        passes=("pd_", "mean"), rebonds=("rt", "mean"), inter=("int_", "mean"),
        pertes=("bp", "mean"), eval=("eval_", "mean"))
    grp.index = ["Etrangere" if k == 0 else "Francaise" for k in grp.index]
    grp.to_csv(f"{OUT}/D_profil_individuel.csv")
    p(">> Profil moyen par joueuse-saison (>=5 matchs) :")
    p(grp.round(2).to_string())

    # D2 : impact equipe
    df["min_etr"] = np.where(df["francaise"] == 0, df["Tps_jeu_decimal"], 0.0)
    ts = df.groupby(["eq", "Saison"]).agg(
        min_etr=("min_etr", "sum"), min_tot=("Tps_jeu_decimal", "sum"),
        pd_tot=("PD", "sum"), pts_tot=("Pts", "sum")).reset_index()
    ts["part_min_etr"] = ts["min_etr"] / ts["min_tot"]
    ts["pd_par_pts"] = ts["pd_tot"] / ts["pts_tot"]
    res = df.groupby(["eq", "Saison", "Num_match", "dom_ext", "Adversaire"])["Gagne_perdu"].first().reset_index()
    res["v"] = res["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)
    wr = res.groupby(["eq", "Saison"])["v"].mean().rename("taux_victoire").reset_index()
    ts = ts.merge(wr, on=["eq", "Saison"])
    ts.to_csv(f"{OUT}/D_equipe_nationalite.csv", index=False)
    p("\n>> Au niveau equipe x saison (n=%d) :" % len(ts))
    p(f"   part de minutes etrangeres : moy {ts['part_min_etr'].mean()*100:.0f}% "
      f"(de {ts['part_min_etr'].min()*100:.0f}% a {ts['part_min_etr'].max()*100:.0f}%)")
    p(f"   corr(part etrangeres, taux de victoire)        = {ts['part_min_etr'].corr(ts['taux_victoire']):+.2f}")
    p(f"   corr(part etrangeres, passes/point=collectif)  = {ts['part_min_etr'].corr(ts['pd_par_pts']):+.2f}")
    p("   (passes/point = passes dec. pour 1 point ; PLUS haut = plus collectif.")
    p("    corr positive => plus d'etrangeres ne rend PAS le jeu plus individuel ici)")
    f.close()


def cat(path):
    print("\n" + "#" * 72)
    print(open(path, encoding="utf-8").read())


def main():
    t, m = charger()
    print(f"charge: {len(t)} equipe-matchs, {len(m)} confrontations")
    for fn in (section_A, section_B, section_C):
        try:
            fn(m)
        except Exception:
            import traceback; traceback.print_exc()
    try:
        section_D()
    except Exception:
        import traceback; traceback.print_exc()
    for nm in ["A_forces", "B_betes_noires", "C_pronos", "D_nationalite"]:
        cat(f"{OUT}/{nm}.txt")


if __name__ == "__main__":
    main()
