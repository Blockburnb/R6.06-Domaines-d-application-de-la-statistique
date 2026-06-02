# ============================================================================
#  ANALYSES FACTORIELLES LFB - LE TRIO DÉCISIF POUR LES PARIS
#  1. ACP : Anatomie de la Défaite / Victoire (Profil Saison)
#  2. AFC : Les Styles de Jeu qui font gagner (Gravité ELO)
#  3. ACM : La Recette du Match Gagnant (Checklist Match)
# ============================================================================

# install.packages(c("FactoMineR", "factoextra", "dplyr"))
library(FactoMineR)
library(factoextra)

CHEMIN <- "C:/R6.06_Domaines_application_de_la_Statistique/TRAVAIL/def/"   # <-- À adapter

# ===========================================================================
# 0. FONCTIONS UTILITAIRES & PRÉPARATION DES DONNÉES
# ===========================================================================
num <- function(x) as.numeric(sub(",", ".", as.character(x), fixed = TRUE))

norm_nom <- function(x) {
  x <- tolower(trimws(as.character(x)))
  x <- iconv(x, to = "ASCII//TRANSLIT")
  gsub("[^a-z]", "", x)
}

terciles <- function(x, prefixe) {
  r <- rank(x, ties.method = "first")
  cut(r, breaks = quantile(r, c(0, 1/3, 2/3, 1)),
      labels = paste0(prefixe, c("_F", "_M", "_E")), include.lowest = TRUE)
}

eq <- read.csv2(file.path(CHEMIN, "equipes_fusionnees.csv"),
                colClasses = "character", check.names = FALSE, fileEncoding = "UTF-8")

tot <- eq[eq$Joueur == "TOTAUX EQUIPE", ]

# Conversion des variables statistiques
cols_num <- c("%Tirs","PD","BP","INT","RD","RO","Pts", "Tirs_marques", "Tirs_tentes",
              "3pts_marques","3pts_tentes","LF_marques","F",
              "Points_int","Point_2eme_chance","Points_CA","Points_banc")

suppressWarnings({
  for (c in cols_num) tot[[c]] <- num(tot[[c]])
})

# Variables composites
tot$Echecs_3pts <- tot[["3pts_tentes"]] - tot[["3pts_marques"]]
tot$Tirs_rates_totaux <- tot$Tirs_tentes - tot$Tirs_marques
tot$Ratio_BP_PD <- tot$BP / (tot$PD + 0.1) 
tot$pts_3pts <- 3 * tot[["3pts_marques"]]
tot$pts_LF   <- tot[["LF_marques"]]

# Calcul du nombre de marqueuses
jou <- eq[eq$Joueur != "TOTAUX EQUIPE" & eq$Joueur != "Team / Coach", ]
suppressWarnings(jou$Pts <- num(jou$Pts))
jou$cle <- paste(jou$Equipe, jou$Saison, jou$Num_match, jou$Adversaire, sep = "||")

nbm <- tapply(jou$Pts, jou$cle, function(p) sum(p > 0, na.rm = TRUE))
eff <- data.frame(cle = names(nbm), nb_marqueuses = as.numeric(nbm))

tot$cle <- paste(tot$Equipe, tot$Saison, tot$Num_match, tot$Adversaire, sep = "||")
tot <- merge(tot, eff, by = "cle", all.x = TRUE)

# Détermination du résultat (Victoire/Défaite) via le calendrier
cal <- read.csv2(file.path(CHEMIN, "calendrier_resultat_fusionne_elo_calcule.csv"),
                 colClasses = "character", check.names = FALSE, fileEncoding = "UTF-8")
names(cal) <- c("Saison","Journee","Domicile","Exterieur","Sdom","Sext","Derby",
                "ELOdom_av","ELOext_av","ELOdom_ap","ELOext_ap")

long <- rbind(
  data.frame(Saison = cal$Saison, eqn = norm_nom(cal$Domicile), elo = num(cal$ELOdom_ap), 
             win = num(cal$Sdom) > num(cal$Sext), loss = num(cal$Sdom) < num(cal$Sext)),
  data.frame(Saison = cal$Saison, eqn = norm_nom(cal$Exterieur), elo = num(cal$ELOext_ap), 
             win = num(cal$Sext) > num(cal$Sdom), loss = num(cal$Sext) < num(cal$Sdom)))

elo <- aggregate(cbind(ELO_moyen = elo, winrate = win, lossrate = loss) ~ eqn + Saison, long, mean)

# Normalisation des noms
tot$eqn  <- norm_nom(tot$Equipe)
tot$eqn_elo <- tot$eqn
tot$eqn_elo[tot$eqn == "charleville"]  <- "charlevillemezieres"
tot$eqn_elo[tot$eqn == "montpellier"] <- "lattesmontpellier"

# Auto-jointure allégée pour le statut V/D
opp_pts <- tot[, c("Saison", "Num_match", "eqn", "Pts")]
names(opp_pts) <- c("Saison", "Num_match", "advn", "Pts_adv")
opp_pts <- opp_pts[!duplicated(opp_pts[, c("Saison", "Num_match", "advn")]), ]

norm_adv <- c("Basket Landes"="Basket landes", "Charleville-Mézières"="Charleville",
              "Charnay"="charnay", "Lattes Montpellier"="Montpellier",
              "Lyon Asvel Féminin"="Lyon", "Roche Vendée"="Roche vendee",
              "Villeneuve d'Ascq"="Villeneuve d'ascq")
tot$Adv_corrige <- ifelse(tot$Adversaire %in% names(norm_adv), norm_adv[tot$Adversaire], tot$Adversaire)
tot$advn <- norm_nom(tot$Adv_corrige)

tot <- merge(tot, opp_pts, by = c("Saison", "Num_match", "advn"), all.x = TRUE)
tot$Resultat <- ifelse(!is.na(tot$Gagne_perdu) & tot$Gagne_perdu != "", tot$Gagne_perdu,
                       ifelse(tot$Pts > tot$Pts_adv, "Victoire",
                              ifelse(tot$Pts < tot$Pts_adv, "Defaite", NA)))


# ===========================================================================
# 1. ACP - "Anatomie de la Défaite et de la Victoire" (Niveau Saison)
# ===========================================================================
v2 <- c("%Tirs", "PD", "BP", "INT", "RD", "RO", "nb_marqueuses", 
        "F", "Echecs_3pts", "Tirs_rates_totaux", "Ratio_BP_PD")

prof <- aggregate(tot[, v2], by = list(eqn = tot$eqn_elo, Saison = tot$Saison), FUN = function(x) mean(x, na.rm = TRUE))
M_acp <- merge(prof, elo, by = c("eqn", "Saison"))

acp2 <- data.frame(M_acp[, v2], ELO_moyen = M_acp$ELO_moyen, 
                   taux_victoire = M_acp$winrate, taux_defaite = M_acp$lossrate, check.names = FALSE)

res_acp2 <- PCA(acp2, quanti.sup = 12:14, graph = FALSE)

p_acp <- fviz_pca_var(res_acp2, repel = TRUE, col.var = "black", col.quanti.sup = "red", 
                      title = "1. ACP - Anatomie de la Défaite et Victoire")
print(p_acp)


# ===========================================================================
# 2. AFC - Identités de jeu : Quels styles font gagner ? (Catégories ELO)
# ===========================================================================
tot$eq_sais  <- paste(tot$eqn_elo, tot$Saison, sep="_")

# Sources et Styles de jeu (Variables actives)
sources_afc <- c("Points_int", "Point_2eme_chance", "Points_CA", "Points_banc", 
                 "pts_3pts", "pts_LF", "PD", "BP", "RO")

# Agrégation des volumes d'actions par équipe/saison
contingence <- aggregate(tot[, sources_afc], by = list(eq_sais = tot$eq_sais), FUN = function(x) sum(x, na.rm = TRUE))
rownames(contingence) <- contingence$eq_sais; contingence$eq_sais <- NULL

# Récupération du WinRate ET de l'ELO moyen depuis le tableau M_acp (déjà calculé en section 1)
win_data <- M_acp[, c("eqn", "Saison", "winrate", "ELO_moyen")]
win_data$eq_sais <- paste(win_data$eqn, win_data$Saison, sep="_")

# CRÉATION DES CATÉGORIES ELO (Tiers : Bas, Moyen, Top)
win_data$Classe_ELO <- terciles(win_data$ELO_moyen, "ELO")
levels(win_data$Classe_ELO) <- c("ELO_Bas", "ELO_Moyen", "ELO_Top") # Renommage propre pour le graphique

# Fusion finale des données
data_afc <- merge(contingence, win_data[, c("eq_sais", "winrate", "Classe_ELO")], by.x = "row.names", by.y = "eq_sais")
rownames(data_afc) <- data_afc$Row.names; data_afc$Row.names <- NULL

# Lancement de l'AFC :
# - Colonnes 1 à 9 : Les statistiques de jeu (Actives)
# - Colonne 10 : Le Taux de victoire (Quantitative supplémentaire, gère la couleur)
# - Colonne 11 : La Classe ELO (Qualitative supplémentaire, projette les centres de gravité)
res_afc <- CA(data_afc, quanti.sup = 10, quali.sup = 11, graph = FALSE)

# Le Biplot Épuré (Taux de victoire = Code couleur + Affichage des barycentres ELO)
p_afc <- fviz_ca_biplot(res_afc, 
                        geom.row = "point",                    # Cache les noms d'équipes, garde que les points
                        geom.col = c("point", "text"),         # Affiche le nom des styles (PD, BP, pts_3pts...)
                        repel = TRUE,
                        col.col = "black",                     # Styles de jeu en noir
                        shape.col = 15,                        # Carré pour les styles
                        col.row = data_afc$winrate,            # Équipes colorées par leur WinRate (Rouge -> Bleu)
                        gradient.cols = c("#FF0000", "#E7B800", "#00AFBB"), 
                        pointsize = 2.5,
                        title = "2. AFC - Identités de jeu & Gravité des Top Équipes", 
                        legend.title = "Taux\nVictoire")
print(p_afc)


# ===========================================================================
# 3. ACM - "La Recette d'un Match Gagnant" (Niveau Match)
# ===========================================================================
cols_acm <- c("%Tirs", "PD", "BP", "Echecs_3pts", "nb_marqueuses", "dom_ext")
d_acm <- tot[complete.cases(tot[, cols_acm]) & tot$Resultat %in% c("Victoire", "Defaite"), ]

acm_df <- data.frame(
  Adresse    = terciles(d_acm[["%Tirs"]], "Adresse"),
  Passes     = terciles(d_acm[["PD"]], "Passes"),
  Pertes     = terciles(d_acm[["BP"]], "Pertes"),
  Echecs_3P  = terciles(d_acm[["Echecs_3pts"]], "Echecs3P"),
  Nb_Marq    = terciles(d_acm[["nb_marqueuses"]], "NbMarq"),
  Lieu       = factor(d_acm$dom_ext),
  Resultat   = factor(d_acm$Resultat)
)

res_acm <- MCA(acm_df, quali.sup = 7, graph = FALSE)

p_acm <- fviz_mca_var(res_acm, repel = TRUE, col.var = "black", col.quali.sup = "red", shape.var = 15,
                      title = "3. ACM - La Recette d'un Match Gagnant")
print(p_acm)

# --- EXTRACTION DES RÈGLES DE PARI ---
desc_res <- catdes(acm_df, num.var = 7)

cat("\n======================================================\n")
cat("--- CHECKLIST DU PARIEUR : CONDITIONS DE VICTOIRE ---\n")
cat("======================================================\n")
print(round(desc_res$category$Victoire, 3))

cat("\n======================================================\n")
cat("--- ALERTE ROUGE : CONDITIONS DE DÉFAITE ---\n")
cat("======================================================\n")
print(round(desc_res$category$Defaite, 3))