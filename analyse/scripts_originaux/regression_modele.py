"""
MODELE DE REGRESSION LOGISTIQUE - probabilite de victoire + classement predit
=============================================================================
1. Modele : P(victoire domicile) = logistique(ecart ELO, avantage terrain, forme).
   -> sort une VRAIE PROBABILITE par match (pas juste oui/non).
2. Calibration & qualite : AUC, Brier score, courbe de fiabilite.
3. Application prof : a partir de la MI-SAISON (journee 11), predire le
   classement final et le comparer au classement reel.

Features connues avant match : d_elo, forme recente (5 matchs), derby.
Cible : victoire de l'equipe a domicile.
Saisons : 24-25 et 25-26 (132 matchs chacune, 12 equipes, 22 journees).

Usage : python analyse/regression_modele.py
Sorties: analyse/sorties_reg/*
"""

import os
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "analyse/sorties_reg"
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


def charger():
    cal = pd.read_csv("data/calendrier_resultat_fusionne_elo_calcule.csv", sep=";", dtype=str)
    cal.columns = [c.strip() for c in cal.columns]
    ED, EE = fc(cal.columns, "elo", "domicile", "avant"), fc(cal.columns, "elo", "exterieur", "avant")
    SD, SE = fc(cal.columns, "score", "domicile"), fc(cal.columns, "score", "exterieur")
    DER = fc(cal.columns, "derby")
    for c in [ED, EE, SD, SE]:
        cal[c] = pd.to_numeric(cal[c].astype(str).str.replace(",", "."), errors="coerce")
    cal["dom"] = cal["Domicile"].map(canon)
    cal["ext"] = cal["Exterieur"].map(canon)
    cal["jour"] = pd.to_numeric(cal["Journee"], errors="coerce")
    cal["d_elo"] = cal[ED] - cal[EE]
    cal["elo_d"], cal["elo_e"] = cal[ED], cal[EE]
    cal["ecart"] = cal[SD] - cal[SE]
    cal["home_win"] = (cal["ecart"] > 0).astype(int)
    cal["derby"] = pd.to_numeric(cal[DER], errors="coerce").fillna(0).astype(int)
    cal = cal.dropna(subset=[ED, EE, SD, SE])
    cal["sord"] = cal["Saison"].str[:2].astype(int)
    cal = cal.sort_values(["sord", "jour"]).reset_index(drop=True)

    # forme recente : net rating glissant 5 matchs (par saison, reset)
    fd, fe = [], []
    hist = {}
    for _, r in cal.iterrows():
        kd, ke = (r["Saison"], r["dom"]), (r["Saison"], r["ext"])
        fd.append(np.mean(hist.get(kd, [])[-5:]) if hist.get(kd) else 0.0)
        fe.append(np.mean(hist.get(ke, [])[-5:]) if hist.get(ke) else 0.0)
        hist.setdefault(kd, []).append(r["ecart"])
        hist.setdefault(ke, []).append(-r["ecart"])
    cal["forme_dom"], cal["forme_ext"] = fd, fe
    cal["d_forme"] = cal["forme_dom"] - cal["forme_ext"]
    return cal


# ----------------------------------------------------------------------------
# 1+2. Modele probabiliste + qualite
# ----------------------------------------------------------------------------
def modele(cal, p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_predict
    from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score

    feats = ["d_elo", "d_forme", "derby"]
    X = cal[feats].values
    y = cal["home_win"].values
    sc = StandardScaler().fit(X)
    Xs = sc.transform(X)

    clf = LogisticRegression(max_iter=2000)
    # probas hors-echantillon (cross_val) pour une eval honnete
    proba = cross_val_predict(clf, Xs, y, cv=5, method="predict_proba")[:, 1]
    pred = (proba >= 0.5).astype(int)

    p("=== 1. MODELE PROBABILISTE (regression logistique) ===\n")
    p(f"   {len(cal)} matchs | features : {feats}")
    p(f"   AUC            = {roc_auc_score(y, proba):.3f}  (pouvoir discriminant)")
    p(f"   Accuracy       = {accuracy_score(y, pred)*100:.1f}%")
    p(f"   Brier score    = {brier_score_loss(y, proba):.3f}  (qualite des probas, +bas=mieux)")
    p(f"   (Brier de reference 'toujours 50%' = {np.mean((0.5-y)**2):.3f})\n")

    # equation lisible (coef sur variables brutes)
    clf.fit(Xs, y)
    b = clf.coef_[0] / sc.scale_           # coef sur echelle reelle
    b0 = clf.intercept_[0] - (clf.coef_[0] * sc.mean_ / sc.scale_).sum()
    p("   Equation : logit(P_victoire_domicile) =")
    p(f"     {b0:+.3f}")
    for f_, c_ in zip(feats, b):
        p(f"     {c_:+.5f} x {f_}")
    p("\n   Avantage du terrain pur (d_elo=0, forme=0, pas derby) :")
    p(f"     P = {1/(1+np.exp(-b0)):.3f}  -> ~{1/(1+np.exp(-b0))*100:.0f}% pour le domicile a forces egales\n")

    # courbe de fiabilite (les probas sont-elles honnetes ?)
    p("   Fiabilite (matchs groupes par proba predite) :")
    cal = cal.assign(proba=proba)
    bins = pd.cut(cal["proba"], [0, .35, .5, .65, .8, 1.0])
    rel = cal.groupby(bins).agg(n=("home_win", "size"),
                                proba_moy=("proba", "mean"),
                                vict_reelle=("home_win", "mean"))
    for idx, r in rel.iterrows():
        if r["n"] > 0:
            p(f"     proba {str(idx):12s} : predit {r['proba_moy']*100:3.0f}%  "
              f"observe {r['vict_reelle']*100:3.0f}%  (n={int(r['n'])})")
    p("     -> si 'predit' ~ 'observe', les probabilites sont bien calibrees.\n")
    return clf, sc, feats


# ----------------------------------------------------------------------------
# 3. Classement final predit depuis la mi-saison
# ----------------------------------------------------------------------------
def classement_mi_saison(cal, clf, sc, feats, p):
    p("=== 3. CLASSEMENT FINAL PREDIT DES LA MI-SAISON (journee 11) ===\n")
    p("Methode : on se place a la fin de la journee 11. Pour chaque match RESTANT,")
    p("le modele donne P(victoire). On ajoute les victoires acquises (J1-11) +")
    p("l'esperance de victoires sur J12-22. On classe, et on compare au reel.\n")

    MI = 11
    for saison in sorted(cal["Saison"].unique()):
        s = cal[cal["Saison"] == saison].copy()
        equipes = sorted(set(s["dom"]) | set(s["ext"]))

        # victoires reelles J1-11 (acquises)
        acquis = {e: 0.0 for e in equipes}
        joue1 = s[s["jour"] <= MI]
        for _, r in joue1.iterrows():
            gagnant = r["dom"] if r["home_win"] == 1 else r["ext"]
            acquis[gagnant] += 1

        # esperance de victoires sur les matchs restants (J12-22) via le modele
        esper = {e: 0.0 for e in equipes}
        rest = s[s["jour"] > MI]
        X = sc.transform(rest[feats].values)
        pr = clf.predict_proba(X)[:, 1]
        for (_, r), phome in zip(rest.iterrows(), pr):
            esper[r["dom"]] += phome
            esper[r["ext"]] += (1 - phome)

        pred_tot = {e: acquis[e] + esper[e] for e in equipes}

        # classement reel final (toutes journees)
        reel = {e: 0 for e in equipes}
        for _, r in s.iterrows():
            reel[r["dom"] if r["home_win"] == 1 else r["ext"]] += 1

        pred_rank = sorted(equipes, key=lambda e: -pred_tot[e])
        reel_rank = sorted(equipes, key=lambda e: -reel[e])
        pos_reel = {e: i + 1 for i, e in enumerate(reel_rank)}

        p(f"--- Saison {saison} ---")
        p(f"   {'#pred':>5s} {'equipe':16s} {'V_pred':>7s} {'V_reel':>6s} {'#reel':>5s}  ecart")
        ecarts = []
        for i, e in enumerate(pred_rank):
            ec = (i + 1) - pos_reel[e]
            ecarts.append(abs(ec))
            p(f"   {i+1:>5d} {e:16s} {pred_tot[e]:7.1f} {reel[e]:6d} {pos_reel[e]:>5d}  {ec:+d}")
        # qualite du classement predit
        import numpy as _np
        rho = _np.corrcoef([pred_rank.index(e) for e in equipes],
                           [reel_rank.index(e) for e in equipes])[0, 1]
        p(f"   -> erreur moyenne de position : {_np.mean(ecarts):.1f} rangs | "
          f"correlation de classement = {rho:.2f}")
        # le champion est-il bien predit ?
        p(f"   -> champion predit : {pred_rank[0]}  | champion reel : {reel_rank[0]}  "
          f"{'OK' if pred_rank[0]==reel_rank[0] else 'X'}\n")


def main():
    cal = charger()
    f = open(f"{OUT}/regression.txt", "w", encoding="utf-8")
    def p(*x): print(*x, file=f)
    p("MODELE DE REGRESSION - probabilite de victoire & classement predit")
    p(f"Saisons : {sorted(cal['Saison'].unique())} | {len(cal)} matchs\n")
    clf, sc, feats = modele(cal, p)
    classement_mi_saison(cal, clf, sc, feats, p)
    cal.to_csv(f"{OUT}/matchs_proba.csv", index=False)
    f.close()
    print(open(f"{OUT}/regression.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
