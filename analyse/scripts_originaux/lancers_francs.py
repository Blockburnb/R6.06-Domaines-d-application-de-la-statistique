"""
lancers_francs.py — Le taux de lancers francs (4e facteur d'Oliver) :
  vrai facteur de victoire, ou bruit dependant des fautes (donc inutile au pari) ?

3 questions :
  1) FACTEUR : un avantage aux lancers separe-t-il gagnants et perdants ?
     (AUC seul, taille d'effet de Cohen, Mann-Whitney, IC bootstrap)
  2) SKILL ou HASARD : le taux de LF est-il une qualite stable d'equipe
     (reproductible d'un match a l'autre) ou du bruit ? -> eta^2 (part de
     variance expliquee par l'equipe-saison), compare a l'eFG.
  3) PARI : le taux de LF cumule AVANT match ajoute-t-il de la prediction
     au differentiel de points ? (walk-forward, hors-echantillon strict)

Usage : python analyse/scripts_originaux/lancers_francs.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import outils as O
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from scipy.stats import mannwhitneyu

EPS = 1e-9


def agreger_avec_lf(df):
    """Agregat equipe x match incluant LF_marques (absent de l'outil standard)."""
    j = df[df["Joueur"] != "TOTAUX EQUIPE"].copy()
    keys = ["eq", "Saison", "Num_match", "dom_ext", "adv"]
    num = ["Tirs_tentes", "Tirs_marques", "3pts_marques",
           "LF_marques", "LF_tentes", "Pts", "RO", "BP"]
    num = [c for c in num if c in j.columns]
    t = j.groupby(keys, as_index=False)[num].sum()
    t = t.merge(j.groupby(keys, as_index=False)["Gagne_perdu"].first(), on=keys)
    t["Victoire"] = t["Gagne_perdu"].str.strip().str.lower().eq("victoire").astype(int)
    # facteurs
    t["eFG"] = (t["Tirs_marques"] + 0.5 * t["3pts_marques"]) / (t["Tirs_tentes"] + EPS) * 100
    t["FTr"] = t["LF_tentes"] / (t["Tirs_tentes"] + EPS)            # Oliver : LF tentes / tirs tentes
    t["FT_made_rate"] = t["LF_marques"] / (t["Tirs_tentes"] + EPS)  # LF marques / tirs tentes
    t["pct_LF"] = t["LF_marques"] / (t["LF_tentes"] + EPS) * 100    # adresse aux LF
    t["part_pts_LF"] = t["LF_marques"] / (t["Pts"] + EPS) * 100     # % des points venant des LF
    t["nm"] = pd.to_numeric(t["Num_match"], errors="coerce")
    return t


def bloc1_facteur(t):
    print("=" * 72)
    print("1) LES LANCERS FRANCS SEPARENT-ILS GAGNANTS ET PERDANTS ?")
    print("=" * 72)
    stats = ["FTr", "FT_made_rate", "pct_LF", "part_pts_LF", "eFG"]
    m = O.differentiel_adversaire(t, stats)
    print(f"   ({len(m)} confrontations appariees, saisons 23-24 + 24-25)\n")
    print(f"   {'Facteur':22s} {'AUC seul':>9s} {'Cohen d':>8s} "
          f"{'ecart G-P':>10s} {'IC95':>16s} {'p (MW)':>9s}")
    rng = np.random.RandomState(0)
    noms = {"FTr": "Taux de LF (LFt/Tt)", "FT_made_rate": "LF marques / Tirs",
            "pct_LF": "Adresse aux LF (%)", "part_pts_LF": "% points venant LF",
            "eFG": "eFG% (reference)"}
    for c in stats:
        d = m.dropna(subset=["d_" + c, "Victoire"])
        y = d["Victoire"].values
        x = d["d_" + c].values
        auc = roc_auc_score(y, x)
        win, los = d[c][y == 1].values, d[c][y == 0].values  # niveau brut gagnant/perdant
        sd = np.sqrt(((win.var(ddof=1) + los.var(ddof=1)) / 2))
        cohen = (win.mean() - los.mean()) / (sd + EPS)
        diff = d["d_" + c][y == 1].values  # ecart gagnant - perdant (sur les lignes gagnantes)
        boot = [rng.choice(diff, len(diff)).mean() for _ in range(2000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        p = mannwhitneyu(win, los, alternative="two-sided").pvalue
        sig = "***" if p < 1e-3 else ("**" if p < 1e-2 else ("*" if p < 5e-2 else "ns"))
        print(f"   {noms[c]:22s} {auc:9.3f} {cohen:8.2f} {diff.mean():10.2f} "
              f"[{lo:6.2f},{hi:6.2f}] {p:9.1e} {sig}")
    print("\n   Reperes : eFG AUC~0.92 (quasi-definitionnel). Un facteur 'utile'")
    print("   se situe nettement au-dessus de 0.50.\n")
    return m


def bloc2_skill_ou_hasard(t):
    print("=" * 72)
    print("2) SKILL ou HASARD : le taux de LF est-il une qualite STABLE ?")
    print("=" * 72)

    def eta2(col):
        """Part de variance du facteur expliquee par l'identite equipe-saison."""
        d = t.dropna(subset=[col]).copy()
        grand = d[col].mean()
        ss_tot = ((d[col] - grand) ** 2).sum()
        ss_bet = d.groupby(["eq", "Saison"])[col].apply(
            lambda s: len(s) * (s.mean() - grand) ** 2).sum()
        return ss_bet / (ss_tot + EPS)

    def split_half(col):
        """Correlation moitie 1 / moitie 2 de saison (par equipe-saison)."""
        a, b = [], []
        for _, g in t.dropna(subset=[col]).sort_values("nm").groupby(["eq", "Saison"]):
            if len(g) < 6:
                continue
            h = len(g) // 2
            a.append(g[col].iloc[:h].mean())
            b.append(g[col].iloc[h:].mean())
        if len(a) < 4:
            return np.nan, len(a)
        return np.corrcoef(a, b)[0, 1], len(a)

    print(f"   {'Facteur':22s} {'eta^2 equipe':>13s} {'split-half r':>13s}")
    for c, lab in [("FTr", "Taux de LF"), ("eFG", "eFG% (ref skill)"),
                   ("pct_LF", "Adresse aux LF")]:
        e = eta2(c)
        r, n = split_half(c)
        print(f"   {lab:22s} {e:13.2f} {r:13.2f}   (n={n} eq-saisons)")
    print("\n   Lecture : eta^2 et r eleves = trait stable d'equipe (skill).")
    print("   Proche de 0 = le facteur change a chaque match (hasard / contexte).\n")


def bloc3_pari(t):
    print("=" * 72)
    print("3) PARI : le taux de LF cumule AVANT match aide-t-il a predire ?")
    print("=" * 72)
    # ecart de points du match (pour le differentiel cumule)
    t = t.copy()
    # construire l'ecart via appariement adverse
    mm = O.differentiel_adversaire(t, ["Pts", "FTr"])
    # pour le walk-forward : 1 ligne par match (perspective domicile)
    h = mm[mm["home"] == 1].copy()
    h["ecart"] = h["d_Pts"]
    h["home_win"] = h["Victoire"]
    # ordre chrono
    h["sord"] = h["Saison"].str[:2].astype(int)
    # numero de match (depuis t, via match_id : on reprend nm du domicile)
    nm_map = t.set_index(["eq", "Saison", "dom_ext"])  # pas fiable, on trie par sord puis Pts cumule
    # cumul AVANT match : on a besoin de l'ordre intra-saison -> on reconstruit nm
    # via la table t (domicile = eq de la ligne home)
    base = t[["eq", "Saison", "nm", "FTr"]].rename(columns={"eq": "dom_team"})
    # eq de la perspective domicile = "eq" d'origine; differentiel_adversaire a garde 'eq'
    h = h.merge(base.rename(columns={"dom_team": "eq"}), on=["eq", "Saison"], how="left",
                suffixes=("", "_b"))
    h = h.dropna(subset=["nm"]).drop_duplicates(["match_id"]).sort_values(["sord", "nm"])

    # cumuls AVANT match par equipe-saison (differentiel de pts et FTr)
    def cumuls(df, team_col, val_ecart, val_ftr):
        df = df.sort_values(["sord", "nm"])
        diff_pre, ftr_pre = {}, {}
        out_d, out_f = [], []
        hist_d, hist_f = {}, {}
        for _, r in df.iterrows():
            k = (r[team_col], r["Saison"])
            out_d.append(np.mean(hist_d.get(k, [])) if hist_d.get(k) else np.nan)
            out_f.append(np.mean(hist_f.get(k, [])) if hist_f.get(k) else np.nan)
            hist_d.setdefault(k, []).append(r[val_ecart])
            hist_f.setdefault(k, []).append(r[val_ftr])
        return out_d, out_f

    # cumul du DOMICILE (eq) et de l'EXTERIEUR (eq_opp) : on construit un long format
    # plus simple : table par equipe-match avec ecart signe et FTr, cumul, puis rejoin
    long = t.copy()
    # ecart signe de l'equipe = Pts - Pts_adv : recuperer via mm (toutes lignes)
    sig = mm[["eq", "Saison", "match_id", "d_Pts", "FTr", "home"]].copy()
    sig = sig.merge(t[["eq", "Saison", "nm"]], on=["eq", "Saison"])  # nm approx
    # NB : appariement nm imparfait (jointure large), on garde l'info au niveau equipe-saison
    # -> on calcule un cumul robuste par ORDRE des matchs de l'equipe
    teamrows = mm[["eq", "Saison", "match_id", "d_Pts", "FTr", "Victoire", "home"]].copy()
    teamrows["sord"] = teamrows["Saison"].str[:2].astype(int)
    # ordre : on n'a pas nm fiable ici -> on l'ajoute depuis t par (eq,Saison,FTr) approx
    teamrows = teamrows.merge(t[["eq", "Saison", "FTr", "nm"]].drop_duplicates(),
                              on=["eq", "Saison", "FTr"], how="left")
    teamrows = teamrows.dropna(subset=["nm"]).sort_values(["sord", "nm"])
    dd, ff = {}, {}
    pre_d, pre_f = [], []
    for _, r in teamrows.iterrows():
        k = (r["eq"], r["Saison"])
        pre_d.append(np.mean(dd.get(k, [])) if dd.get(k) else np.nan)
        pre_f.append(np.mean(ff.get(k, [])) if ff.get(k) else np.nan)
        dd.setdefault(k, []).append(r["d_Pts"])
        ff.setdefault(k, []).append(r["FTr"])
    teamrows["diff_pre"] = pre_d
    teamrows["ftr_pre"] = pre_f

    # recomposer le match : home vs away -> features differentielles pre-match
    home = teamrows[teamrows["home"] == 1][["match_id", "Victoire", "diff_pre", "ftr_pre"]]
    away = teamrows[teamrows["home"] == 0][["match_id", "diff_pre", "ftr_pre"]].rename(
        columns={"diff_pre": "diff_pre_a", "ftr_pre": "ftr_pre_a"})
    M = home.merge(away, on="match_id").dropna()
    M["d_diff_pre"] = M["diff_pre"] - M["diff_pre_a"]
    M["d_ftr_pre"] = M["ftr_pre"] - M["ftr_pre_a"]
    M = M.reset_index(drop=True)
    y = M["Victoire"].values
    n = len(M)
    print(f"   ({n} matchs avec historique pre-match exploitable)\n")

    def walk(feats):
        pred, truth = [], []
        for i in range(n):
            if i < 30:
                continue
            tr = M.iloc[:i].dropna(subset=feats + ["Victoire"])
            if len(tr) < 20 or tr["Victoire"].nunique() < 2:
                continue
            sc = StandardScaler().fit(tr[feats].values)
            clf = LogisticRegression(max_iter=2000).fit(sc.transform(tr[feats].values),
                                                         tr["Victoire"].values)
            xi = M.iloc[[i]][feats].values
            pred.append(int(clf.predict_proba(sc.transform(xi))[0, 1] >= 0.5))
            truth.append(y[i])
        pred, truth = np.array(pred), np.array(truth)
        return (pred == truth).mean(), len(truth)

    for lab, feats in [("differentiel seul", ["d_diff_pre"]),
                       ("differentiel + taux LF", ["d_diff_pre", "d_ftr_pre"]),
                       ("taux LF seul", ["d_ftr_pre"])]:
        acc, nn = walk(feats)
        print(f"   {lab:26s} : {acc*100:5.1f} %   (n={nn})")
    print("\n   Si 'diff + LF' n'ameliore pas 'diff seul' -> le taux de LF")
    print("   n'apporte rien d'exploitable avant match.\n")


if __name__ == "__main__":
    df = O.charger_equipes(saisons=O.SAISONS_COMPLETES)
    t = agreger_avec_lf(df)
    print(f"\n{len(t)} equipe-matchs (saisons completes 23-24, 24-25)")
    print(f"Profil moyen : FTr={t['FTr'].mean():.3f}  "
          f"adresse LF={t['pct_LF'].mean():.1f}%  "
          f"part des pts venant des LF={t['part_pts_LF'].mean():.1f}%\n")
    bloc1_facteur(t)
    bloc2_skill_ou_hasard(t)
    bloc3_pari(t)
