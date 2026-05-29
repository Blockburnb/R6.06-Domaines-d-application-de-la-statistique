"""
PREDIRE LA VICTOIRE (et l'ecart de points) - LFB
=================================================
Regle d'or : on n'utilise QUE des infos connues AVANT le match (sinon triche).
Features pre-match :
  - d_elo        : ecart d'ELO avant match (le niveau)
  - home         : avantage du terrain
  - derby        : match derby (1/0)
  - forme_dom/ext: net rating sur les 5 derniers matchs de chaque equipe
  - d_forme      : difference de forme recente
  - h2h          : bilan historique dom vs ext (matchs anterieurs)

On compare plusieurs methodes en validation croisee :
  baseline (domicile) , ELO-logistique , Regression log. complete ,
  Random Forest , Gradient Boosting.
Cible 1 : victoire domicile (classif). Cible 2 : ecart de points (regression).

Usage : python analyse/prediction.py
Sorties: analyse/sorties_pred/*
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_pred"
os.makedirs(OUT, exist_ok=True)


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


def fc(cols, *subs):
    for c in cols:
        if all(s in sa(c) for s in subs):
            return c


# ----------------------------------------------------------------------------
# Construction de la table de matchs avec features PRE-match
# ----------------------------------------------------------------------------
def charger_matchs():
    cal = pd.read_csv("data/calendrier_resultat_fusionne_elo_calcule.csv", sep=";", dtype=str)
    cal.columns = [c.strip() for c in cal.columns]
    ED, EE = fc(cal.columns, "elo", "domicile", "avant"), fc(cal.columns, "elo", "exterieur", "avant")
    SD, SE = fc(cal.columns, "score", "domicile"), fc(cal.columns, "score", "exterieur")
    DER = fc(cal.columns, "derby")
    JOU = fc(cal.columns, "journee")
    for c in [ED, EE, SD, SE]:
        cal[c] = pd.to_numeric(cal[c].astype(str).str.replace(",", "."), errors="coerce")
    cal["dom"] = cal["Domicile"].map(canon)
    cal["ext"] = cal["Exterieur"].map(canon)
    cal["d_elo"] = cal[ED] - cal[EE]
    cal["ecart"] = cal[SD] - cal[SE]                 # cible regression
    cal["home_win"] = (cal["ecart"] > 0).astype(int)  # cible classif
    cal["derby"] = pd.to_numeric(cal[DER], errors="coerce").fillna(0).astype(int)
    cal["jour"] = pd.to_numeric(cal[JOU], errors="coerce")
    cal = cal.dropna(subset=[ED, EE, SD, SE]).reset_index(drop=True)

    # ordre chronologique : saison puis journee
    cal["sord"] = cal["Saison"].str[:2].astype(int)
    cal = cal.sort_values(["sord", "jour"]).reset_index(drop=True)

    # --- forme recente : net rating glissant sur 5 derniers matchs ---
    # on construit l'historique match par match, par equipe
    hist = {}      # eq -> liste des ecarts (de son point de vue) deja joues
    h2h = {}       # (a,b) -> liste resultats de a vs b (1 si a gagne)
    forme_dom, forme_ext, h2h_feat = [], [], []
    for _, r in cal.iterrows():
        d, e = r["dom"], r["ext"]
        fd = np.mean(hist.get(d, [])[-5:]) if hist.get(d) else 0.0
        fe = np.mean(hist.get(e, [])[-5:]) if hist.get(e) else 0.0
        forme_dom.append(fd)
        forme_ext.append(fe)
        prev = h2h.get((d, e), [])
        h2h_feat.append(np.mean(prev) if prev else 0.5)
        # maj apres le match
        hist.setdefault(d, []).append(r["ecart"])
        hist.setdefault(e, []).append(-r["ecart"])
        h2h.setdefault((d, e), []).append(int(r["ecart"] > 0))
        h2h.setdefault((e, d), []).append(int(r["ecart"] < 0))
    cal["forme_dom"] = forme_dom
    cal["forme_ext"] = forme_ext
    cal["d_forme"] = cal["forme_dom"] - cal["forme_ext"]
    cal["h2h"] = h2h_feat
    return cal


# ----------------------------------------------------------------------------
# Classification : victoire domicile
# ----------------------------------------------------------------------------
def classif(cal, p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score

    y = cal["home_win"].values
    p("=== CIBLE 1 : PREDIRE LA VICTOIRE A DOMICILE ===")
    p(f"{len(cal)} matchs | base : {y.mean()*100:.0f}% de victoires a domicile\n")

    feats_full = ["d_elo", "home_const", "derby", "d_forme", "h2h"]
    cal = cal.copy()
    cal["home_const"] = 1  # le terrain est deja implicite (dom vs ext), placeholder neutre

    def ev(X, model, name):
        auc = cross_val_score(model, X, y, cv=5, scoring="roc_auc").mean()
        acc = cross_val_score(model, X, y, cv=5, scoring="accuracy").mean()
        p(f"   {name:32s} AUC={auc:.3f}  accuracy={acc*100:.1f}%")
        return auc, acc

    p(">> Comparaison des methodes (validation croisee 5-fold) :")
    # baseline
    base = (np.ones_like(y) == y).mean()
    p(f"   {'baseline (toujours domicile)':32s} AUC=0.500  accuracy={base*100:.1f}%")

    Xelo = StandardScaler().fit_transform(cal[["d_elo"]].values)
    ev(Xelo, LogisticRegression(max_iter=2000), "ELO seul (log.)")

    Xf = StandardScaler().fit_transform(cal[["d_elo", "derby", "d_forme", "h2h"]].values)
    ev(Xf, LogisticRegression(max_iter=2000), "Reg. logistique (ELO+forme+h2h)")
    ev(cal[["d_elo", "derby", "d_forme", "h2h"]].values,
       RandomForestClassifier(n_estimators=400, max_depth=4, min_samples_leaf=8, random_state=0),
       "Random Forest")
    ev(cal[["d_elo", "derby", "d_forme", "h2h"]].values,
       GradientBoostingClassifier(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=0),
       "Gradient Boosting")

    # importance des features (RF) + poids logistique
    rf = RandomForestClassifier(n_estimators=400, max_depth=4, min_samples_leaf=8, random_state=0)
    rf.fit(cal[["d_elo", "derby", "d_forme", "h2h"]].values, y)
    imp = pd.Series(rf.feature_importances_, index=["d_elo", "derby", "d_forme", "h2h"]).sort_values(ascending=False)
    p("\n   Importance des facteurs (Random Forest) :")
    for k_, v in imp.items():
        p(f"      {k_:10s} {v:.3f}")

    lr = LogisticRegression(max_iter=2000).fit(Xf, y)
    co = pd.Series(lr.coef_[0], index=["d_elo", "derby", "d_forme", "h2h"]).sort_values(key=abs, ascending=False)
    p("\n   Poids standardises (reg. logistique) :")
    for k_, v in co.items():
        p(f"      {k_:10s} {v:+.3f}")
    p("")


# ----------------------------------------------------------------------------
# Regression : ecart de points
# ----------------------------------------------------------------------------
def regression(cal, p):
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score

    y = cal["ecart"].values
    p("=== CIBLE 2 : PREDIRE L'ECART DE POINTS ===")
    p(f"ecart reel : moyenne {y.mean():+.1f}, ecart-type {y.std():.1f} pts\n")

    def ev(cols, model, name):
        X = cal[cols].values
        mae = -cross_val_score(model, X, y, cv=5, scoring="neg_mean_absolute_error").mean()
        r2 = cross_val_score(model, X, y, cv=5, scoring="r2").mean()
        p(f"   {name:34s} MAE={mae:4.1f} pts  R2={r2:+.2f}")

    p(">> Erreur moyenne de prediction de l'ecart (val. croisee 5-fold) :")
    # baseline : ecart moyen constant
    mae_base = np.mean(np.abs(y - y.mean()))
    p(f"   {'baseline (ecart moyen constant)':34s} MAE={mae_base:4.1f} pts  R2=0.00")
    ev(["d_elo"], LinearRegression(), "Lineaire (ELO seul)")
    ev(["d_elo", "derby", "d_forme", "h2h"], LinearRegression(), "Lineaire (ELO+forme+h2h)")
    ev(["d_elo", "derby", "d_forme", "h2h"],
       GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=0),
       "Gradient Boosting")

    # calibration ELO -> points : combien de points par 100 ELO ?
    lr = LinearRegression().fit(cal[["d_elo"]].values, y)
    p(f"\n   Calibration : +100 points d'ELO d'avance = "
      f"{lr.coef_[0]*100:+.1f} points d'ecart attendus.")
    p(f"   (constante = {lr.intercept_:+.1f} pts = avantage du terrain implicite)\n")


def main():
    cal = charger_matchs()
    f = open(f"{OUT}/prediction.txt", "w", encoding="utf-8")
    def p(*x): print(*x, file=f)
    p("PREDICTION DE LA VICTOIRE - LFB")
    p("Features connues AVANT match : ecart ELO, derby, forme recente (5 matchs), h2h.")
    p(f"Saisons : {sorted(cal['Saison'].unique())}\n")
    classif(cal, p)
    regression(cal, p)
    cal.to_csv(f"{OUT}/matchs_features.csv", index=False)
    f.close()
    print(open(f"{OUT}/prediction.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
