# Quels facteurs pèsent le plus pour gagner un match ? (LFB)

**Données** : `data/equipes_fusionnees.csv`, championnat uniquement.
8 222 lignes joueuse×match → agrégées en **704 équipe×match** → **618 matchs**
appariés équipe-vs-adversaire (les 2 équipes ont leurs stats).

**Méthode clé** : on ne regarde pas une stat dans l'absolu mais **l'écart avec
l'adversaire** sur le match. « Tirer à 45 % » ne fait gagner que si l'adversaire
tire moins bien. Trois lectures complémentaires (pour ne pas se faire piéger par
la corrélation entre stats) :

| Méthode | À quoi ça sert | Qualité |
|---|---|---|
| **Univariée** (chaque facteur seul) | classement d'importance fiable, effet chiffré | AUC par facteur |
| **Multivariée** (facteurs non redondants) | poids combinés, signes cohérents | AUC = 0.855 |
| **Random Forest** | contre-vérification non linéaire | AUC = 0.951 |

---

## 1. Classement des facteurs (effet univarié)

Effet = **gain de probabilité de victoire pour +1 écart-type d'avantage** sur
l'adversaire (depuis un match équilibré 50/50). `AUC seul` = pouvoir prédictif du
facteur isolé (0.5 = hasard, 1 = parfait).

| Rang | Facteur | Effet | AUC seul |
|---|---|---|---|
| 1 | **Efficacité au tir (eFG%)** | **+32 %** | 0.81 |
| 2 | % de tirs réussis | +30 % | 0.80 |
| 3 | **Passes décisives** | +24 % | 0.75 |
| 4 | Ratio passes / pertes | +23 % | 0.75 |
| 5 | **% à 3 points** | +22 % | 0.73 |
| 6 | **Rebonds défensifs** | +20 % | 0.71 |
| 7 | Avantage du terrain | +14 % | 0.57 |
| 8 | Pression défensive (INT+CT) | +12 % | 0.64 |
| 9 | Interceptions | +11 % | 0.63 |
| 10 | Taux de pertes de balle | **−10 %** | 0.62 |
| — | Rebonds offensifs, contres, apport du banc | ~ +3 % | ≈0.53 |
| — | Part de tirs à 3pts, dépendance à la star | **≈ 0 %** | 0.50 |

**Modèle multivarié** (signes cohérents, tout tient ensemble) :
eFG **+26 %**, taux de pertes **−16 %**, rebond défensif **+15 %**, rebond
offensif +10 %, pression défensive +10 %, % à 3pts +9 %, avantage terrain +8 %.

**Traduit en « +X → +Y% » (ton format) :**
- **+10 points d'eFG%** de mieux que l'adversaire → **≈ +27 %** de victoire.
- **+10 points de % à 3pts** de mieux → **≈ +14 %**.
- jouer **à domicile** → **+8 à +14 %** (réel mais modéré : AUC 0.57 seul).

---

## 2. Les 4 enseignements

1. **Gagner = être efficace, pas jouer vite.** La *possession* en soi ne pèse
   rien (les 2 équipes en ont ~le même nombre). Ce qui compte = **ce qu'on fait
   de chaque possession** : marquer (eFG, %3pts), ne pas gâcher (pertes).
2. **Le tir à 3 points est le grand discriminant.** Le Random Forest le classe
   n°1 (importance 0.32) : c'est le facteur qui sépare le plus nettement
   gagnants et perdants. Championnat tranché par l'adresse extérieure.
3. **Le collectif bat l'individuel.** Passes décisives et ratio passes/pertes
   sont dans le top ; la *dépendance à une star* a un effet **nul** sur la
   victoire (les équipes mono-joueuse ne gagnent pas plus).
4. **La défense compte** : rebond défensif + interceptions + contres pèsent
   autant que des pans de l'attaque.

> ⚠️ Style ≠ facteur de victoire : « part de tirs à 3pts tentés », « apport du
> banc », « dépendance à la star » ont un effet ≈ 0 → ce sont des **choix de jeu**,
> pas des leviers de résultat.

---

## 3. Global vs par équipe (ta question)

- **Le modèle est global** (toutes équipes) : la « loi générale » du championnat.
  Un modèle *par* équipe = sur-apprentissage (~22 matchs/équipe).
- **Le style se lit par équipe** → `sorties/profil_equipes_zscore.csv`
  (z-score vs ligue, |z|≥1 = se démarque). Exemples lus dans les données :
  - **Bourges** : rebonds (RD/RO) + passes décisives → équipe complète.
  - **Basket Landes** : contres, banc profond, rotation large → défense + profondeur.
  - **Roche Vendée / Landerneau** : très dépendantes de leur star.
  - **Toulouse** : beaucoup de pertes, faible adresse (surtout à 3pts) → profil fragile.
  - **Charnay** : pressing (interceptions) mais faible au rebond défensif.

---

## 4. Limites (à dire dans le rendu)
- **Corrélation ≠ causalité** : un eFG élevé *accompagne* la victoire ; le forcer
  ne la garantit pas mécaniquement.
- **Pas de vraie fatigue** : le calendrier n'a pas de dates → « repos entre matchs »
  non calculable (approché par la profondeur de rotation seulement).
- Championnat uniquement (coupe/playoffs = adversaires hors des 12 équipes ou trop
  peu de matchs).

## Fichiers produits
- `facteurs_victoire.py` — script reproductible (`python analyse/facteurs_victoire.py`)
- `sorties/importance_univariee.csv` — classement principal (tableau §1)
- `sorties/modele_multivarie.csv` — modèle combiné
- `sorties/importance_rf.csv` — Random Forest
- `sorties/profil_equipes_zscore.csv` — style par équipe
- `sorties/facteurs_victoire.png` — graphique
