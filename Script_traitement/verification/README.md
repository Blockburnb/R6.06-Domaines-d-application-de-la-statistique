# Scripts de Vérification - Documentation

Ce dossier contient les scripts de vérification qui contrôlent l'intégrité des données après chaque étape du traitement.

## 📋 Vue d'ensemble

Chaque script vérifie qu'aucune donnée n'a été perdue ou dégradée lors du traitement.

| Script | Vérifie | Contrôles |
|--------|---------|-----------|
| `verifier_fusion.py` | Fusion des équipes | Nombre de lignes, équipes complètement tracées |
| `verifier_fusion_calendrier.py` | Fusion calendrier | Nombre de matchs, saisons complètes |
| `verifier_enrichissement_calendrier_elo.py` | Enrichissement ELO | Nombre de matchs, équipes initialisées |

---

## ✅ verifier_fusion.py

### Logique

Ce script vérifie que la fusion des fichiers équipes a conservé tous les enregistrements.

#### Processus de vérification

1. **Charge les données source** : Lit tous les CSV du dossier `donnée prof/Fichier Equipe/`
2. **Normalise les données** : Applique le même traitement que `fusion_fichier_equipes.py`
3. **Compte les enregistrements** : Par équipe et au total
4. **Charge le fichier fusionné** : Lit le CSV de sortie
5. **Compare** :
   - Le nombre total d'enregistrements
   - Le nombre d'enregistrements par équipe
   - Les données ligne par ligne (hash)
6. **Reporte** les écarts détectés

### Utilisation

```bash
cd verification
python verifier_fusion.py
```

### Output

```
Verification de la fusion
- Total source:  10008
- Total fusion:  10008
- Controle par equipe:
  OK | Angers: source=890, fusion=890
  OK | Basket landes: source=1007, fusion=1007
  ...
RESULTAT: OK - aucune ligne sautee, aucune degradation detectee.
```

### Sortie en cas d'erreur

```
KO | Montpellier: source=886, fusion=850  # 36 lignes manquantes

RESULTAT: KO - des ecarts ont ete detectes.
Detail des ecarts:
- Lignes manquantes: 36
- Lignes en trop: 0

Exemples de lignes manquantes:
- x1 | Montpellier;2024;1;LFB;dom;G;Lyon;...
```

---

## 📅 verifier_fusion_calendrier.py

### Logique

Ce script vérifie que la fusion du calendrier n'a perdu aucun match.

#### Processus de vérification

1. **Lit le classeur Excel** `Calendrier et resultat.xlsx`
2. **Extrait chaque feuille** (saison)
3. **Normalise** les en-têtes et données
4. **Compte les matchs** par saison
5. **Charge le CSV fusionné**
6. **Compare** :
   - Le nombre total de matchs
   - Le nombre de matchs par saison
   - Les matchs ligne par ligne
7. **Reporte** les écarts

### Utilisation

```bash
cd verification
python verifier_fusion_calendrier.py
```

### Output

```
Verification de la fusion du calendrier
- Total source:  264
- Total fusion:  264
- Controle par saison:
  OK | 24-25: source=132, fusion=132
  OK | 25-26: source=132, fusion=132

RESULTAT: OK - aucune ligne sautee, aucune degradation detectee.
```

### Exemple d'erreur

```
KO | 24-25: source=132, fusion=131  # 1 match manquant

RESULTAT: KO - des ecarts ont ete detectes.
Detail des ecarts:
- Lignes manquantes: 1

Exemples de lignes manquantes:
- x1 | 24-25;1;Angers;Tarbes;73;59;0
```

### Points de contrôle

- ✓ Nombre total de matchs : 264 (132 + 132)
- ✓ Toutes les colonnes présentes et correctes
- ✓ Intégrité des données (pas de fusions mal faites)

---

## 🎯 verifier_enrichissement_calendrier_elo.py

### Logique

Ce script vérifie que l'enrichissement pour les ELO a correctement initialisé les équipes.

#### Processus de vérification

1. **Charge les ELO initiaux** depuis `Classement ELO LFB.xlsx`
2. **Charge le calendrier** fusionné
3. **Simule l'enrichissement** pour générer les données attendues
4. **Charge le CSV enrichi**
5. **Compare** :
   - Le nombre de lignes
   - Les équipes initialisées en 24-25
   - Les données ligne par ligne
6. **Reporte** les écarts

### Utilisation

```bash
cd verification
python verifier_enrichissement_calendrier_elo.py
```

### Output

```
Verification de l'enrichissement ELO
- Total source:  264
- Total enrichi: 264
- Equipes initialisees en 24-25:
  OK | angers: source=1, enrichi=1
  OK | basketlandes: source=1, enrichi=1
  ...
  OK | villeneuvedascq: source=1, enrichi=1

RESULTAT: OK - aucune ligne sautee, aucune degradation detectee.
```

### Points de contrôle

- ✓ **12 équipes** présentes en 24-25 avec ELO initial
- ✓ Pas de doublons
- ✓ Tous les matchs conservés
- ✓ Les 4 colonnes ELO présentes

### Équipes attendues

```
angers, basketlandes, bourges, charlevillemezieres, charnay, 
chartres, landerneau, lattesmontpellier, lyon, rochevendee, 
tarbes, villeneuvedascq
```

---

## 🔄 Flux de vérification

```
Pipeline exécute :
  1. fusion_fichier_equipes.py
     ↓
  2. verifier_fusion.py (vérifie)
     ↓
  3. fusion_calendrier_resultat.py
     ↓
  4. verifier_fusion_calendrier.py (vérifie)
     ↓
  5. enrichir_calendrier_elo.py
     ↓
  6. verifier_enrichissement_calendrier_elo.py (vérifie)
     ↓
  7. calculer_elo.py
     ↓
  [Pas de vérification pour ELO calculés - validés visuellement]
```

---

## 📝 Utilisation indépendante

Chaque script peut être lancé indépendamment pour déboguer une étape spécifique :

```bash
# Vérifier juste la fusion équipes
cd Script traitement/verification
python verifier_fusion.py

# Vérifier juste le calendrier
python verifier_fusion_calendrier.py

# Vérifier juste l'enrichissement ELO
python verifier_enrichissement_calendrier_elo.py
```

## 🎯 Critères de réussite

Pour chaque script, la réussite est définie par :

1. ✓ **Aucune ligne manquante** : `Lignes manquantes: 0`
2. ✓ **Aucune ligne en trop** : `Lignes en trop: 0`
3. ✓ **Tous les éléments contrôlés OK** : Les listes d'équipes/saisons affichent toutes `[OK]`
4. ✓ **Message final** : `RESULTAT: OK - aucune ligne sautee, aucune degradation detectee.`

## 🚨 Interprétation des erreurs

### "Lignes manquantes"
Les enregistrements présents en source mais absent du fichier traité = **perte de données**

### "Lignes en trop"
Les enregistrements présents dans le fichier traité mais pas en source = **données dupliquées/altérées**

### "KO" pour une équipe/saison
Le nombre d'enregistrements ne correspond pas exactement

---

## 💡 Conseils de débogage

Si un test échoue :

1. Vérifier les fichiers sources dans `donnée prof/`
2. Vérifier les fichiers intermédiaires dans `data_intermediaire/`
3. Consulter les "Exemples de lignes manquantes/en trop" pour identifier le problème
4. Réexécuter le pipeline complet : `python ../pipeline.py`
