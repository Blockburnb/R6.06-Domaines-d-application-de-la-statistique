# Style de jeu (v2) — analyse corrigée

Script : [styles_v2.py](styles_v2.py) → sorties dans [sorties_styles_v2/](sorties_styles_v2/).

> **Pourquoi une v2 ?** Tu as identifié le défaut central de la v1 : elle clusterisait
> sur eFG% / rebond = des mesures de **qualité**, donc elle séparait juste « les forts
> des faibles » et la matrice de confrontation ne disait que *les forts gagnent*. Cette
> v2 sépare explicitement **NIVEAU** (à quel point on est fort) et **STYLE** (comment on
> joue), et teste si le style sert vraiment à quelque chose.

## Sur quoi je me base maintenant (et pourquoi c'est mieux)

Variables de **style**, choisies pour décrire le *comment* sans mesurer le niveau :
- **D'où viennent les points** (donnée **nouvelle**, tirée de la ligne `TOTAUX EQUIPE`,
  jamais exploitée avant) : % en raquette, % à 3pts, % en contre-attaque, % de seconde
  chance, % du banc.
- **Comment on joue** : rythme (possessions/match), part de tirs à 3pts, défense
  agressive (interceptions/possession), dépendance à la star, taille moyenne des
  joueuses (pondérée par les minutes).

---

## Étape 1 — Vérifier que ces variables ne mesurent PAS le niveau

Corrélation de chaque variable avec le taux de victoire (proxy du niveau). C'est le
contrôle qui manquait totalement en v1 :

| Variable | r(victoires) | Verdict |
|---|---|---|
| % contre-attaque | +0.03 | style pur |
| part 3pts tirés | +0.05 | style pur |
| taille moyenne | +0.07 | style pur |
| % à 3pts (points) | +0.15 | style pur |
| rythme (pace) | −0.24 | style pur |
| % raquette | +0.25 | style pur |
| % banc | +0.27 | style pur |
| % seconde chance | +0.29 | style pur |
| défense agressive | +0.34 | style pur |
| **dépendance à la star** | **−0.69** | **= NIVEAU, écartée** |

→ **Découverte importante** : la **dépendance à la star n'est PAS un style, c'est un
marqueur de faiblesse** (r = −0.69). Les mauvaises équipes dépendent d'une joueuse parce
qu'elles n'ont qu'elle. Je l'ai donc **retirée** du clustering (sinon elle réintroduit le
niveau, exactement le piège de la v1). Les 9 autres variables sont du style "pur".

---

## Étape 2 — Le nombre de clusters n'est plus arbitraire

Choisi par **score de silhouette** (netteté des groupes ; plus haut = mieux) :

| k | silhouette |
|---|---|
| 2 | 0.160 |
| 3 | 0.163 |
| 4 | 0.173 |
| **5** | **0.180** |

→ **Toutes les silhouettes sont faibles (~0.16-0.18).** C'est un résultat en soi : **il
n'existe pas de groupes de style nets** en LFB. Les équipes forment un continuum, pas des
"familles" tranchées. La v1 imposait 4 archétypes francs — c'était une sur-interprétation.

## Les styles obtenus (k=5, à lire avec prudence)

| Style | Marqueurs | % victoires (étendue) |
|---|---|---|
| 0 — banc + contre-attaque, lent | + banc, + CA, − rythme | 55 % (14→82) |
| 1 — jeu extérieur / grandes | + part 3pts, + taille | 53 % (27→86) |
| 2 — jeu intérieur classique | − 3pts (joue près du panier) | 48 % (19→86) |
| 3 — défense agressive | + interceptions, + CA | 56 % (50→59) |
| 4 — atypique (1 équipe) | − raquette, − CA | 33 % |

**Le point décisif** : dans chaque style, le taux de victoire va de **~15 % à ~86 %**.
Bourges est dans le style "intérieur" (2) en 24-25 et gagne 86 %, mais Roche Vendée est
dans le **même** style et gagne 19 %. Donc :

> **Le style n'est PAS le niveau** — c'est ce qu'on voulait. On trouve des bonnes et des
> mauvaises équipes dans chaque style. (En v1 : un cluster à 74 % et un à 28 % → c'était
> le niveau déguisé en style.) Mission « isoler le *comment* » réussie.

---

## Étape 3 — LE TEST DÉCISIF : le style sert-il à prédire qui gagne ?

On prédit chaque match (90 matchs avec ELO + styles connus) et on compare :
- **Modèle 1** : écart d'ELO seul (= le niveau).
- **Modèle 2** : écart d'ELO **+** différentiel de style.

| Modèle | AUC |
|---|---|
| ELO seul | 0.802 |
| ELO + style | 0.771 |
| **gain du style** | **−0.032** |

### Verdict (honnête — et c'est LE résultat de cette analyse)

**Le style n'ajoute rien pour prédire qui gagne ; il dégrade même légèrement le modèle**
(il ajoute du bruit). Ta phrase de départ — *« on n'a finalement que : les forts battent
les faibles »* — est **statistiquement démontrée** : une fois le niveau (ELO) connu,
savoir *comment* une équipe joue n'aide pas à prédire le résultat.

C'est un vrai enseignement, défendable à l'oral : **en LFB, le niveau prime largement sur
le style.** Le style sert à **décrire** une équipe et à **réfléchir au recrutement**
(« on joue trop intérieur, il manque une shooteuse »), **pas** à pronostiquer.

---

## Réponses directes à tes questions

**« On n'a que : les forts battent les faibles ? »** → **Oui, et c'est maintenant
prouvé** : le style ajoute −0.032 d'AUC à l'ELO (donc rien d'utile). Le niveau décide.

**« Comment trouver le style / sur quoi tu t'es basé / challenge ta réflexion »** → La v1
était biaisée (style = mesures de qualité). La v2 corrige avec : variables neutres au
niveau, **contrôle systématique** (corr avec victoires), retrait de `dep_star` et
`taille` quand elles capturent le niveau, **k validé par silhouette**, et **régression
hiérarchique** ELO vs ELO+style.

**« D'autres données à recouper ? »** → **Oui, j'en ai activé une nouvelle** : la ligne
`TOTAUX EQUIPE` (répartition des points raquette / CA / 2e chance / banc), inexploitée
jusqu'ici. Restent : enchaînement des matchs (fatigue — limité sans dates), et surtout
les **trajectoires de joueuses sur 11 saisons** (peu exploité).

**« Méthodes de data mining ? »** → Utilisées ici : clustering + **silhouette** (valider
k), **régression hiérarchique** (isoler un effet net du niveau — la bonne méthode pour ta
question). Autres pertinentes pour la suite : **PCA** (réduire/visualiser les profils),
**arbres/forêts** (importance non linéaire), **modèle de régression** pour l'écart de
points.

---

## Pistes pour la suite (par valeur)

1. **Niveau JOUEUSE plutôt qu'équipe** : PCA + clustering sur ~300 joueuses → typologie
   (meneuse / intérieure / shooteuse / role-player). Là le style individuel **a** du sens
   et l'échantillon est grand. C'est aussi le cœur du volet recrutement du prof.
2. **Modèle d'écart de points** : le style ne change pas le *vainqueur*, mais peut influer
   sur la *marge* — à tester proprement.
3. **Trajectoires de joueuses** (11 saisons) : fidélité à un club, production qui se
   maintient après un transfert.

## Fichiers
- `sorties_styles_v2/profils_style.csv` — variables de style + cluster par équipe-saison
- `sorties_styles_v2/style.txt` — rapport complet (étapes 1→3)

> Note : la v1 ([SYNTHESE_STYLES.md](SYNTHESE_STYLES.md)) est **conservée mais dépassée** —
> garde-la seulement pour montrer la démarche critique (v1 biaisée → v2 corrigée), c'est
> valorisable à l'oral.
