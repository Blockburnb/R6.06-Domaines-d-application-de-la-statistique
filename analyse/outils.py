"""
outils.py - fonctions communes a tous les notebooks d'analyse LFB.

Centralise : chemins, normalisation des noms d'equipes/joueuses, chargement
des deux sources (stats equipes, calendrier ELO) et de la liste des joueuses.
Chaque notebook importe ce module puis se concentre sur SON analyse.

Sources :
  - data/equipes_fusionnees.csv                       : 1 ligne par joueuse x match
  - data/calendrier_resultat_fusionne_elo_calcule.csv : 1 ligne par match (+ ELO)
  - donnee prof/liste joueuses multi annee.xlsm       : 1 feuille par saison (11)
"""

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# --- chemins (resolus depuis la racine du repo, qui contient data/) ---
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DONNEE_PROF = ROOT / "donnée prof"
RESULTATS = ROOT / "analyse" / "resultats"

# competition de reference (orthographe d'origine dans les donnees, sans double n)
COMPET = "Championat de France"
# seules saisons completes (resultats fiables cote stats joueuses)
SAISONS_COMPLETES = ["23-24", "24-25"]


# ---------------------------------------------------------------------------
# Normalisation des noms
# ---------------------------------------------------------------------------
def sans_accents(x):
    """minuscules, sans accents, sans espaces de bord."""
    if not isinstance(x, str):
        return ""
    return (unicodedata.normalize("NFKD", x)
            .encode("ascii", "ignore").decode().lower().strip())


def canon_equipe(name):
    """Nom d'equipe canonique. Indispensable : les colonnes Equipe et Adversaire
    n'utilisent pas les memes libelles (Lyon vs Lyon Asvel Feminin, Montpellier
    vs Lattes Montpellier, Roche vendee vs Roche Vendee...)."""
    s = sans_accents(name)
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


def cle_joueuse(s):
    """Cle d'appariement d'une joueuse : initiale+nom sans ponctuation.
    'J. Wojta' -> 'jwojta' ; 'A.Diallo' -> 'adiallo'."""
    return "".join(c for c in sans_accents(s) if c.isalpha())


def trouver_colonne(cols, *mots):
    """Retrouve une colonne contenant tous les `mots` (robuste aux accents)."""
    for c in cols:
        cc = sans_accents(c)
        if all(m in cc for m in mots):
            return c
    return None


def parse_taille(x):
    """'1m68' -> 1.68"""
    if not isinstance(x, str):
        return np.nan
    return pd.to_numeric(x.lower().replace("m", ".").replace(" ", ""), errors="coerce")


# ---------------------------------------------------------------------------
# Source 1 : stats equipes (joueuse x match) -> agregat equipe x match
# ---------------------------------------------------------------------------
def charger_equipes(saisons=None, competition=COMPET):
    """Lit equipes_fusionnees.csv, convertit le numerique (decimale virgule),
    filtre la competition et les saisons, ajoute eq/adv/cle canoniques.
    Retourne le DataFrame au niveau JOUEUSE x match (ligne TOTAUX EQUIPE incluse)."""
    df = pd.read_csv(DATA / "equipes_fusionnees.csv", sep=";", decimal=",", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    num = ["Tps_jeu_decimal", "Tirs_marques", "Tirs_tentes", "2pts_tentes",
           "3pts_marques", "3pts_tentes", "LF_marques", "LF_tentes",
           "Points_int", "Point_2eme_chance", "Points_CA", "Points_banc",
           "Pts", "RO", "RD", "RT", "PD", "BP", "INT", "CT", "CTS", "F", "FPR", "EVAL"]
    for c in num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False),
                                  errors="coerce")
    df = df[df["Competition"] == competition].copy()
    if saisons is not None:
        df = df[df["Saison"].isin(saisons)].copy()
    df["eq"] = df["Equipe"].map(canon_equipe)
    df["adv"] = df["Adversaire"].map(canon_equipe)
    df["cle"] = df["Joueur"].map(cle_joueuse)
    return df


def agreger_equipe_match(df):
    """Agrege les stats des joueuses au niveau EQUIPE x match (somme),
    + dep_star (part de pts de la meilleure marqueuse) et resultat.
    Exclut la ligne 'TOTAUX EQUIPE' de la somme des joueuses."""
    j = df[df["Joueur"] != "TOTAUX EQUIPE"].copy()
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]
    num = ["Tps_jeu_decimal", "Tirs_marques", "Tirs_tentes", "3pts_marques",
           "3pts_tentes", "LF_tentes", "Pts", "RO", "RD", "PD", "BP", "INT", "CT"]
    num = [c for c in num if c in j.columns]
    t = j.groupby(keys, as_index=False)[num].sum()
    t = t.merge(j.groupby(keys, as_index=False)["Gagne_perdu"].first(), on=keys)
    star = (j.groupby(keys)["Pts"].max() / j.groupby(keys)["Pts"].sum()
            ).rename("dep_star").reset_index()
    t = t.merge(star, on=keys)
    t["Victoire"] = t["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)
    return t


def differentiel_adversaire(t, stats):
    """Reconstruit chaque match en differentiel equipe - adversaire.
    `stats` = colonnes a opposer. Ajoute d_<stat> et la colonne home (1=domicile).
    match_id unique en championnat (1 confrontation A domicile vs B / saison)."""
    dom = np.where(t["dom_ext"] == "Domicile", t["eq"], t["adv"])
    ext = np.where(t["dom_ext"] == "Domicile", t["adv"], t["eq"])
    t = t.copy()
    t["match_id"] = t["Saison"] + " | " + dom + " vs " + ext
    base = t[["match_id", "eq", "Saison", "dom_ext", "Victoire"] + stats].copy()
    opp = (base.rename(columns={c: c + "_opp" for c in stats})
           .rename(columns={"eq": "eq_opp", "Saison": "_s", "dom_ext": "_d",
                            "Victoire": "_v"}))
    m = base.merge(opp, on="match_id")
    m = m[m["eq"] != m["eq_opp"]].copy()
    for c in stats:
        m["d_" + c] = m[c] - m[c + "_opp"]
    m["home"] = (m["dom_ext"] == "Domicile").astype(int)
    return m


# ---------------------------------------------------------------------------
# Source 2 : calendrier + ELO  (-> matchs avec features pre-match)
# ---------------------------------------------------------------------------
def charger_calendrier(forme=True, fenetre=5):
    """Lit le calendrier ELO, derive les features connues AVANT match :
    d_elo (ecart ELO avant match), derby, ecart de points (cible), home_win,
    et la forme recente (net rating glissant sur `fenetre` matchs, reset/saison).
    Trie chronologiquement (saison puis journee)."""
    cal = pd.read_csv(DATA / "calendrier_resultat_fusionne_elo_calcule.csv",
                      sep=";", dtype=str)
    cal.columns = [c.strip() for c in cal.columns]
    ED = trouver_colonne(cal.columns, "elo", "domicile", "avant")
    EE = trouver_colonne(cal.columns, "elo", "exterieur", "avant")
    SD = trouver_colonne(cal.columns, "score", "domicile")
    SE = trouver_colonne(cal.columns, "score", "exterieur")
    DER = trouver_colonne(cal.columns, "derby")
    for c in [ED, EE, SD, SE]:
        cal[c] = pd.to_numeric(cal[c].astype(str).str.replace(",", "."), errors="coerce")
    cal["dom"] = cal["Domicile"].map(canon_equipe)
    cal["ext"] = cal["Exterieur"].map(canon_equipe)
    cal["jour"] = pd.to_numeric(cal["Journee"], errors="coerce")
    cal["elo_dom"], cal["elo_ext"] = cal[ED], cal[EE]
    cal["d_elo"] = cal[ED] - cal[EE]
    cal["ecart"] = cal[SD] - cal[SE]
    cal["home_win"] = (cal["ecart"] > 0).astype(int)
    cal["derby"] = pd.to_numeric(cal[DER], errors="coerce").fillna(0).astype(int)
    cal = cal.dropna(subset=[ED, EE, SD, SE])
    cal["sord"] = cal["Saison"].str[:2].astype(int)
    cal = cal.sort_values(["sord", "jour"]).reset_index(drop=True)

    if forme:
        fd, fe, hist = [], [], {}
        for _, r in cal.iterrows():
            kd, ke = (r["Saison"], r["dom"]), (r["Saison"], r["ext"])
            fd.append(np.mean(hist.get(kd, [])[-fenetre:]) if hist.get(kd) else 0.0)
            fe.append(np.mean(hist.get(ke, [])[-fenetre:]) if hist.get(ke) else 0.0)
            hist.setdefault(kd, []).append(r["ecart"])
            hist.setdefault(ke, []).append(-r["ecart"])
        cal["forme_dom"], cal["forme_ext"] = fd, fe
        cal["d_forme"] = np.array(fd) - np.array(fe)
    return cal


# ---------------------------------------------------------------------------
# Source 3 : liste des joueuses (11 saisons) - nationalite, taille, age
# ---------------------------------------------------------------------------
def lire_liste_joueuses():
    """Concatene les 11 feuilles 'liste joueuses AAAA-AAAA'.
    Colonnes reelles : Saison, Nom_complet, Date de naissance, Taille, Equipe,
    Nationalite, Nom, Prenom, Nom_condense. Retourne un DataFrame avec :
    cle, eq, Saison ('23-24'), nat, francaise (0/1), taille_num (m), age_num."""
    xl = pd.ExcelFile(DONNEE_PROF / "liste joueuses multi annee.xlsm")
    frames = []
    for sh in xl.sheet_names:
        if "liste joueuses" not in sh:
            continue
        d = pd.read_excel(xl, sh, dtype=str, header=0)
        d.columns = [str(c).strip() for c in d.columns]
        c_nom = trouver_colonne(d.columns, "nom_condense") or trouver_colonne(d.columns, "nom_complet")
        c_eq = trouver_colonne(d.columns, "equipe")
        c_nat = trouver_colonne(d.columns, "national")
        c_nais = trouver_colonne(d.columns, "naissance")
        c_tail = trouver_colonne(d.columns, "taille")
        annee = int(sh.split()[-1][:4])                       # 2023
        sc = f"{annee % 100:02d}-{(annee + 1) % 100:02d}"     # '23-24'
        sub = pd.DataFrame({
            "cle": d[c_nom].map(cle_joueuse),
            "eq": d[c_eq].map(canon_equipe) if c_eq else None,
            "nat": d[c_nat].fillna("").map(sans_accents) if c_nat else "",
            "nais": pd.to_datetime(d[c_nais], errors="coerce") if c_nais else pd.NaT,
            "taille_num": d[c_tail].map(parse_taille) if c_tail else np.nan,
            "Saison": sc, "ref_year": annee,
        })
        sub = sub[sub["cle"].str.len() > 1]
        frames.append(sub)
    L = pd.concat(frames, ignore_index=True)
    L["francaise"] = L["nat"].str.contains("franc").astype(int)
    L["age_num"] = L["ref_year"] - L["nais"].dt.year
    return L


def tailles_par_cle():
    """Taille (m) par (cle, Saison), depuis la liste des joueuses."""
    L = lire_liste_joueuses()
    return (L.dropna(subset=["taille_num"])[["cle", "Saison", "taille_num"]]
            .drop_duplicates(["cle", "Saison"]).rename(columns={"taille_num": "taille"}))
