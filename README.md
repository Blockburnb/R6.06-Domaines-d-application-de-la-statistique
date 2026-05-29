# R6.06 - Domaines d'application de la Statistique

## 📊 Traitement des données de Basketball LFB

Ce projet traite et analyse les données statistiques du basketball féminin français (LFB - Ligue de Basketball Féminin).

Sujet : Quels sont les facteurs qui pèsent le plus pour gagner un match ?
---

## 🚀 Démarrage rapide

### Exécuter le pipeline complet

```bash
cd "Script traitement"
python pipeline.py
```

Le pipeline traite automatiquement tous les données et génère les fichiers finaux en **~10 secondes**.

### Résultat attendu

À la fin, vous verrez :

```
======================================================================
PIPELINE TERMINE AVEC SUCCES
======================================================================

Fichiers finaux disponibles dans: ../data
  - equipes_fusionnees.csv
  - calendrier_resultat_fusionne_elo_calcule.csv
```

---

## 📁 Fichiers d'entrée (Source)

Les fichiers sources doivent être placés dans le dossier `donnée prof/` :

### 1. Dossier `donnée prof/Fichier Equipe/` (12 fichiers CSV)

**Contient** : Les données de **chaque équipe** (joueurs, matchs, statistiques)

**Fichiers** :
- `Angers.csv`
- `Basket landes.csv`
- `Bourges.csv`
- `Charleville.csv`
- `charnay.csv`
- `Chartres.csv`
- `Landerneau.csv`
- `Lyon.csv`
- `Montpellier.csv`
- `Roche vendee.csv`
- `Toulouse.csv`
- `Villeneuve d'ascq.csv`

**Format** : CSV délimité par `;` (point-virgule)

**En-têtes** : Equipe, Saison, Num_match, Competition, dom_ext, Gagne_perdu, Adversaire, ..., JOUEUR, ...

**Contenu** : ~10 000 lignes (environ 800-1000 par équipe)

### 2. Fichier `donnée prof/Calendrier et resultat.xlsx`

**Contient** : Le **calendrier et les résultats** de tous les matchs

**Format** : Classeur Excel avec une **feuille par saison**
- Feuille `24-25` : Saison 2024-2025
- Feuille `25-26` : Saison 2025-2026

**Colonnes** : Journée, Domicile, Extérieur, Score domicile, Score Extérieur, Derby

**Contenu** : 264 matchs (132 par saison)

### 3. Fichier `donnée prof/Classement ELO LFB.xlsx`

**Contient** : Les **ELO initiaux** des équipes (avant la saison 24-25)

**Format** : Classeur Excel simple

**Colonnes** : Equipe, ELO

**Contenu** : 12 équipes avec leur ELO initial

---

## 📤 Fichiers de sortie (Résultats)

Les fichiers finaux sont générés dans le dossier `/data/` à la racine du repo.

### 1. `data/equipes_fusionnees.csv`

**Contient** : Fusion de **tous les fichiers équipes**

**Taille** : 10 008 lignes

**Colonnes** : 
```
Equipe, Saison, Num_match, Competition, dom_ext, Gagne_perdu, 
Adversaire, Capitaine, Starter/bench, Joueur, Minutes, Secondes,
Secondes(minutes), Tps_jeu_decimal, Tirs_marques, Tirs_tentes, %Tirs,
2pts_marques, 2pts_tentes, %2pts, 3pts_marques, 3pts_tentes, %3pts,
LF_marques, LF_tentes, %LF, Pts_apres_balles_perdues, Points_int,
Point_2eme_chance, Points_CA, Points_banc, Ecart_max, Serie_max,
Pts, RO, RD, RT, PD, BP, INT, CT, CTS, F, FPR, +/-, EVAL, N, JOUEUR
```

**Usage** : Données complètes de tous les joueurs et matchs

### 2. `data/calendrier_resultat_fusionne_elo_calcule.csv`

**Contient** : **Calendrier complet avec tous les ELO**

**Taille** : 264 lignes (1 par match)

**Colonnes** :
```
Saison, Journee, Domicile, Exterieur, Score domicile, Score Exterieur, Derby,
ELO domicile avant match, ELO exterieur avant match,
ELO domicile apres match, ELO exterieur apres match
```

**Usage** : 
- Analyse du classement ELO par équipe
- Évolution de l'ELO au fil des saisons
- Comparaison des forces respectives

---

## 📊 Exemple de données de sortie

### Calendrier avec ELO

```
Saison;Journee;Domicile;Exterieur;Score domicile;Score Exterieur;Derby;
ELO domicile avant match;ELO exterieur avant match;
ELO domicile apres match;ELO exterieur apres match

24-25;1;Angers;Tarbes;73;59;0;1465.0;1485.0;1483.51;1471.78
24-25;1;Charleville-Mézières;Basket Landes;61;94;0;1520.0;1600.0;1506.46;1609.67
...
```

### Interprétation

- **Angers** : ELO 1465 → 1483.51 (gagne +18.51)
- **Tarbes** : ELO 1485 → 1471.78 (perd -13.22)

---

## 🧮 Formule ELO utilisée

Le pipeline calcule les ELO selon la **formule ELO classique** avec ajustements :

```
P = 1 / (1 + 10^((ELO_adversaire - ELO_equipe) / 400))
Nouvel_ELO = Ancien_ELO + K * (R - P)

Où :
- K = 30 de base
  + 5 pour match à domicile
  - 5 pour match à l'extérieur
  + 10 supplémentaires en cas de derby
- R = 1 (victoire) ou 0 (défaite)
- P = Probabilité de victoire estimée avant le match
```

---

## 🏗️ Structure du projet

```
R6.06-Domaines-d-application-de-la-statistique/
├── README.md                                # Ce fichier
├── donnée prof/                             # ✅ Source (fournie)
│   ├── Fichier Equipe/                      #    12 fichiers CSV
│   ├── Calendrier et resultat.xlsx          #    Calendrier
│   └── Classement ELO LFB.xlsx              #    ELO initiaux
├── Script traitement/                       # ✅ Traitement
│   ├── pipeline.py                          #    Script principal
│   ├── README.md                            #    Doc détaillée
│   ├── modules/                             #    Scripts traitement
│   │   ├── fusion_fichier_equipes.py
│   │   ├── fusion_calendrier_resultat.py
│   │   ├── enrichir_calendrier_elo.py
│   │   └── calculer_elo.py
│   ├── data_intermediaire/                  #    Fichiers externes
│   │   ├── equipes_fusionnees.csv
│   │   ├── calendrier_resultat_fusionne.csv
│   │   ├── calendrier_resultat_fusionne_elo.csv
│   │   └── calendrier_resultat_fusionne_elo_calcule.csv
│   └── verification/                        #    Vérification
│       ├── verifier_fusion.py
│       ├── verifier_fusion_calendrier.py
│       └── verifier_enrichissement_calendrier_elo.py
└── data/                                    # ✅ Résultats finaux
    ├── equipes_fusionnees.csv               #    Données équipes
    └── calendrier_resultat_fusionne_elo_calcule.csv  # Calendrier avec ELO
```

---

## 📋 Processus de traitement

Le pipeline exécute automatiquement 5 étapes :

1. **Fusion des équipes** (10 008 enregistrements)
   - Lit 12 fichiers CSV
   - Normalise les en-têtes
   - Fusionne en 1 fichier
   
2. **Fusion du calendrier** (264 matchs)
   - Lit le classeur Excel
   - Extrait chaque saison
   - Fusionne en 1 fichier

3. **Enrichissement ELO** (264 matchs)
   - Charge les ELO initiaux
   - Les ajoute au calendrier
   
4. **Calcul ELO** (264 matchs)
   - Calcule l'ELO après chaque match
   - Propage les valeurs
   
5. **Vérifications** (3 contrôles)
   - Valide la fusion équipes
   - Valide la fusion calendrier
   - Valide l'enrichissement ELO

---

## ⚙️ Configuration

### Requirements

```
Python 3.7+
pandas
openpyxl
```

### Installation

```bash
pip install pandas openpyxl
```

### Exécution

```bash
cd "Script traitement"
python pipeline.py
```

---

## 🔍 Documentation complète

Pour plus de détails, consultez :

- **[Script traitement/README.md](Script%20traitement/README.md)** - Guide complet du pipeline
- **[Script traitement/modules/README.md](Script%20traitement/modules/README.md)** - Doc des modules
- **[Script traitement/verification/README.md](Script%20traitement/verification/README.md)** - Doc des vérifications

---

## 💾 Données générées

Le pipeline génère :

### Fichiers intermédiaires (conservé pour débogage)
- `equipes_fusionnees.csv` (10 008 lignes)
- `calendrier_resultat_fusionne.csv` (264 lignes)
- `calendrier_resultat_fusionne_elo.csv` (264 lignes)
- `calendrier_resultat_fusionne_elo_calcule.csv` (264 lignes)

### Fichiers finaux (dans /data)
- `equipes_fusionnees.csv` 
- `calendrier_resultat_fusionne_elo_calcule.csv`

---

## 📝 Notes

- ✅ Le pipeline est **idempotent** (peut être relancé ∞ fois)
- ✅ Les **vérifications** garantissent l'intégrité des données
- ✅ Les **ELO** sont calculés automatiquement et propagés
- ✅ Les fichiers intermédiaires sont **conservés** pour débogage
- ⏱️ Durée typique : **~10 secondes**

---

## 📞 Support

Pour questions ou problèmes :
1. Vérifier que les sources existent dans `donnée prof/`
2. Consulter les logs du pipeline
3. Relancer `python pipeline.py`
4. Lire la documentation détaillée dans les README spécifiques

---

## 📚 Context du projet

**Thème** : Pronostique  
**Problématique** : Quel critère est le plus important à regarder avant de faire un pronostique ?

### Vocabulaire des statistiques

- **Pts** : Points
- **RO** : Rebonds offensifs (après tir manqué, l'équipe récupère la balle)
- **RD** : Rebonds défensifs (l'équipe adverse après tir récupère la balle)
- **RT** : Rebonds totaux (RO + RD)
- **PD** : Passe décisive (dernier joueur qui fait la passe avant panier)
- **BP** : Balle perdue
- **INT** : Interception
- **CT** : Contre (blocage de la balle après tir)
- **CTS** : Contre subis
- **F** : Fautes (Max 5 fautes/joueur, sinon sortis)
- **FPR** : Faute provoquée (victime de la faute)
- **+/-** : Écart quand le joueur quitte le terrain
- **EVAL** : Impact du joueur sur le match
- **%X_points** : Répartition du X_points par tirs tentés
- **LF** : Lancer franc
- **pts_int** : Points à l'intérieur de la raquette
- **2E chance** : Points après rebond offensif (même possession)
- **points_CA** : Points contre-attaque
- **points_banc** : Points des joueurs du banc
- **série_max** : Plus grand nombre de points marqués consécutifs
