"""
sans_elo.py — Peut-on pronostiquer SANS l'ELO (non public) ?

1) Modele walk-forward n'utilisant que de l'info PUBLIQUE connue avant match :
   - differentiel de points moyen cumule dans la saison (proxy du niveau)
   - forme recente (5 derniers matchs)
   - avantage du terrain
   Compare sa reussite a : baseline domicile, favori ELO, modele ELO.

2) Traduit "1 ecart-type d'avance" en reperes concrets (ecart-type des
   differentiels equipe - adversaire par match : eFG, %tirs, %3pts, PD, RD, pertes).

Usage : python analyse/scripts_originaux/sans_elo.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import outils as O
from sklearn.linear_model import LogisticRegression


def accuracy_walkforward():
    cal = O.charger_calendrier(forme=True, fenetre=5).reset_index(drop=True)

    # --- differentiel de points moyen cumule (saison en cours, avant match) ---
    hist = {}
    dd, de = [], []
    for _, r in cal.iterrows():
        kd, ke = (r["Saison"], r["dom"]), (r["Saison"], r["ext"])
        dd.append(np.mean(hist.get(kd, [])) if hist.get(kd) else np.nan)
        de.append(np.mean(hist.get(ke, [])) if hist.get(ke) else np.nan)
        hist.setdefault(kd, []).append(r["ecart"])
        hist.setdefault(ke, []).append(-r["ecart"])
    cal["diff_dom"] = dd
    cal["diff_ext"] = de
    cal["d_diff"] = cal["diff_dom"] - cal["diff_ext"]
    cal["n_dom"] = [len(hist.get((s, d), [])) for s, d in zip(cal["Saison"], cal["dom"])]

    y = cal["home_win"].values
    n = len(cal)

    # nombre de matchs deja joues par chaque equipe AVANT le match courant
    cnt = {}
    nb_dom, nb_ext = [], []
    for _, r in cal.iterrows():
        kd, ke = (r["Saison"], r["dom"]), (r["Saison"], r["ext"])
        nb_dom.append(cnt.get(kd, 0)); nb_ext.append(cnt.get(ke, 0))
        cnt[kd] = cnt.get(kd, 0) + 1; cnt[ke] = cnt.get(ke, 0) + 1
    cal["nb_dom"], cal["nb_ext"] = nb_dom, nb_ext
    valide = (cal["nb_dom"] >= 3) & (cal["nb_ext"] >= 3)

    WARMUP = 40  # comme l'analyse paris : on amorce sur les 40 premiers matchs

    def walk(features):
        pred, truth = [], []
        for i in range(n):
            if i < WARMUP or not valide.iloc[i]:
                continue
            tr = cal.iloc[:i]
            trv = tr[valide.iloc[:i].values].dropna(subset=features + ["home_win"])
            if len(trv) < 25 or trv["home_win"].nunique() < 2:
                continue
            X = trv[features].values
            clf = LogisticRegression(max_iter=2000).fit(X, trv["home_win"].values)
            xi = cal.iloc[[i]][features].values
            if np.isnan(xi).any():
                continue
            pred.append(int(clf.predict_proba(xi)[0, 1] >= 0.5))
            truth.append(y[i])
        pred, truth = np.array(pred), np.array(truth)
        return (pred == truth).mean(), len(truth)

    res = {}
    res["baseline_domicile"] = ((cal["home_win"][valide & (np.arange(n) >= WARMUP)] == 1).mean(),
                                int((valide & (np.arange(n) >= WARMUP)).sum()))
    # favori ELO (regle simple : ELO domicile > ELO exterieur => domicile gagne)
    sub = cal[valide & (np.arange(n) >= WARMUP)]
    fav_elo = (sub["d_elo"] > 0).astype(int)
    res["favori_elo_simple"] = ((fav_elo.values == sub["home_win"].values).mean(), len(sub))
    # favori differentiel (regle simple, sans modele) : d_diff + avantage terrain (~3 pts)
    fav_diff = ((sub["d_diff"].fillna(0) + 3.0) > 0).astype(int)
    res["favori_diff_simple"] = ((fav_diff.values == sub["home_win"].values).mean(), len(sub))

    res["modele_SANS_elo (diff+forme)"] = walk(["d_diff", "d_forme"])
    res["modele_diff_seul"] = walk(["d_diff"])
    res["modele_AVEC_elo (elo+forme)"] = walk(["d_elo", "d_forme"])
    res["modele_elo_seul"] = walk(["d_elo"])
    return res


def ecarts_types_differentiels():
    t = O.charger_equipes(saisons=O.SAISONS_COMPLETES)
    a = O.agreger_equipe_match(t)
    eps = 1e-9
    a["eFG"] = (a["Tirs_marques"] + 0.5 * a["3pts_marques"]) / (a["Tirs_tentes"] + eps) * 100
    a["pct_tirs"] = a["Tirs_marques"] / (a["Tirs_tentes"] + eps) * 100
    a["pct_3pts"] = a["3pts_marques"] / (a["3pts_tentes"] + eps) * 100
    a["possessions"] = a["Tirs_tentes"] - a["RO"] + a["BP"] + 0.44 * a["LF_tentes"]
    stats = ["eFG", "pct_tirs", "pct_3pts", "PD", "RD", "BP", "INT"]
    m = O.differentiel_adversaire(a, stats)
    out = {}
    for c in stats:
        out[c] = float(m["d_" + c].std())
    return out, len(m)


if __name__ == "__main__":
    print("=" * 70)
    print("1) REUSSITE DES PRONOSTICS — AVEC vs SANS ELO (walk-forward)")
    print("=" * 70)
    for k, (acc, nn) in accuracy_walkforward().items():
        print(f"  {k:34s} : {acc*100:5.1f} %   (n={nn})")

    print("\n" + "=" * 70)
    print("2) '1 ECART-TYPE D'AVANCE' = quel ecart concret entre les 2 equipes ?")
    print("=" * 70)
    sd, nm = ecarts_types_differentiels()
    noms = {"eFG": "Efficacite au tir (eFG%)", "pct_tirs": "% de tirs reussis",
            "pct_3pts": "% a 3 points", "PD": "Passes decisives",
            "RD": "Rebonds defensifs", "BP": "Pertes de balle", "INT": "Interceptions"}
    print(f"  (ecart-type du differentiel equipe - adversaire, sur {nm} matchs)")
    for c, v in sd.items():
        unite = "pts" if c in ("eFG", "pct_tirs", "pct_3pts") else ""
        print(f"  1 ecart-type sur {noms[c]:28s} ~= {v:4.1f} {unite}")
