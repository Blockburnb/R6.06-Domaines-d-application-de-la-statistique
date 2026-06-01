# Fiche chiffres : tout pour rédiger les 2 pages

Tous les nombres citables, regroupés par thème. Chaque chiffre est reproductible dans les notebooks 00 à 07. À coller dans le modèle du prof une fois reçu.

Problématique : quels sont les facteurs qui pèsent le plus pour gagner un match en LFB ?

## Données et méthode

- Sources : stats joueuse par match (saisons 23-24 et 24-25), calendrier avec ELO (24-25 et 25-26), liste des joueuses sur 11 saisons (2015 à 2026).
- Volumes : 438 équipe-matchs, 358 confrontations appariées équipe contre adversaire, 264 matchs de calendrier, 20 équipes-saisons, 1927 joueuses-saisons.
- Idée centrale : on raisonne en différentiel équipe moins adversaire. Une stat ne compte que comparée à celle d'en face.
- Distinction clé : expliquer la victoire (stats mesurées pendant le match) n'est pas la prédire (on n'a alors que l'ELO et la forme).
- Outils : classement univarié par AUC, modèle logistique multivarié, Random Forest en garde-fou, tests de significativité (Mann-Whitney, intervalle de confiance bootstrap, taille d'effet de Cohen), validation croisée, walk-forward pour les paris.

## 1. Ce qui fait gagner (facteurs pendant le match)

Classement par pouvoir discriminant (AUC du facteur seul), avec taille d'effet de Cohen. Tous les facteurs de tête sont significatifs à p inférieur à 0,001.

| Facteur | AUC seul | Cohen d | Significatif |
|---|---|---|---|
| Efficacité au tir (eFG%) | 0,92 | 1,93 | oui |
| Pourcentage de tirs réussis | 0,91 | 1,86 | oui |
| Passes décisives | 0,85 | 1,47 | oui |
| Pourcentage à 3 points | 0,79 | 1,15 | oui |
| Rebonds défensifs | 0,78 | 1,10 | oui |
| Pression défensive (interceptions plus contres) | 0,68 | 0,66 | oui |
| Taux de pertes de balle | 0,68 | -0,65 | oui |
| Interceptions | 0,67 | 0,61 | oui |
| Contres, rebonds offensifs, part de tirs à 3pts | environ 0,50 | proche de 0 | non |

- Modèle multivarié sur variables non redondantes : AUC environ 0,99 en validation croisée. Très élevé parce que ces stats, mesurées pendant le match, suivent de près le résultat.
- Random Forest (garde-fou non linéaire) : AUC environ 0,97. Place le 3 points en tête de ses importances.
- Lecture : on gagne en étant efficace, pas en jouant vite. La possession en soi ne pèse rien (les deux équipes en ont autant). Le collectif (passes décisives) bat l'individuel.

## 2. Offensif ou défensif, loin ou près du panier

- Profil moyen d'une équipe par match : 72 points, 76 possessions.
- Répartition des points : 43 % près du panier (raquette), 28 % de loin (3 points), 14 % en contre-attaque, 13 % de seconde chance (ces deux dernières catégories se recoupent avec les autres).
- Championnat à dominante intérieure, mais c'est l'avantage au 3 points qui sépare le mieux gagnants et perdants (AUC 0,61, contre 0,53 pour la raquette).
- Formule : on marque surtout près, on fait la différence de loin.

## 3. Avantage du terrain

- Brut : 59,8 % de victoires à domicile, marge moyenne de 2,7 points.
- Net du niveau (à ELO égal) : 62,8 % de victoires, soit environ 3 points.
- Repère : 100 points d'ELO d'avance valent environ 4,4 points d'écart.
- Lecture : réel mais modéré, le terrain départage surtout les matchs serrés.

## 4. Prédire avant le match

- Le favori ELO gagne 68,2 % des matchs (132 matchs de 24-25). Le pronostic naïf "le domicile gagne" plafonne à 59,8 %.
- Le favori perd environ une fois sur trois (32 % de surprises).
- Régression logistique ELO plus forme récente : AUC 0,755, environ 69 % de bons pronostics. La forme récente est le deuxième facteur après l'ELO.
- Écart de points prédit à environ plus ou moins 10 points (le basket reste très variable).
- Probabilités bien calibrées : score de Brier 0,194 contre 0,250 pour le naïf.
- Le classement final se prédit dès la mi-saison, à moins d'un rang d'erreur.

## 5. La taille du cinq de départ

- L'équipe qui aligne plus de titulaires d'au moins 1,85 m que l'adversaire gagne 68 % de ses matchs. À égalité de grandes, c'est 50 %. Avec moins de grandes, 32 %.
- Effet significatif (corrélation 0,29, p inférieur à 0,001). C'est le nombre de grandes qui compte, pas la taille moyenne.
- Surprise : ce n'est pas la stabilité du cinq qui fait gagner (effet nul), c'est sa taille.
- Nuance : la taille va souvent avec le budget, donc l'effet n'est pas purement mécanique.

## 6. Les joueuses

Panorama sur 11 saisons :

- Part d'étrangères stable autour de 34 %, petit pic à 39 % en 2020-21 (COVID), repli récent de 32 % à 29 %.
- Âge moyen stable autour de 24 à 25 ans, taille moyenne environ 1,81 m. Pas de rajeunissement net.

Performance et âge (joueuses à au moins 200 minutes) :

- Pic de performance vers 28-29 ans. EVAL moyen qui monte de 6,7 à 21 ans jusqu'à 10,9 à 28-29 ans.
- Le championnat valorise l'expérience plus que la jeunesse.

Fidélité et turnover :

- Le championnat renouvelle environ 60 % de ses effectifs chaque été.
- 44 % des joueuses présentes sur plusieurs saisons restent fidèles à un seul club.
- Club le plus stable : Bourges (50 % de turnover). Le plus volatil : Charleville (66 %).

Talents :

- Pépite : D. Malonga (Lyon, 19 ans), rendement par minute parmi les meilleurs de la ligue (EVAL par minute 0,62), sur 22 matchs et 33 minutes de moyenne.
- Sous-cotées (fort rendement, minutes plafonnées) : K. Diaby et K. Alexander (Bourges), autour de 0,84 d'EVAL par minute sur 22 minutes.

Étrangères contre françaises (par joueuse-saison) :

- Étrangères : 25 minutes, 9,3 points, EVAL 10,1. Françaises : 17 minutes, 4,9 points, EVAL 5,3.
- Les étrangères jouent 1,5 fois plus et ont un impact 2 fois supérieur, ce sont les cadres recrutées.
- La corrélation entre part d'étrangères et victoires est de 0,39 (lien positif modéré). L'idée qu'elles jouent moins collectif est infirmée.

## 7. Les équipes

- Bourges est le patron : meilleur différentiel de points, gagne partout (95 % à domicile, 68 % à l'extérieur), et reste la bête noire de presque toute la ligue.
- Forteresses et écarts domicile contre extérieur : Lyon montre le plus grand écart (59 % chez elle, 23 % dehors). Basket Landes et Charleville dépendent aussi de leur salle. Chartres est faible des deux côtés (23 %).
- Corrélations au niveau équipe-saison : avantage d'efficacité au tir et victoires 0,85, passes décisives 0,80, rebond défensif 0,70.
- Les effectifs changent beaucoup d'une saison à l'autre. Villeneuve d'Ascq, dominante en 23-24, s'effondre en 24-25.

## 8. Résultats négatifs et limites (pour la partie recul)

- Le style de jeu ne prédit pas la victoire. Ajouter le style à l'ELO dégrade la prédiction (AUC de 0,80 à 0,77). Seul le niveau compte.
- La stabilité du cinq de départ n'a aucun effet (corrélation proche de 0, non significative).
- La dépendance à une star est un marqueur de faiblesse (corrélation de -0,69 avec les victoires), pas une source d'imprévisibilité.
- Le plus/minus individuel est confondu par la force de l'équipe (46 % de sa variance vient de l'équipe-saison), inutile pour juger une joueuse.
- Prédire les playoffs est infaisable ici : pas d'ELO en phase finale, et les saisons disponibles se recouvrent mal.
- Les paris ne sont pas rentables : environ 70 % de bons pronostics, mais le bookmaker garde l'avantage.
- Limite générale : corrélation n'est pas causalité. Ces facteurs accompagnent la victoire, les forcer ne la garantit pas. Les confrontations directes reposent sur 3 à 4 matchs par paire, donc indicatives seulement.

## Phrases prêtes à coller

- En LFB, on gagne en étant efficace, pas en jouant vite : l'efficacité au tir est de loin le premier facteur de victoire.
- Le tir à 3 points est le grand discriminant du championnat, alors que l'essentiel des points se marque près du panier.
- L'ELO pronostique deux matchs sur trois, mais un sur trois reste une surprise : le basket garde une part d'aléa irréductible.
- À niveau égal, jouer chez soi vaut environ trois points.
- Aligner un cinq plus grand que l'adversaire fait passer les chances de victoire de une sur trois à deux sur trois.
- Le championnat valorise l'expérience : la performance culmine vers 28-29 ans, et les effectifs se renouvellent à 60 % chaque été.
- Ce qui ne fait pas gagner compte aussi : ni le style de jeu, ni la stabilité du cinq, ni la dépendance à une star.
