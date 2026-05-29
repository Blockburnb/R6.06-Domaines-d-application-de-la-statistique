# Analyse exploratoire approfondie — LFB

Script : [exploratoire.py](exploratoire.py) → sorties dans [sorties_explo/](sorties_explo/).
Suite de [SYNTHESE.md](SYNTHESE.md) (les facteurs de victoire).

> **Distinction clé** : les facteurs trouvés avant (eFG, 3pts, rebonds…) sont mesurés
> **pendant** le match → ils *expliquent* la victoire mais ne se connaissent pas à
> l'avance. Pour **pronostiquer**, on n'utilise que ce qui est connu **avant** le
> match : l'ELO et la force de la saison passée.
>
> **Périmètre** : résultats analysés sur les **2 saisons complètes 23-24 et 24-25**
> (la 25-26 est en cours → exclue des analyses de résultats, gardée pour le panorama
> joueuses). Championnat de France uniquement.

---

## A. Quelles équipes sont armées pour gagner ?

Par équipe et saison, on mesure l'**avantage moyen sur l'adversaire** (« net ») sur
chaque facteur, et son lien avec le % de victoires (n = 20 équipes-saisons).

**Ce qui distingue le mieux une équipe qui gagne :**

| Facteur (avantage de l'équipe) | Corrélation avec % de victoires |
|---|---|
| Net points (référence) | +0.94 |
| **Net eFG% (efficacité au tir)** | **+0.85** |
| **Net passes décisives** | **+0.80** |
| Net rebonds défensifs | +0.70 |
| Net % à 3 points | +0.63 |
| Net pression défensive | +0.46 |
| Net pertes de balle | −0.36 |

→ Au niveau **équipe**, l'efficacité au tir et le **jeu collectif (passes décisives)**
priment. Cohérent avec l'analyse match par match.

**Hiérarchie (net points/match) :**
- **Bourges** = référence : +22 (23-24) puis **+27** (24-25), 78→89 % de victoires,
  domine eFG (+8), 3pts (+10) et passes (+12). Patron du championnat.
- **Villeneuve d'Ascq** : ultra-dominateur en 23-24 (+34 net, 89 %) mais **s'effondre
  en 24-25** (−4 net, 33 %) → gros changement d'effectif entre les deux saisons.
- **Basket Landes, Montpellier** : le top solide en 24-25.
- **Roche Vendée** : lanterne rouge constante (−22 puis −20 net).
- Détail : `sorties_explo/A_forces_equipe_saison.csv`.

→ **« Qui va en profiter »** = les équipes qui dominent efficacité + passes : **Bourges
en priorité**, c'est la mieux armée sur les facteurs payants.

---

## B. Bêtes noires

Méthode : on compare le % de victoires réel d'une équipe contre une adversaire au %
**attendu** vu leurs niveaux respectifs. Une sous-performance marquée = bête noire.

**Les plus nettes (sur 4 confrontations) :**
- **Montpellier → Bourges** : 0 % en 4 matchs (attendu 41 %), −27 pts/match.
- **Lyon → Bourges** : 0 % (attendu 37 %), −21 pts.
- **Angers → Bourges** : 0 % (attendu 35 %).
- **Landerneau → Roche Vendée** : 0 % (attendu 57 %) — la plus « anormale », deux
  équipes de niveau proche mais Roche gagne tout.

→ **Bourges est la bête noire de presque toute la ligue** (personne ne la bat sur
l'échantillon). ⚠️ **Seulement 4 matchs par paire** → tendance indicative, **pas**
significative statistiquement. Détail : `sorties_explo/B_confrontations.csv`.

---

## C. Pronostics 24-25 (validé sur données réelles)

Backtest **hors-échantillon** : on prédit les 132 matchs de championnat 24-25 avec de
l'information connue **avant** chaque match, puis on compare au résultat réel.

| Méthode de pronostic | % de bons pronostics |
|---|---|
| « le domicile gagne » (naïf) | 59.8 % |
| **Favori ELO (avant match)** | **68.2 %** (132 matchs) |
| Force de la saison 23-24 | 52.2 % (90 matchs couverts) |

**Réponse : OUI, on peut pronostiquer la 24-25, et l'ELO est le bon outil** : 68 % de
réussite vs 60 % pour le naïf. En revanche, prédire seulement avec la force de la
saison *précédente* marche mal (52 %) → **les effectifs changent trop d'une saison à
l'autre** (cf. Villeneuve d'Ascq) ; l'ELO, lui, se met à jour match après match.

**~1 match sur 3 est une surprise** (le favori ELO perd dans **32 %** des cas). Ça
répond directement au sujet du prof (« % de matchs perdus par une favorite » ≈ 32 %).

> Note : la « force 23-24 » prédit mal (52 %) car elle ne couvre que 90 matchs
> (équipes promues sans historique) et ignore les changements d'effectif. L'ELO reste
> le meilleur prédicteur disponible avant match.

> Piste : une régression logistique sur l'écart d'ELO + avantage terrain donnerait une
> **probabilité** par match (et non un oui/non), potentiellement > 68 %.

---

## D. Nationalité & panorama des joueuses (11 saisons, 2015→2026)

Le fichier couvre **11 saisons** (pas seulement 3) → panorama complet demandé par le
prof. 1 927 lignes joueuse-saison. Appariement liste ↔ stats : **76 %** (correct ;
le reste = écarts d'orthographe des noms).

**D0 — Évolution du championnat :**

| Saison | Joueuses | % étrangères | Âge moyen | Taille moy. |
|---|---|---|---|---|
| 15-16 | 188 | 34 % | 23.9 | 1.81 m |
| 18-19 | 177 | 34 % | 24.7 | 1.82 m |
| 19-20 (COVID) | 164 | 35 % | 24.7 | 1.82 m |
| 20-21 (COVID) | 174 | **39 %** | 25.0 | 1.82 m |
| 21-22 | 181 | 33 % | 24.9 | 1.81 m |
| 23-24 | 180 | 37 % | 24.6 | 1.81 m |
| 24-25 | 171 | 32 % | 24.3 | 1.81 m |
| 25-26 | 168 | 29 % | 23.9 | 1.80 m |

→ **COVID** : petit pic d'étrangères en 20-21 (39 % vs ~34 % avant), puis **repli sur
les 2 dernières saisons (32 % → 29 %)**. Tendance récente = **moins** d'étrangères.
→ **Âge** : stable autour de **24-25 ans**, sans rajeunissement net (léger creux récent
à 23.9, comme en 15-16). La théorie « le championnat rajeunit nettement » est
**infirmée**.
→ **Taille** stable (~1,81 m). Détail : `sorties_explo/D_evolution_saison.csv`.

**D1 — Profil individuel (par joueuse-saison, ≥5 matchs, saisons 23-24+24-25) :**

| | n | Minutes | Points | Passes déc. | Rebonds | Interceptions | EVAL |
|---|---|---|---|---|---|---|---|
| **Étrangères** | 87 | 25.2 | **9.3** | 2.0 | 4.4 | 1.04 | **10.1** |
| **Françaises** | 151 | 17.2 | 4.9 | 1.4 | 2.2 | 0.65 | 5.3 |

→ Les étrangères jouent **~1,5× plus** et ont un impact (EVAL) **~2× supérieur** : ce
sont les **joueuses-cadres** recrutées pour performer. Les françaises forment le
réservoir plus large (rotation, banc, jeunes).

**D2 — Impact sur le collectif et les résultats (équipe×saison, n=20) :**
- Part de minutes étrangères : 38 % en moyenne (de 9 % à 62 % selon l'équipe).
- **corr(part étrangères, victoires) = +0.39** → lien positif **modéré** : faire jouer
  ses étrangères aide à gagner (ce sont les meilleures), sans être déterminant.
- **corr(part étrangères, jeu collectif) = +0.23** → ⚠️ **ta théorie n'est PAS
  confirmée** : on s'attendait à un jeu plus *individuel* avec plus d'étrangères, mais
  la corrélation est légèrement **positive** (un peu *plus* de passes par point). Pas
  d'effet « moins collectif » dans ces données — au mieux l'inverse, faiblement.

> ⚠️ **Corrélation ≠ causalité** : les étrangères ne *créent* pas la victoire ; ce sont
> les clubs au plus gros budget qui recrutent les meilleures (souvent étrangères) ET
> gagnent. Sur le « collectif », l'intuition de départ ne se vérifie pas ici.

---

## Pistes pour aller plus loin

1. **Prono probabiliste** (régression logistique ELO + terrain) → proba % par match +
   classement final prédit dès la mi-saison (attendu explicite du prof).
2. **Panorama joueuses approfondi** : pyramide des âges, durée de carrière, fidélité à
   un club (les 11 saisons permettent de suivre les trajectoires individuelles).
3. **« Qui recruter »** : croiser les faiblesses d'une équipe (analyse de style) avec
   les profils de joueuses, par poste.
4. **Bêtes noires** : intégrer la 25-26 finie pour fiabiliser (plus de confrontations).

## Fichiers
- `sorties_explo/A_forces_equipe_saison.csv` — force par équipe/saison
- `sorties_explo/B_confrontations.csv` — toutes les confrontations
- `sorties_explo/C_pronos.txt` — backtest pronostics
- `sorties_explo/D_evolution_saison.csv` — panorama 11 saisons
- `sorties_explo/D_profil_individuel.csv`, `D_equipe_nationalite.csv` — nationalités
