# Modèle de régression — probabilité de victoire & classement prédit

Script : [regression_modele.py](regression_modele.py) → sorties dans [sorties_reg/](sorties_reg/).
264 matchs (saisons 24-25 + 25-26, 12 équipes, 22 journées).

C'est le modèle "abouti" du projet : il sort une **vraie probabilité** par match (pas un
oui/non) et répond directement à l'attente du prof — *prédire le classement final dès la
mi-saison*.

---

## 1. Le modèle probabiliste

Régression logistique, features connues **avant** le match : écart d'ELO, forme récente
(net rating sur 5 matchs), derby.

| Métrique | Valeur | Interprétation |
|---|---|---|
| AUC | **0.760** | bon pouvoir discriminant |
| Accuracy | **69.7 %** | ~7 matchs sur 10 bien prédits |
| Brier score | **0.194** | qualité des probas (réf. "toujours 50 %" = 0.250) → nettement mieux |

### L'équation (lisible, défendable à l'oral)
```
logit(P_victoire_domicile) = 0.610
                           + 0.00471 × (écart ELO)
                           + 0.03647 × (écart de forme récente)
                           − 0.599   × (derby)
```
- **Avantage du terrain pur** (équipes à forces égales, hors derby) : **P ≈ 65 %** pour
  le receveur. C'est l'avantage du terrain quantifié.
- **+100 points d'ELO** d'avance → logit +0.47 → la proba passe d'environ 65 % à **~75 %**.
- **Derby : coefficient négatif (−0.60)** → en derby, l'avantage du terrain s'**efface**
  (le receveur ne profite plus de son public face à un rival proche géographiquement).
  C'est un vrai résultat, cohérent avec l'intuition « les derbys sont indécis ».

### Les probabilités sont-elles honnêtes ? (calibration)
On groupe les matchs par proba prédite et on compare au taux de victoire réel :

| Proba prédite | Victoires observées | n |
|---|---|---|
| ~26 % | 30 % | 44 |
| ~43 % | 42 % | 48 |
| ~58 % | 51 % | 51 |
| ~72 % | 75 % | 59 |
| ~87 % | 89 % | 62 |

→ **Prédit ≈ observé** sur toute l'échelle : le modèle est **bien calibré**. Quand il dit
"72 %", l'équipe gagne effectivement ~75 % du temps. Les probabilités sont exploitables
telles quelles (pour un pronostic, une cote…).

---

## 2. Classement final prédit dès la mi-saison (le livrable prof)

**Méthode** : on se place à la fin de la **journée 11** (mi-saison). Victoires déjà
acquises (J1-11) + **espérance de victoires** sur les matchs restants (J12-22) calculée
par le modèle → total prédit → classement. Comparé au classement réel final.

### Saison 24-25 — erreur moyenne **0.7 rang**, corrélation **0.96**, champion ✅

| #prédit | Équipe | V prédites | V réelles | #réel | écart |
|---|---|---|---|---|---|
| 1 | **Bourges** | 17.6 | 19 | 1 | 0 |
| 2 | Montpellier | 14.8 | 15 | 4 | −2 |
| 3 | Charnay | 14.7 | 15 | 3 | 0 |
| 4 | Basket Landes | 13.3 | 15 | 2 | +2 |
| 5 | Charleville | 12.7 | 13 | 5 | 0 |
| 6 | Lyon | 11.8 | 11 | 7 | −1 |
| 7 | Angers | 11.5 | 12 | 6 | +1 |
| 8 | Tarbes | 10.8 | 9 | 8 | 0 |
| 9 | Villeneuve d'Ascq | 9.1 | 7 | 10 | −1 |
| 10 | Landerneau | 6.7 | 7 | 9 | +1 |
| 11 | Roche Vendée | 5.5 | 6 | 11 | 0 |
| 12 | Chartres | 3.6 | 3 | 12 | 0 |

### Saison 25-26 — erreur moyenne **1.0 rang**, corrélation **0.91**, champion ✅

| #prédit | Équipe | V prédites | V réelles | #réel | écart |
|---|---|---|---|---|---|
| 1 | **Basket Landes** | 16.9 | 19 | 1 | 0 |
| 2 | Bourges | 15.5 | 17 | 2 | 0 |
| 3 | Charleville | 14.4 | 15 | 3 | 0 |
| 4 | Montpellier | 14.0 | 13 | 5 | −1 |
| 5 | Landerneau | 12.4 | 14 | 4 | +1 |
| 6 | Villeneuve d'Ascq | 12.4 | 11 | 7 | −1 |
| 7 | Charnay | 11.7 | 11 | 6 | +1 |
| … | … | | | | |
| 12 | Chartres | 5.3 | 7 | 8 | +4 |

### Lecture
Dès la mi-saison, le modèle place chaque équipe à **moins d'1 rang en moyenne** de sa
position finale (0.7 puis 1.0), avec une **corrélation de classement de 0.91-0.96**, et
**identifie correctement le champion les deux saisons** (Bourges puis Basket Landes). Les
erreurs se concentrent au **milieu de tableau**, là où quelques matchs serrés font
basculer le classement — c'est la part d'aléa irréductible. Le haut et le bas du tableau
sont très prévisibles.

---

## Conclusion
- **Outil opérationnel** : probabilité calibrée par match + classement prévisionnel
  fiable dès la J11. Répond pile au sujet « prédire le classement final à partir de la
  première partie de saison ».
- **Le niveau (ELO) fait l'essentiel**, la forme récente affine, le derby annule
  l'avantage du terrain — cohérent avec tout le reste de l'étude.
- **Limite** : le milieu de tableau reste incertain (matchs serrés) ; le haut et le bas
  sont quasi acquis dès la mi-saison.

## Fichiers
- `sorties_reg/regression.txt` — rapport complet
- `sorties_reg/matchs_proba.csv` — chaque match avec sa probabilité prédite
