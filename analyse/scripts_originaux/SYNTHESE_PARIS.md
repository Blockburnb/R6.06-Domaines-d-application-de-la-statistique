# Prédictions vs réalité + peut-on parier ?

Script : [paris.py](paris.py) → sorties dans [sorties_paris/](sorties_paris/).

> **Point méthodo capital** : ici j'évalue en **walk-forward** (hors-échantillon strict).
> Pour prédire un match, le modèle n'est entraîné que sur les matchs **antérieurs** —
> aucune fuite du futur. C'est la **seule** évaluation crédible pour parler de pari (les
> AUC précédentes en validation croisée étaient déjà honnêtes, mais le walk-forward
> imite exactement les conditions réelles : on parie sans connaître la suite).

224 matchs prédits ainsi (sur 264 ; les 40 premiers servent à amorcer le modèle).

---

## 1. Est-ce que je prédis bien les matchs ?

**Accuracy hors-échantillon strict : 70.5 %** (vs 59.8 % en pariant trivialement toujours
le domicile). Donc oui, le modèle prédit réellement, hors de tout sur-apprentissage.

### Graphique 1 — Calibration & séparation (`1_calibration.png`)
![calibration](sorties_paris/1_calibration.png)

- **À gauche (calibration)** : les points suivent la diagonale → quand le modèle annonce
  X %, l'équipe gagne ~X % du temps. Les probabilités sont **honnêtes**, pas juste un
  classement. C'est ce qui les rendrait théoriquement utilisables pour un pari.
- **À droite (séparation)** : les matchs gagnés par le domicile (bleu) sont concentrés à
  droite (proba haute), les défaites (rouge) à gauche. Le modèle **sépare** bien les deux
  — mais la zone de recouvrement au milieu (proba 40-60 %) = les matchs incertains, qu'on
  ne peut pas trancher.

### Graphique 2 — Prédiction match par match (`2_matchs.png`)
![matchs](sorties_paris/2_matchs.png)

Chaque point = un match de la saison 25-26. **Bleu = le domicile a gagné, rouge = perdu.**
Une bonne prédiction = bleus en haut (proba > 50 %), rouges en bas. C'est massivement le
cas : la majorité des bleus sont au-dessus de la ligne, les rouges en dessous. Les
"erreurs" sont les bleus sous la ligne et rouges au-dessus = les **upsets** (~30 %).

---

## 2. Pourrait-on réalistement parier avec ce modèle ?

**Réponse honnête : non, pas de façon rentable.** Voici pourquoi, chiffré.

### Le piège : prédire ≠ battre le bookmaker
Bien prédire (70 %) ne suffit pas. Pour gagner de l'argent, il faut être **plus précis
que le bookmaker**, car lui ajoute une **marge** (~6 %) dans ses cotes.

| Stratégie simulée | ROI |
|---|---|
| Parier le favori du modèle (book aussi bon que nous, marge 6 %) | **−5.5 %** |
| Value betting *si* on a un vrai edge de 7 pts sur le book | +31.5 % |

- **−5.5 %** : si le bookmaker estime les probas aussi bien que nous (le cas réaliste,
  car il utilise l'ELO **et plus**), sa marge nous fait perdre ~5 % à long terme. Mécanique
  et inévitable.
- **+31.5 %** : on ne gagne *que si* notre modèle est réellement **meilleur** que le book.
  Or notre modèle utilise seulement ELO + forme ; un bookmaker intègre blessures,
  compositions, dynamique en direct… **Très peu probable qu'on ait cet edge.**

### Les obstacles réels du pari LFB
1. **La marge du bookmaker** (~5-8 %) : il faut la battre *avant* de gagner un centime.
2. **Le book connaît déjà l'ELO** : notre principale info n'est pas un avantage.
3. **Le basket féminin français est un marché de niche** : cotes rares, plafonds de mise
   bas, peu de liquidité → même un edge théorique serait inexploitable en pratique.
4. **L'aléa** : ~30 % de surprises, donc forte variance → il faudrait des centaines de
   paris pour que l'espérance se réalise, avec un risque de ruine entre-temps.

### Verdict
- ✅ Le modèle est un **excellent outil de pronostic** : qui va gagner (70 %), avec quelle
  probabilité (calibrée), et le classement final dès la mi-saison.
- ❌ Ce **n'est pas** un système de paris rentable : prédire le sport ≠ battre un marché
  qui prédit déjà aussi bien, marge en plus.

> C'est exactement la nuance attendue dans une démarche data sérieuse : un modèle peut
> être *juste* sans être *profitable*. Le distinguer est un résultat en soi.

## Fichiers
- `sorties_paris/predictions.csv` — chaque match avec sa proba hors-échantillon
- `sorties_paris/1_calibration.png`, `2_matchs.png` — graphiques
- `sorties_paris/paris.txt` — rapport complet
