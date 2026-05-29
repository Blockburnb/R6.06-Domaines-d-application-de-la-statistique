# Prédiction de la victoire + Typologie des joueuses

Scripts : [prediction.py](prediction.py), [joueuses.py](joueuses.py).
Sorties : [sorties_pred/](sorties_pred/), [sorties_joueuses/](sorties_joueuses/).

---

# PARTIE 1 — Prédire la victoire

**Règle d'or respectée** : on n'utilise QUE des infos connues *avant* le match
(sinon c'est de la triche — c'était le piège des "facteurs" mesurés pendant le match).
Features pré-match : écart d'ELO, derby, **forme récente** (net rating sur les 5
derniers matchs), **historique direct** (h2h). 264 matchs (saisons 24-25 + 25-26).

## Cible 1 : qui gagne ? (classification)

| Méthode | AUC | Accuracy |
|---|---|---|
| Baseline (toujours domicile) | 0.500 | 59.8 % |
| ELO seul (régression log.) | 0.750 | 66.7 % |
| **Rég. logistique (ELO + forme + h2h)** | **0.755** | 69.3 % |
| Random Forest | 0.741 | **70.1 %** |
| Gradient Boosting | 0.698 | 64.4 % |

→ **Meilleur compromis : régression logistique ELO + forme** (AUC 0.755, simple et
robuste). La Random Forest pousse l'accuracy à 70 % mais sans gagner en AUC.
→ **La forme récente apporte un vrai plus** : +3 pts d'accuracy sur l'ELO seul.
C'est le 2ᵉ facteur le plus important après l'ELO :

| Facteur | Importance (RF) | Poids (logistique) |
|---|---|---|
| **écart d'ELO** | 0.555 | +0.80 |
| **forme récente (5 matchs)** | 0.368 | +0.38 |
| historique direct (h2h) | 0.065 | −0.03 |
| derby | 0.012 | −0.16 |

→ Le **derby** a un effet quasi nul sur le vainqueur (mais cf. l'écart ci-dessous).
Les méthodes complexes (boosting) ne battent pas la régression : avec ~260 matchs et
peu de features, **le modèle simple gagne** (pas assez de données pour le non-linéaire).

## Cible 2 : de combien ? (régression sur l'écart de points)

| Méthode | Erreur moyenne (MAE) | R² |
|---|---|---|
| Baseline (écart moyen) | 11.5 pts | 0.00 |
| **Linéaire (ELO seul)** | **10.2 pts** | **+0.20** |
| Linéaire (ELO + forme + h2h) | 10.5 pts | +0.18 |
| Gradient Boosting | 10.9 pts | +0.08 |

→ On prédit l'écart à **±10 points** en moyenne. C'est honnête mais imprécis :
l'écart-type des écarts réels est de 14.6 pts → le basket reste **très variable**, une
grande partie de la marge est imprévisible (réussite du soir, blessures…).

**Calibration utile pour l'oral** : **+100 points d'ELO d'avance = +4,4 points d'écart
attendus**, plus **+2,9 pts** d'avantage du terrain. Ça rend l'ELO concret.
Exemple : Bourges (ELO ~1650) reçoit Chartres (~1360) → 290 ELO × 0.044 + 2.9 ≈
**+16 points** prédits pour Bourges.

## Conclusion prédiction
On peut prédire le **vainqueur à ~70 %** et l'**écart à ±10 pts**. L'ELO fait le gros du
travail, la **forme récente** ajoute un vrai plus, le reste (derby, h2h) est marginal.
Au-delà, l'aléa du basket plafonne ce qu'on peut prédire.

---

# PARTIE 2 — Typologie des joueuses (PCA + clustering)

C'est ici que le "style" a enfin du sens : **204 joueuses-saisons** (≥8 matchs, ≥10
min/match), dont **179 avec taille connue**, profilées en **stats par minute** (= leur
*rôle*, pas leur volume de jeu) + taille. Championnat 23-24 + 24-25.

## Les axes qui structurent les joueuses (PCA)

2 axes expliquent **60 %** de la variation. L'**axe 1** (39 %) oppose très clairement :
- d'un côté (poids +) **taille (+0.45), rebond offensif (+0.44), rebond déf. (+0.39),
  contres (+0.36)** → les intérieures
- de l'autre (poids −) **part de tirs à 3pts (−0.41), passes (−0.29)** → les extérieures

→ C'est l'opposition **intérieure ↔ extérieure**, l'axe fondamental du basket, que les
données **retrouvent toutes seules** : bon signe de validité. L'axe 2 (21 %) sépare le
**volume** (tirs, interceptions, passes = joueuses très impliquées) du reste.

## Les archétypes — k=2 retenu (validé par silhouette)

| k | silhouette |
|---|---|
| **2** | **0.245** ← meilleur |
| 3 | 0.179 |
| 4 | 0.180 |

→ Comme pour les équipes, les données ne supportent proprement que **2 groupes** : la
grande dichotomie **intérieures / extérieures**. (Forcer plus de groupes donne des
sous-types moins nets — disponibles dans le CSV si besoin.)

| Archétype | n | Taille | Profil | Marqueurs |
|---|---|---|---|---|
| **0 — Intérieures** | 77 | **1.89 m** | rebonds (off+déf), contres, taille, lancers ; peu de 3pts/passes | +taille, +reb_off, +reb_déf, +contres ; −3pts |
| **1 — Extérieures** | 102 | 1.77 m | tirs à 3pts, plus petites ; peu de rebond | +part 3pts ; −rebonds, −taille |

→ **Impact/minute** : intérieures 0.42 vs extérieures 0.31 — les intérieures pèsent un
peu plus par minute (le jeu près du panier reste payant), mais **dans chaque groupe
l'impact varie de stars à role-players** → on a bien capturé le *rôle*, pas le niveau.
C'est exactement ce qui manquait à l'analyse de style des équipes.

**Sous-types (k=5, pour aller plus fin)** — le script révèle aussi : meneuses-créatrices
(petites, +passes), pivots pures (1.91 m, +contres+rebonds), shooteuses spécialistes
(+3pts, peu de rebond), ailières polyvalentes. Détail : `joueuses_archetypes.csv`.

## Usage pour le recrutement (volet du prof)
Cette typologie répond à *"il manque quoi à mon équipe ?"* : on regarde la répartition
intérieures/extérieures de l'effectif et on cible une recrue du bon profil (ex. une
équipe sans pivot dominante → cibler un archétype 0 à fort impact/min).

---

## Bilan méthodes de data mining utilisées
- **Régression logistique / linéaire** — prédiction vainqueur & écart (le bon outil ici).
- **Random Forest / Gradient Boosting** — testés, mais le modèle simple gagne (peu de données).
- **Validation croisée 5-fold** — pour comparer honnêtement (pas de sur-apprentissage).
- **Forme glissante** (feature engineering temporel) — l'ajout qui marche.
- **PCA** — comprendre les axes de variation des joueuses.
- **k-means + silhouette** — archétypes de joueuses, k choisi par les données.

## Fichiers
- `sorties_pred/prediction.txt`, `matchs_features.csv`
- `sorties_joueuses/joueuses.txt`, `joueuses_archetypes.csv`
