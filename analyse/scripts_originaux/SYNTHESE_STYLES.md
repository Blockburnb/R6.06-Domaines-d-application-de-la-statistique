# Styles d'équipes & confrontations de styles — LFB

Script : [styles.py](styles.py) → sorties dans [sorties_styles/](sorties_styles/).
Saisons complètes 23-24 + 24-25, championnat. 20 équipe-saisons, 360 confrontations.

Cadre : les **Four Factors de Dean Oliver** (le standard mondial d'analyse basket),
tous calculables ici, en version offensive ET défensive :

| Facteur | Offensif | Défensif (ce qu'on impose) |
|---|---|---|
| Efficacité tir | eFG% | eFG% concédé |
| Pertes de balle | TOV% | TOV% forcées |
| Rebond | ORB% (rebond off.) | DRB% (rebond déf.) |
| Lancers | FTr (accès à la ligne) | — |

\+ rythme (`pace` = possessions/match), part de tirs à 3pts (`TPAr`), dépendance à
la star, et les **ratings** ORtg (pts/100 poss) / DRtg (pts encaissés/100 poss).

---

## S1-S2. Les 4 archétypes de jeu (clustering k-means)

| Archétype | Identité (traits saillants) | % victoires | Équipes |
|---|---|---|---|
| **#2 — Dominateurs / rebond** | rebond off **et** déf élevés, concèdent peu d'eFG | **74 %** | Bourges (×2), Villeneuve d'Ascq 23-24, Basket Landes (×2), Montpellier 24-25, Angers 24-25 |
| **#3 — Intermédiaires / défense agressive** | forcent des pertes, bon eFG concédé, mais faible rebond déf. | 40 % | Lyon 24-25, Charleville 24-25, Montpellier 23-24, Charnay, Angers 23-24, VA 24-25, Chartres 24-25, Landerneau 24-25 |
| **#0 — Jeu extérieur / 3pts** | beaucoup de 3pts (TPAr), perdent des balles, peu de lancers | 37 % | Lyon 23-24, Charleville 23-24, Roche Vendée 24-25 |
| **#1 — Dépendants d'une star / lents** | dépendance star très forte (+2.9σ), rythme lent | **28 %** | Landerneau 23-24, Roche Vendée 23-24 |

→ **Le style gagnant = la domination au rebond + une défense qui concède peu**
(archétype #2, 74 %). C'est le profil de Bourges et du VA version 23-24.
→ **La dépendance à une star = marqueur des équipes faibles** (#1, 28 %), confirme
nos analyses précédentes.
→ Le détail des Four Factors par équipe : `sorties_styles/profils_avec_cluster.csv`.

---

## S3. Matrice de confrontation : quel style bat quel style

Taux de victoire (ligne = mon archétype, colonne = archétype adverse) :

| Mon style ↓ \ vs → | #0 3pts | #1 Star | #2 Domin. | #3 Inter. |
|---|---|---|---|---|
| **#0 Jeu 3pts** | 50 | 62 | **15** | 45 |
| **#1 Dépend. star** | 38 | 50 | **8** | 33 |
| **#2 Dominateurs** | 85 | 92 | 50 | 81 |
| **#3 Intermédiaires** | 55 | 67 | **19** | 50 |

**Lectures clés :**
- **Les dominateurs (#2) écrasent absolument tout** : 85 % vs jeu-3pts, 92 % vs
  dépendants-star, 81 % vs intermédiaires. Aucune kryptonite dans ces données.
- **À l'inverse, personne ne bat les dominateurs** : le style 3pts ne gagne que 15 %
  contre eux, les dépendants-star 8 %, les intermédiaires 19 %.
- Entre les "non-dominateurs", hiérarchie nette : les intermédiaires (#3) battent le
  jeu-3pts (55 %) et les dépendants-star (67 %) → **la défense agressive + équilibre
  bat la spécialisation offensive**.
- Le pire matchup du tableau : **dépendants-star vs dominateurs = 8 %** → miser sur une
  seule joueuse face à une équipe complète = quasi perdu d'avance.

⚠️ Certaines cases reposent sur 4-12 matchs → tendance, pas preuve formelle.

---

## S3b. Tests d'interaction — le "style bat style" est-il réel ?

On teste si l'effet d'un style **dépend** du style adverse (terme d'interaction en
régression logistique, coef standardisé ; |coef| ≥ 0.15 = effet conditionnel notable) :

| Hypothèse testée | Coef interaction | Verdict |
|---|---|---|
| Mon adresse à 3pts × rebond défensif adverse | **−0.40** | **notable** |
| Mon pressing (INT) × dépendance à la star adverse | **+0.23** | **notable** |
| Mon rythme × rythme adverse | 0.00 | nul |

→ **Deux vraies confrontations de styles ressortent** (au-delà du simple niveau) :
1. **Le rebond défensif adverse neutralise l'adresse extérieure** (−0.40). Une équipe
   qui mise sur le 3pts marque *moins utilement* contre une équipe qui domine au
   rebond : les tirs ratés sont récupérés par la défense → pas de seconde chance. C'est
   l'effet "pierre-feuille-ciseaux" le plus net, et il **explique** pourquoi le style
   3pts (#0) se fait laminer par les dominateurs/rebondeurs (#2) dans la matrice.
2. **Le pressing est plus payant contre une équipe dépendante d'une star** (+0.23) :
   forcer des pertes de balle fait plus mal quand le jeu repose sur une seule joueuse
   (on la coupe du ballon).
3. Imposer son **rythme** n'a aucun effet conditionnel (0.00) : jouer vite ou lent ne
   dépend pas de l'adversaire.

→ Conclusion nuancée : **le style compte vraiment dans 2 cas précis** (rebond vs 3pts,
pressing vs star), mais pour le reste, *mieux vaut être une bonne équipe que d'avoir le
"bon style"*. Les dominateurs gagnent surtout parce qu'ils sont complets.

---

## Ce que ça apporte
- **Nouveau & parlant à l'oral** : la typologie en 4 archétypes + la matrice "qui bat
  qui" + l'explication mécanique (le rebond tue le 3pts, le pressing tue la
  dépendance-star) — étayée par les tests d'interaction.
- **Confirmé** : efficacité + rebond gagnent ; dépendance à une star = faiblesse.

## Fichiers
- `sorties_styles/profils_avec_cluster.csv` — Four Factors + archétype par équipe-saison
- `sorties_styles/matrice_winrate.csv`, `matrice_n.csv` — confrontations
- `sorties_styles/styles.txt`, `confrontations.txt`, `interactions.txt` — détail lisible
