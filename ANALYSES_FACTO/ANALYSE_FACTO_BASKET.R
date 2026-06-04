# =============================================================================
#  R6.06 - LFB : SUR QUELS CRITERES LES MATCHS SONT-ILS GAGNES ?
#  Analyses factorielles en R  (FactoMineR + factoextra)
#  Script complet et reproductible.
#
#  Unite d'analyse : UN MATCH joue par UNE EQUIPE (totaux d'equipe).
#  Variable cible  : Victoire / Defaite.
# =============================================================================


# -----------------------------------------------------------------------------
# 0) PACKAGES
# -----------------------------------------------------------------------------
pkgs <- c("dplyr", "tidyr", "FactoMineR", "factoextra")
for (p in pkgs) if (!requireNamespace(p, quietly = TRUE)) install.packages(p)
library(dplyr)
library(tidyr)
library(FactoMineR)
library(factoextra)


# -----------------------------------------------------------------------------
# 1) LECTURE DU FICHIER + RECONSTRUCTION DES TOTAUX D'EQUIPE
#    - read.csv2  : separateur ';' et decimale ',' (format du fichier)
#    - check.names = FALSE : garde les noms tels quels (%2P, 2PM, +/- ...)
#      -> on y accede alors avec des back-quotes :  `2PM`, `%3pts`, ...
#    - Les totaux sont reconstruits en SOMMANT les lignes joueuses, car la
#      ligne "TOTAUX EQUIPE" du fichier contient des valeurs manquantes
#      selon les matchs.
# -----------------------------------------------------------------------------

# setwd("chemin/vers/le/dossier")   # <- placez ici le dossier contenant le CSV
df <- read.csv2("C:/R6.06_Domaines_application_de_la_Statistique/TRAVAIL/equipes_fusionnees_abrege.csv",
                stringsAsFactors = FALSE,
                check.names      = FALSE,
                fileEncoding     = "UTF-8")   # si accents bizarres -> "latin1"

# Colonnes de comptage a sommer par match
count_cols <- c("TM","TT","2PM","2PT","3PM","3PT","LFM","LFT",
                "RO","RD","RT","PD","BP","INT","CT","CTS","F","FPR","Pts","EVAL","+/-")

# On ne garde que les lignes "joueuses" (on retire les totaux et la ligne staff)
joueuses <- df %>% filter(!Joueur %in% c("TOTAUX EQUIPE", "Team / Coach"))

# Une case vide de comptage = 0 (une joueuse qui n'a pas tire, etc.)
joueuses[count_cols] <- lapply(joueuses[count_cols], function(x) {
  x <- as.numeric(x); x[is.na(x)] <- 0; x
})

# Cle d'un match-equipe
cle <- c("Equipe", "Saison", "Num_match", "Competition", "dom_ext", "Adversaire")

# Totaux d'equipe = somme des lignes joueuses
team <- joueuses %>%
  group_by(across(all_of(cle))) %>%
  summarise(across(all_of(count_cols), sum), .groups = "drop")

# Resultat du match (Victoire / Defaite)
premier_non_na <- function(x) { x <- x[!is.na(x)]; if (length(x)) x[1] else NA }
res <- df %>%
  group_by(across(all_of(cle))) %>%
  summarise(Victoire = premier_non_na(Victoire), .groups = "drop")

team <- left_join(team, res, by = cle)

# Pourcentages recalcules a partir des sommes (coherents avec les totaux)
team <- team %>%
  mutate(
    `%2pts` = ifelse(`2PT` > 0, `2PM` / `2PT`,            NA_real_),
    `%3pts` = ifelse(`3PT` > 0, `3PM` / `3PT`,            NA_real_),
    `%LF`   = ifelse( LFT  > 0,  LFM  /  LFT,             NA_real_),
    eFG     = ifelse( TT   > 0, (TM + 0.5 * `3PM`) / TT,  NA_real_)   # tir efficace
  )

# On ne garde que les matchs au resultat connu (saisons completes ; 25-26 ecartee)
dat <- team %>%
  filter(Victoire %in% c("Victoire", "Defaite")) %>%
  as.data.frame()
dat$Victoire <- factor(dat$Victoire, levels = c("Defaite", "Victoire"))

cat("Matchs analyses :", nrow(dat),
    "| Victoires :", sum(dat$Victoire == "Victoire"),
    "| Defaites :",  sum(dat$Victoire == "Defaite"), "\n")


# -----------------------------------------------------------------------------
# 2) CHOIX DES COLONNES  (les "bonnes colonnes")
#    ACTIVES = le "comment on joue" -> ce sont les CRITERES testes.
#    SUPPLEMENTAIRES quanti = variables liees mecaniquement au score
#        (l'equipe qui marque le plus gagne par definition) :
#        on ne veut pas qu'elles construisent les axes, juste les illustrer.
#    SUPPLEMENTAIRE quali = le resultat du match.
# -----------------------------------------------------------------------------
vars_actives <- c("%2pts","%3pts","%LF","3PT",        # adresse + volume 3pts
                  "RO","RD",                           # rebonds off / def
                  "PD","BP","INT","CT",                # passes, pertes, intercep, contres
                  "F","FPR")                           # fautes / fautes provoquees

vars_sup_quanti <- c("Pts","eFG","EVAL")               # variables "score" -> illustratives
var_sup_quali   <- "Victoire"                          # cible -> qualitative supplementaire


# -----------------------------------------------------------------------------
# 3) ACP NORMEE
# -----------------------------------------------------------------------------
acp_tab <- dat[, c(vars_actives, vars_sup_quanti, var_sup_quali)]

res.pca <- PCA(acp_tab,
               scale.unit = TRUE,
               graph      = FALSE,
               quanti.sup = match(vars_sup_quanti, names(acp_tab)),
               quali.sup  = match(var_sup_quali,   names(acp_tab)))

## --- Resultats chiffres ---
print(round(res.pca$eig, 3))        # valeurs propres + % d'inertie
print(summary(res.pca))
res.pca$var$coord                   # coordonnees des variables actives (cercle)
res.pca$var$contrib                 # contributions aux axes (%)
res.pca$var$cos2                    # qualite de representation
res.pca$quanti.sup$coord            # variables quantitatives supplementaires
res.pca$quali.sup$coord             # barycentres Victoire / Defaite sur les axes
dimdesc(res.pca, axes = 1:3)        # description automatique des axes

## --- Graphiques ---
g_eig  <- fviz_eig(res.pca, addlabels = TRUE,
                   main = "ACP - Eboulis des valeurs propres")

g_var  <- fviz_pca_var(res.pca, col.var = "contrib", repel = TRUE,
                       gradient.cols = c("#bdbdbd", "#2166ac", "#b2182b"),
                       title = "ACP - Cercle des correlations (F1-F2)")

g_ind  <- fviz_pca_ind(res.pca, label = "none",
                       habillage   = dat$Victoire,
                       addEllipses = TRUE, ellipse.level = 0.5,
                       palette     = c("#b2182b", "#1b7837"),
                       title = "ACP - Matchs colores par le resultat")

# Variables actives + barycentres du resultat sur le meme plan
g_biv  <- fviz_pca_var(res.pca, repel = TRUE,
                       title = "ACP - Variables (le resultat est en quali. sup.)")

print(g_eig); print(g_var); print(g_ind)


# -----------------------------------------------------------------------------
# 4) ACM  (ACP sur variables qualitatives)
#    On decoupe les criteres-cles en 3 classes d'effectifs ~ egaux
#    (ntile gere les ex aequo -> pas d'erreur de bornes), puis on ajoute la
#    modalite "Resultat" pour lire quelles modalites sont proches de Victoire.
# -----------------------------------------------------------------------------
disc3 <- function(x, nom) {
  factor(dplyr::ntile(x, 3), levels = 1:3,
         labels = paste0(nom, c("-Faible", "-Moyen", "-Eleve")))
}

acm_tab <- data.frame(
  eFG      = disc3(dat$eFG,     "eFG"),
  Passes   = disc3(dat$PD,      "PD"),
  RebDef   = disc3(dat$RD,      "RD"),
  RebOff   = disc3(dat$RO,      "RO"),
  BallesP  = disc3(dat$BP,      "BP"),
  Adresse3 = disc3(dat$`%3pts`, "3P"),
  Intercep = disc3(dat$INT,     "INT"),
  Resultat = dat$Victoire
)

res.mca <- MCA(acm_tab, graph = FALSE)   # toutes les variables sont actives

## --- Resultats chiffres ---
print(round(res.mca$eig, 3))
res.mca$var$coord
res.mca$var$contrib
res.mca$var$cos2
dimdesc(res.mca, axes = 1:2)

## --- Graphiques ---
g_mca_var <- fviz_mca_var(res.mca, repel = TRUE, col.var = "cos2",
                          gradient.cols = c("#bdbdbd", "#2166ac", "#b2182b"),
                          title = "ACM - Carte des modalites")

g_mca_bip <- fviz_mca_biplot(res.mca, repel = TRUE, label = "var",
                             title = "ACM - Biplot (individus + modalites)")

print(g_mca_var)


# -----------------------------------------------------------------------------
# 5) COMPLEMENT : lien direct de chaque critere avec la victoire
#    (correlation point-biseriale ; tri croissant)
# -----------------------------------------------------------------------------
win      <- as.integer(dat$Victoire == "Victoire")
criteres <- c(vars_actives, "eFG")
correl   <- sort(sapply(criteres, function(v) cor(win, dat[[v]], use = "complete.obs")))
print(round(correl, 3))

barplot(correl, horiz = TRUE, las = 1, cex.names = 0.8,
        col  = ifelse(correl > 0, "#1b7837", "#b2182b"),
        main = "Correlation de chaque critere avec la VICTOIRE",
        xlab = "correlation point-biseriale")


# -----------------------------------------------------------------------------
# 6) EXPORT DES FIGURES (optionnel)
# -----------------------------------------------------------------------------
ggsave("acp_eboulis.png",   g_eig,     width = 7, height = 4.5, dpi = 300)
ggsave("acp_cercle.png",    g_var,     width = 7, height = 7,   dpi = 300)
ggsave("acp_individus.png", g_ind,     width = 8, height = 6.5, dpi = 300)
ggsave("acm_modalites.png", g_mca_var, width = 9, height = 7.5, dpi = 300)

# Fin du script
