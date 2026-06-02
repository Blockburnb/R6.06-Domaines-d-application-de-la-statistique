from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import sys

def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in s).strip().replace(" ", "_")

def cap_first(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return s
    s = str(s).strip()
    if not s:
        return s
    return s[0].upper() + s[1:]

def make_radar(ax, angles_rad, values, line_color="#1A1A1A", fill_color="#C85A17"):
    vals = np.concatenate((values, [values[0]]))
    angs = np.concatenate((angles_rad, [angles_rad[0]]))
    ax.plot(angs, vals, color=line_color, linewidth=2)
    ax.fill(angs, vals, color=fill_color, alpha=0.6)

def place_outer_labels(ax, angles_rad, labels, radius_factor=1.08, fontsize=10):
    rmax = ax.get_ylim()[1]
    r = rmax * radius_factor
    for ang, lab in zip(angles_rad, labels):
        ca = math.cos(ang)
        sa = math.sin(ang)
        if ca > 0.1:
            ha = "left"
        elif ca < -0.1:
            ha = "right"
        else:
            ha = "center"
        if sa > 0.1:
            va = "bottom"
        elif sa < -0.1:
            va = "top"
        else:
            va = "center"
        ax.text(ang, r, str(lab), fontsize=fontsize, ha=ha, va=va)

def main(team_name: str | None = None):
    here = Path(__file__).resolve().parent
    src = here / "stats_par_equipe.csv"
    if not src.exists():
        raise FileNotFoundError(f"Fichier introuvable: {src}")

    df = pd.read_csv(src, sep=";", decimal=",", encoding="utf-8")
    if "Equipe" in df.columns:
        df["Equipe"] = df["Equipe"].apply(cap_first)

    target_order = ["%Tirs_mean", "PD_mean", "BP_mean", "3pts_marques_mean"]
    for i, col in enumerate(target_order):
        if col not in df.columns:
            alt = col.replace("_mean", "")
            target_order[i] = alt if alt in df.columns else None
    cols = [c for c in target_order if c is not None]
    if len(cols) != 4:
        raise RuntimeError("Les 4 colonnes attendues (%Tirs, PD, BP, 3pts_marques) sont requises dans stats_par_equipe.csv")

    display_labels = ["Tirs marqués", "Passes décisives", "Balles perdues", "3 points marqués"]

    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    max_vals = df[cols].max(skipna=True)
    max_vals[max_vals == 0] = 1.0

    out_dir = here / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    if team_name:
        team_name = cap_first(team_name)

    teams = [team_name] if team_name else df["Equipe"].dropna().unique()

    angles_deg = np.array([180, 120, 60, 0])
    angles_rad = np.deg2rad(angles_deg)

    for team in teams:
        row = df[df["Equipe"] == team]
        if row.empty:
            print(f"Aucune donnée pour l'équipe : {team}")
            continue
        vals = row.iloc[0][cols].to_numpy(dtype=float)
        vals = np.nan_to_num(vals, nan=0.0)
        vals_norm = vals / max_vals.to_numpy(dtype=float)

        fig, ax = plt.subplots(figsize=(6,3.6), subplot_kw=dict(polar=True))
        ax.set_theta_offset(0)
        ax.set_theta_direction(1)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_xticks([])

        ticks = np.linspace(0, 1, 5)
        ax.set_yticks(ticks)
        ax.set_yticklabels([])
        ax.set_ylim(0, 1)
        ax.grid(color="gray", linestyle="--", linewidth=0.5)

        make_radar(ax, angles_rad, vals_norm, line_color="#1A1A1A", fill_color="#C85A17")
        place_outer_labels(ax, angles_rad, display_labels, radius_factor=1.08, fontsize=10)

        # title placed below the radar, bold
        fig.text(0.5, 0.02, str(team), ha="center", va="bottom", fontsize=12, fontweight="bold")

        fig.tight_layout()
        fname = out_dir / f"radar_{safe_name(team)}.png"
        fig.savefig(fname, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"Écrit : {fname}")

if __name__ == "__main__":
    team_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(team_arg)