import pandas as pd
import math
from pathlib import Path


def calculate_win_probability(elo_team, elo_opponent):
    """
    Calcule la probabilité de victoire d'une équipe contre son adversaire.
    
    P = 1 / (1 + 10^((ELO_adversaire - ELO_team) / 400))
    
    Args:
        elo_team: ELO de l'équipe
        elo_opponent: ELO de l'adversaire
    
    Returns:
        Probabilité de victoire entre 0 et 1
    """
    return 1 / (1 + 10 ** ((elo_opponent - elo_team) / 400))


def calculate_elo_adjustment(elo_old, elo_opponent, is_home, is_derby, result):
    """
    Calcule l'ajustement d'ELO après un match.
    
    Nouvel_ELO = Ancien_ELO + K * (R - P)
    
    Args:
        elo_old: ELO avant le match
        elo_opponent: ELO de l'adversaire avant le match
        is_home: True si l'équipe joue à domicile, False sinon
        is_derby: True si c'est un derby, False sinon
        result: 1 si victoire, 0 si défaite
    
    Returns:
        Nouvel ELO
    """
    # Calcul de la probabilité de victoire
    P = calculate_win_probability(elo_old, elo_opponent)
    
    # Calcul de K
    K = 30
    if is_derby:
        K += 10  # +10 pour les deux équipes en cas de derby
    else:
        if is_home:
            K += 5  # +5 pour match à domicile
        else:
            K -= 5  # -5 pour match à l'extérieur
    
    # Calcul du nouvel ELO
    new_elo = elo_old + K * (result - P)
    
    return new_elo


def process_elo_calculation(input_file, output_file, default_elo=1500):
    """
    Lit le fichier CSV des matchs et calcule les ELO après chaque rencontre.
    Propage les ELO calculés aux matchs suivants de la même équipe.
    
    Args:
        input_file: Chemin du fichier CSV d'entrée
        output_file: Chemin du fichier CSV de sortie
        default_elo: ELO par défaut pour les nouvelles équipes (défaut: 1500)
    """
    # Lecture du fichier
    df = pd.read_csv(input_file, sep=';')
    
    # Dictionnaire pour stocker les ELO actuels de chaque équipe
    team_elo = {}
    
    # Traitement de chaque ligne
    for idx, row in df.iterrows():
        home_team = row['Domicile']
        away_team = row['Exterieur']
        
        # Récupérer les ELO avant match
        if pd.isna(row['ELO domicile avant match']) or pd.isna(row['ELO extérieur avant match']):
            # Chercher les ELO dans le dictionnaire (calculés précédemment)
            if home_team not in team_elo:
                team_elo[home_team] = default_elo
            if away_team not in team_elo:
                team_elo[away_team] = default_elo
            
            elo_home_before = team_elo[home_team]
            elo_away_before = team_elo[away_team]
        else:
            elo_home_before = float(row['ELO domicile avant match'])
            elo_away_before = float(row['ELO extérieur avant match'])
            # Initialiser les ELO dans le dictionnaire
            team_elo[home_team] = elo_home_before
            team_elo[away_team] = elo_away_before
        
        score_home = int(row['Score domicile'])
        score_away = int(row['Score Exterieur'])
        
        is_derby = bool(row['Derby'])
        
        # Déterminer le résultat (1 si victoire, 0 si défaite)
        result_home = 1 if score_home > score_away else 0
        result_away = 1 if score_away > score_home else 0
        
        # Calculer les nouveaux ELO
        elo_home_after = calculate_elo_adjustment(
            elo_home_before,
            elo_away_before,
            is_home=True,
            is_derby=is_derby,
            result=result_home
        )
        
        elo_away_after = calculate_elo_adjustment(
            elo_away_before,
            elo_home_before,
            is_home=False,
            is_derby=is_derby,
            result=result_away
        )
        
        # Mettre à jour les ELO dans le dictionnaire
        team_elo[home_team] = elo_home_after
        team_elo[away_team] = elo_away_after
        
        # Mettre à jour le DataFrame
        df.at[idx, 'ELO domicile avant match'] = elo_home_before
        df.at[idx, 'ELO extérieur avant match'] = elo_away_before
        df.at[idx, 'ELO domicile après match'] = round(elo_home_after, 2)
        df.at[idx, 'ELO extérieur après match'] = round(elo_away_after, 2)
    
    # Sauvegarde du fichier
    df.to_csv(output_file, sep=';', index=False)


def main(input_path: Path, output_path: Path) -> None:
    process_elo_calculation(str(input_path), str(output_path))
    print(f"[modules/calculer_elo.py] ELO calcules: {output_path}")


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent.parent
    input_file = script_dir / "data_intermediaire" / "calendrier_resultat_fusionne_elo.csv"
    output_file = script_dir / "data_intermediaire" / "calendrier_resultat_fusionne_elo_calcule.csv"
    main(input_file, output_file)
