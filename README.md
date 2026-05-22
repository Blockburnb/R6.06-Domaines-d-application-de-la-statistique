Thème :
Pronostique

Problématique :
Quel critère est le plus important à regarder avant de faire un pronostique ?

Rôles : 
F :
H :
L :
T :

Vocs : 

Pts : Points
Ro rebonds offensifs -> quand tir manqué, l'équipe recup la balle après 
Rd -> rebonds défensif, l'équipe adverse après tir recupere la balle
RT -> Rebonds totaux, off + def
PD -> Passe décisive, dernier joueur qui fait la passe avant panier
BP -> Balle perdu, le joueur perd la balle
INT -> Interception
CT -> Contre, blocage de la balle après tire
CTS -> Contre subis
F -> Fautes  (Max 5 fautes/joueurs sinon sortis du joueur pour le match)
FPR-> Faute provoqué (victime de la faute)
+/- -> Ecart quand le joueur sort du terrain
EVAL -> Impact du joueur sur le match, calculé selon actions +/- ;départ à 0; tout les points ont la même valeurs sauf certains cas
%X_points -> Répartition du X_points par tirs tentés durant le match
LF -> Lancer franc
pts_int -> points à l'intérieur de la raquette
2E chance -> après rebond offensif, on est dans la meme possession, et si on marque le 2eme panier on est sur une 2eme chance, 
points_CA -> points contre attaque
points_banc -> points joueurs qui ne sont pas dans le 5 de départ
série max -> plus grand nb de pts marqués sans points marqués par l'adversaire
-> Minimum 3 joueurs sur le banc
-> Feuille classement elo, ELO -> elo début saison 24-25

Scripts de traitement CSV

Deux scripts Python ont été ajoutés dans le dossier `Script traitement/` pour consolider et contrôler les données des équipes.

1) Fusion des fichiers d'équipe

Script: `Script traitement/fusion_fichier_equipes.py`

Ce script:
- lit tous les fichiers `.csv` dans `donnée prof/Fichier Equipe/`
- crée un fichier unique `Script traitement/equipes_fusionnees.csv`
- ajoute la colonne `Equipe` à partir du nom du fichier source
- conserve l'ordre d'entêtes demandé
- normalise les variantes d'entête (ex: `Adveresaire` -> `Adversaire`)

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/fusion_fichier_equipes.py"
```

2) Vérification de la fusion

Script: `Script traitement/verifier_fusion.py`

Ce script vérifie que la fusion est correcte, notamment:
- entêtes du fichier fusionné
- nombre total de lignes (source vs fusion)
- nombre de lignes par équipe
- comparaison du contenu ligne par ligne pour détecter les lignes manquantes, en trop, ou dégradées

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/verifier_fusion.py"
```

Interprétation du résultat:
- `RESULTAT: OK` -> fusion valide
- `RESULTAT: KO` -> écarts détectés, détails affichés dans la sortie

3) Fusion du calendrier et des résultats

Script: `Script traitement/fusion_calendrier_resultat.py`

Ce script:
- lit le classeur `donnée prof/Calendrier et resultat.xlsx`
- fusionne les feuilles `Calendrier 24-25` et `Calendrier 25-26`
- génère `Script traitement/calendrier_resultat_fusionne.csv`
- ajoute la colonne `Saison` avec `24-25` ou `25-26` selon la feuille source

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/fusion_calendrier_resultat.py"
```

4) Vérification de la fusion du calendrier

Script: `Script traitement/verifier_fusion_calendrier.py`

Ce script vérifie que la fusion du calendrier est correcte, notamment:
- entêtes du fichier fusionné
- nombre total de lignes (source vs fusion)
- nombre de lignes par saison
- comparaison du contenu ligne par ligne pour détecter les lignes manquantes, en trop, ou dégradées

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/verifier_fusion_calendrier.py"
```

Interprétation du résultat:
- `RESULTAT: OK` -> fusion calendrier valide
- `RESULTAT: KO` -> écarts détectés, détails affichés dans la sortie

5) Enrichissement ELO du calendrier

Script: `Script traitement/enrichir_calendrier_elo.py`

Ce script:
- lit `donnée prof/Classement ELO LFB.xlsx`
- lit `Script traitement/calendrier_resultat_fusionne.csv`
- génère `Script traitement/calendrier_resultat_fusionne_elo.csv`
- ajoute les colonnes `ELO domicile avant match`, `ELO extérieur avant match`, `ELO domicile après match`, `ELO extérieur après match`
- renseigne uniquement les premiers matchs de chaque équipe en saison `24-25` avec les valeurs entières de la colonne `ELO` du classement
- laisse les colonnes `après match` vides pour le moment, en attente de la suite du calcul

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/enrichir_calendrier_elo.py"
```

6) Vérification de l'enrichissement ELO

Script: `Script traitement/verifier_enrichissement_calendrier_elo.py`

Ce script vérifie que l'enrichissement ELO est correct, notamment:
- entêtes du fichier enrichi
- nombre total de lignes
- équipes correctement initialisées sur leurs premiers matchs de 24-25
- comparaison du contenu ligne par ligne pour détecter les lignes manquantes, en trop, ou dégradées

Commande:

```bash
/workspaces/R6.06-Domaines-d-application-de-la-statistique/.venv/bin/python "Script traitement/verifier_enrichissement_calendrier_elo.py"
```

Interprétation du résultat:
- `RESULTAT: OK` -> enrichissement ELO valide
- `RESULTAT: KO` -> écarts détectés, détails affichés dans la sortie
