# Analyse — Data mining LFB

Analyse statistique du championnat de basket féminin (LFB) :
**qu'est-ce qui fait gagner un match, et peut-on le prédire ?**

## Organisation

```
analyse/
├── outils.py            # fonctions communes (chargement, noms, ELO, joueuses)
├── notebooks/           # 1 notebook par thème — à lire dans l'ordre
├── resultats/           # CSV et graphiques générés (1 sous-dossier par thème)
└── scripts_originaux/   # archives : scripts .py et synthèses .md de travail
```

## Les notebooks (ordre de lecture)

| # | Notebook | Question | Résultat clé |
|---|----------|----------|--------------|
| 01 | `facteurs_victoire` | Quels facteurs font gagner ? | efficacité au tir, 3pts, passes décisives, rebond défensif |
| 02 | `exploratoire` | Forces, bêtes noires, pronos ELO, nationalité | Bourges domine ; ELO pronostique ~68 % ; étrangères = cadres |
| 03 | `styles_equipes` | Définir le style d'une équipe | démarche critique : le style **ne prédit pas** la victoire (seul le niveau compte) |
| 04 | `typologie_joueuses` | Profils de joueuses (PCA + clustering) | axe intérieure ↔ extérieure ; archétypes = postes réels |
| 05 | `prediction` | Prédire victoire / écart / classement | régression logistique ; classement prédit dès la mi-saison (< 1 rang d'erreur) |
| 06 | `paris` | Pourrait-on parier ? | ~70 % en walk-forward, mais **pas** rentable face au bookmaker |

## Fil méthodologique

- **Différentiel équipe − adversaire** : une stat ne compte que comparée à l'adverse.
- **Explication ≠ prédiction** : les facteurs (nb 01) sont mesurés *pendant* le match ;
  pour *prédire* (nb 05), on n'utilise que l'info connue *avant* (ELO, forme).
- **Validation honnête** : validation croisée, et **walk-forward** pour les paris (zéro
  fuite du futur).
- **Résultats négatifs assumés** : le style ne prédit pas, les paris ne sont pas
  rentables, la théorie « étrangères = jeu moins collectif » est infirmée.

## Exécuter

Prérequis : `pip install pandas numpy scikit-learn matplotlib openpyxl`.

Ouvrir les notebooks dans VS Code ou Jupyter et exécuter dans l'ordre. Chaque notebook
est autonome (il importe `outils.py` et retrouve seul la racine du projet) et réécrit ses
résultats dans `resultats/<thème>/`. Les notebooks livrés contiennent déjà leurs sorties.

## Données sources (à la racine du repo)

- `data/equipes_fusionnees.csv` — stats joueuse × match
- `data/calendrier_resultat_fusionne_elo_calcule.csv` — matchs + ELO
- `donnée prof/liste joueuses multi annee.xlsm` — joueuses sur 11 saisons
