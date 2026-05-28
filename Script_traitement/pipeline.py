#!/usr/bin/env python3
"""
Pipeline de traitement complet des données de statistiques basketball.

Ce script orchestre l'ensemble du processus de traitement:
1. Fusion des fichiers équipes
2. Fusion du calendrier et des résultats
3. Enrichissement avec les ELO initiaux
4. Calcul des ELO après chaque match
5. Vérification de l'intégrité des données

Les fichiers finaux sont exportés vers /data à la racine du repository.
"""

import sys
from pathlib import Path
import shutil


def add_verification_path():
    """Ajoute le répertoire verification au path pour les imports."""
    script_dir = Path(__file__).resolve().parent
    verification_dir = script_dir / "verification"
    sys.path.insert(0, str(verification_dir))


def run_pipeline():
    """Exécute le pipeline complet de traitement."""
    
    # Initialiser les chemins
    script_dir = Path(__file__).resolve().parent
    modules_dir = script_dir / "modules"
    data_intermediaire_dir = script_dir / "data_intermediaire"
    data_output_dir = script_dir.parent / "data"
    
    # S'assurer que les répertoires existent
    modules_dir.mkdir(exist_ok=True)
    data_intermediaire_dir.mkdir(exist_ok=True)
    data_output_dir.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("PIPELINE DE TRAITEMENT - DEBUT")
    print("=" * 70)
    
    try:
        # Etape 1: Fusion des fichiers équipes
        print("\n[1/5] Fusion des fichiers equipes...")
        from modules.fusion_fichier_equipes import main as fusion_equipes
        equipes_path = data_intermediaire_dir / "equipes_fusionnees.csv"
        fusion_equipes(equipes_path)
        
        # Etape 2: Fusion du calendrier et résultats
        print("\n[2/5] Fusion du calendrier et des resultats...")
        from modules.fusion_calendrier_resultat import main as fusion_calendrier
        calendrier_path = data_intermediaire_dir / "calendrier_resultat_fusionne.csv"
        fusion_calendrier(calendrier_path)
        
        # Etape 3: Enrichissement avec ELO initiaux
        print("\n[3/5] Enrichissement avec les ELO initiaux...")
        from modules.enrichir_calendrier_elo import main as enrichir_elo
        calendrier_elo_path = data_intermediaire_dir / "calendrier_resultat_fusionne_elo.csv"
        enrichir_elo(calendrier_path, calendrier_elo_path)
        
        # Etape 4: Calcul des ELO
        print("\n[4/5] Calcul des ELO apres chaque match...")
        from modules.calculer_elo import main as calculer_elo
        calendrier_elo_calcule_path = data_intermediaire_dir / "calendrier_resultat_fusionne_elo_calcule.csv"
        calculer_elo(calendrier_elo_path, calendrier_elo_calcule_path)
        
        # Etape 5: Vérification
        print("\n" + "=" * 70)
        print("VERIFICATION - Controle des donnees produites")
        print("=" * 70)
        
        verification_results = []
        
        print("\n[5.1/5.3] Verification de la fusion des equipes...")
        add_verification_path()
        from verification.verifier_fusion import main as verifier_fusion
        result_fusion = verifier_fusion()
        verification_results.append(("Fusion equipes", result_fusion))
        
        print("\n[5.2/5.3] Verification de la fusion du calendrier...")
        from verification.verifier_fusion_calendrier import main as verifier_calendrier
        result_calendrier = verifier_calendrier()
        verification_results.append(("Fusion calendrier", result_calendrier))
        
        print("\n[5.3/5.3] Verification de l'enrichissement ELO...")
        from verification.verifier_enrichissement_calendrier_elo import main as verifier_elo
        result_elo = verifier_elo()
        verification_results.append(("Enrichissement ELO", result_elo))
        
        # Résumé des vérifications
        print("\n" + "=" * 70)
        print("RESULTATS DES VERIFICATIONS")
        print("=" * 70)
        all_ok = True
        for name, result in verification_results:
            status = "OK" if result == 0 else "KO"
            print(f"  [{status}] {name}")
            if result != 0:
                all_ok = False
        
        if not all_ok:
            print("\nATTENTION: Des ecarts ont ete detectes lors des verifications!")
            print("Consultez les logs ci-dessus pour plus de details.")
        
        # Copier les fichiers finaux vers /data
        print("\n" + "=" * 70)
        print("FINALISATION - Copie des fichiers de sortie")
        print("=" * 70)
        
        # Fichiers finaux à exporter
        final_files = {
            equipes_path: data_output_dir / "equipes_fusionnees.csv",
            calendrier_elo_calcule_path: data_output_dir / "calendrier_resultat_fusionne_elo_calcule.csv"
        }
        
        for src, dst in final_files.items():
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  [OK] {src.name} -> data/")
            else:
                print(f"  [KO] ERREUR: {src.name} introuvable!")
                return False
        
        print("\n" + "=" * 70)
        print("PIPELINE TERMINE AVEC SUCCES")
        print("=" * 70)
        print(f"\nFichiers finaux disponibles dans: {data_output_dir}")
        print(f"  - equipes_fusionnees.csv")
        print(f"  - calendrier_resultat_fusionne_elo_calcule.csv")
        print(f"\nFichiers intermediaires dans: {data_intermediaire_dir}")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("ERREUR LORS DE L'EXECUTION DU PIPELINE")
        print("=" * 70)
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
