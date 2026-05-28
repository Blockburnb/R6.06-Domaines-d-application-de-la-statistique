# Modules de Traitement - Documentation

Ce dossier contient tous les modules de traitement qui composent le pipeline. Chaque module peut être importé et utilisé indépendamment ou via le pipeline principal.

## 📋 Vue d'ensemble

| Module | Rôle | Entrée | Sortie |
|--------|------|--------|--------|
| `fusion_fichier_equipes.py` | Fusionne les fichiers CSV des équipes | Dossier equipes + résultats | CSV fusionné |
| `fusion_calendrier_resultat.py` | Extrait calendrier et résultats du classeur Excel | XLSX calendrier | CSV calendrier |
| `enrichir_calendrier_elo.py` | Ajoute les ELO initiaux | CSV calendrier + XLSX ELO | CSV avec ELO initiaux |
| `calculer_elo.py` | Calcule l'ELO après chaque match | CSV avec ELO initiaux | CSV avec ELO calculés |

---

## 🔧 fusion_fichier_equipes.py

### Logique

Ce module fusionne tous les fichiers CSV des équipes en un seul fichier unifié. Il :

1. **Parcourt** tous les fichiers CSV dans `donnée prof/Fichier Equipe/`
2. **Normalise** les en-têtes selon les alias connus
3. **Ajoute** une colonne "Equipe" pour identifier la source
4. **Filtre** les lignes vides
5. **Exporte** un CSV unique avec en-têtes standardisés

### Utilisation

```python
from modules.fusion_fichier_equipes import main

output_path = Path("data_intermediaire/equipes_fusionnees.csv")
main(output_path)
```

### En-têtes standardisés

Tous les fichiers sont normalisés selon ces 48 en-têtes :
```
Equipe, Saison, Num_match, Competition, dom_ext, Gagne_perdu, 
Adversaire, Capitaine, Starter/bench, Joueur, Minutes, Secondes, ...
```

### Gestion des erreurs

- ❌ Lance une exception si aucun CSV trouvé dans le dossier source
- ⚠️ Ignore les lignes totalement vides
- 🔄 Tente plusieurs encodages (UTF-8, CP1252, Latin-1)

---

## 📅 fusion_calendrier_resultat.py

### Logique

Ce module extrait et fusionne le calendrier et les résultats du classeur Excel. Il :

1. **Lit** le fichier `Calendrier et resultat.xlsx`
2. **Parse** le fichier XLSX en tant qu'archive ZIP
3. **Extrait** les valeurs partagées (sharedStrings.xml)
4. **Extrait** chaque feuille par saison
5. **Normalise** les en-têtes
6. **Valide** la présence des colonnes requises
7. **Exporte** un CSV unifié

### Utilisation

```python
from modules.fusion_calendrier_resultat import main

output_path = Path("data_intermediaire/calendrier_resultat_fusionne.csv")
main(output_path)
```

### En-têtes requis (case-insensitive, normalizés)

```
Saison, Journee, Domicile, Exterieur, Score domicile, Score Exterieur, Derby
```

### Structure du fichier XLSX

- Chaque feuille = une saison (ex: "24-25", "25-26")
- Colonnes requises : Journée, Domicile, Extérieur, Scores, Derby
- Extraction regex des saisons : `(\d{2}-\d{2})`

---

## 🎯 enrichir_calendrier_elo.py

### Logique

Ce module ajoute les ELO initiaux au calendrier. Il :

1. **Charge** les ELO initiaux depuis `Classement ELO LFB.xlsx`
2. **Normalise** les noms d'équipes pour comparaison
3. **Charge** le calendrier fusionné
4. **Pour la saison 24-25** :
   - Ajoute l'ELO de chaque équipe à son premier match
5. **Pour les autres saisons** :
   - Duplique les ELO finaux de la saison précédente
6. **Exporte** le calendrier enrichi

### Utilisation

```python
from modules.enrichir_calendrier_elo import main

input_path = Path("data_intermediaire/calendrier_resultat_fusionne.csv")
output_path = Path("data_intermediaire/calendrier_resultat_fusionne_elo.csv")
main(input_path, output_path)
```

### En-têtes d'entrée

```
Saison, Journee, Domicile, Exterieur, Score domicile, Score Exterieur, Derby
```

### En-têtes de sortie

```
[En-têtes entrée] + ELO domicile avant match, ELO extérieur avant match, 
                     ELO domicile après match, ELO extérieur après match
```

### Normalization des équipes

Les noms d'équipes sont normalisés pour la comparaison :
- `Lattes Montpellier` → `lattesmontpellier`
- `Roche Vendée` → `rochevendee`
- `Villeneuve d'Ascq` → `villeneuvedascq`

---

## 📊 calculer_elo.py

### Logique

Ce module calcule l'ELO après chaque match selon la formule ELO classique. Il :

1. **Crée** un dictionnaire pour tracker les ELO actuels
2. **Pour chaque match** :
   - Récupère les ELO avant match
   - Si ELO manquant → assigne ELO défaut (1500)
   - Calcule la probabilité de victoire : `P = 1 / (1 + 10^((ELO_opp - ELO) / 400))`
   - Calcule K avec ajustements (domicile/extérieur/derby)
   - Applique la formule : `Nouvel_ELO = Ancien_ELO + K * (R - P)`
3. **Propage** les ELO calculés aux matchs suivants
4. **Exporte** le calendrier avec ELO finaux

### Utilisation

```python
from modules.calculer_elo import main

input_path = Path("data_intermediaire/calendrier_resultat_fusionne_elo.csv")
output_path = Path("data_intermediaire/calendrier_resultat_fusionne_elo_calcule.csv")
main(input_path, output_path)
```

### Formule ELO utilisée

```
P = 1 / (1 + 10^((ELO_adversaire - ELO_equipe) / 400))
Nouvel_ELO = Ancien_ELO + K * (R - P)

Où :
- K = 30 de base
  + 5 pour match à domicile
  - 5 pour match à l'extérieur
  + 10 supplémentaires en cas de derby (appliqué aux deux)
- R = 1 (victoire) ou 0 (défaite)
- P = Probabilité de victoire estimée
```

### Cas particuliers

- ✓ **ELO initial manquant** → 1500 assigné par défaut
- ✓ **Score égal** → Traité comme défaite (R = 0)
- ✓ **Derby** → Ajustement +10 aux deux équipes

---

## 🔄 Flux de données

```
donnée prof/
  ├── Fichier Equipe/*.csv
  │   ↓
fusion_fichier_equipes.py
  → equipes_fusionnees.csv
  
donnée prof/
  └── Calendrier et resultat.xlsx
      ↓
fusion_calendrier_resultat.py
  → calendrier_resultat_fusionne.csv
      ↓
enrichir_calendrier_elo.py (utilise Classement ELO LFB.xlsx)
  → calendrier_resultat_fusionne_elo.csv
      ↓
calculer_elo.py
  → calendrier_resultat_fusionne_elo_calcule.csv
```

---

## 📝 Notes importantes

### Encodages supportés
- UTF-8 (with BOM)
- CP1252
- Latin-1

### Performance
- Fusion équipes : ~10 000 lignes en <1s
- Fusion calendrier : ~264 matchs en <1s
- Enrichissement ELO : ~264 matchs en <1s
- Calcul ELO : ~264 matchs en <1s

### Robustesse
- Normalisation des espaces et accents
- Gestion des données manquantes
- Validation des en-têtes
- Propagation automatique des ELO entre matchs
