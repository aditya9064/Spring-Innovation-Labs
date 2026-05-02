"""
CrimeScope — Problem diagram for the deck (editorial version).

Design intent: read like an FT/NYT graphic, not a dashboard.
  - No boxes, badges, pills, or clip-art arrows.
  - Two huge numbers in red/green do all the work.
  - Thin vertical rules separate the columns; the negative space carries weight.
  - One thin strip-plot at the bottom proves it isn't cherry-picked.

Reads:
  - crimescope/ml/artifacts/tract_scores_latest.csv

Writes:
  - crimescope/presentation/figures/13_problem.png

Run:
  python3 crimescope/presentation/build_problem_diagram.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------- paths ----------
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ml" / "artifacts"
OUT = ROOT / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- editorial palette ----------
BG = "#ffffff"
INK = "#0b1220"          # near-black headlines
BODY = "#334155"         # body / sub-labels
MUTED = "#94a3b8"        # tertiary
RULE = "#e5e7eb"         # thin separators
GREEN = "#15803d"        # deeper editorial green
RED = "#b91c1c"          # deeper editorial red
AMBER = "#b45309"
ORANGE = "#c2410c"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "text.color": INK,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.dpi": 150,
})


def _band_color(score: float) -> str:
    if score < 30: return GREEN
    if score < 60: return AMBER
    if score < 80: return ORANGE
    return RED


# ---------- data ----------
scores = pd.read_csv(ART / "tract_scores_latest.csv")
risk = scores["risk_score"].clip(0, 100).values
mean_risk = float(np.mean(risk))
n_tracts = len(scores)

livable = scores[scores["total_pop_acs"] >= 1500].copy()
livable_sorted = livable.sort_values("risk_score").reset_index(drop=True)
low_tract = livable_sorted.iloc[int(len(livable_sorted) * 0.05)]
high_tract = livable_sorted.iloc[int(len(livable_sorted) * 0.95)]


# =====================================================================
# Figure
# =====================================================================
W, H = 14, 8.6
fig = plt.figure(figsize=(W, H))
fig.patch.set_facecolor(BG)


# ---------------------------------------------------------------------
# 1. Eyebrow + headline + subhead (centered editorial block)
# ---------------------------------------------------------------------
fig.text(
    0.5, 0.945, "THE PROBLEM",
    color=MUTED, fontsize=11, fontweight="bold",
    ha="center", va="center",
)
fig.text(
    0.5, 0.895,
    "Same average.  Same quote.  Different reality.",
    color=INK, fontsize=30, fontweight="bold",
    ha="center", va="center",
)
fig.text(
    0.5, 0.848,
    "Two real postcodes in the same city. One number is used to price both today.",
    color=BODY, fontsize=14,
    ha="center", va="center",
)


# ---------------------------------------------------------------------
# 2. Three-column comparison — pure typography on white
# ---------------------------------------------------------------------
# Layout coords (figure fraction)
top_y    = 0.75
mid_y    = 0.48     # the BIG number sits here
sub_y    = 0.34
foot_y   = 0.295

left_cx  = 0.21
mid_cx   = 0.50
right_cx = 0.79

# Two thin vertical rules separating the columns
rule_y0, rule_y1 = 0.30, 0.78
rule_left_x  = 0.355
rule_right_x = 0.645
fig.add_artist(plt.Line2D(
    [rule_left_x, rule_left_x], [rule_y0, rule_y1],
    color=RULE, linewidth=1.0, transform=fig.transFigure,
))
fig.add_artist(plt.Line2D(
    [rule_right_x, rule_right_x], [rule_y0, rule_y1],
    color=RULE, linewidth=1.0, transform=fig.transFigure,
))


def column(cx, eyebrow, eyebrow_color, postcode, big, big_color, label, foot):
    fig.text(cx, top_y, eyebrow,
             color=eyebrow_color, fontsize=11, fontweight="bold",
             ha="center", va="center")
    fig.text(cx, top_y - 0.045, postcode,
             color=BODY, fontsize=13, ha="center", va="center",
             family="monospace")
    fig.text(cx, mid_y, big,
             color=big_color, fontsize=120, fontweight="bold",
             ha="center", va="center")
    fig.text(cx, sub_y, label,
             color=INK, fontsize=14, ha="center", va="center")
    fig.text(cx, foot_y, foot,
             color=MUTED, fontsize=11, ha="center", va="center")


# Left — the quiet postcode
column(
    cx=left_cx,
    eyebrow="POSTCODE A",
    eyebrow_color=GREEN,
    postcode=str(int(low_tract["tract_geoid"])),
    big=f"{int(low_tract['y_incidents_12m']):,}",
    big_color=GREEN,
    label="actual crime incidents",
    foot=f"last 12 months  ·  ~{int(low_tract['total_pop_acs']):,} residents",
)

# Right — the loud postcode
column(
    cx=right_cx,
    eyebrow="POSTCODE B",
    eyebrow_color=RED,
    postcode=str(int(high_tract["tract_geoid"])),
    big=f"{int(high_tract['y_incidents_12m']):,}",
    big_color=RED,
    label="actual crime incidents",
    foot=f"last 12 months  ·  ~{int(high_tract['total_pop_acs']):,} residents",
)

# Center — what underwriters see today (no numbers, just the system's input)
fig.text(mid_cx, top_y, "TODAY'S QUOTE USES",
         color=MUTED, fontsize=11, fontweight="bold",
         ha="center", va="center")
fig.text(mid_cx, top_y - 0.045, "city-wide average",
         color=BODY, fontsize=13, ha="center", va="center",
         family="monospace")
fig.text(mid_cx, mid_y, f"{mean_risk:.0f}",
         color=INK, fontsize=120, fontweight="bold",
         ha="center", va="center")
fig.text(mid_cx, sub_y, "one number for the entire city",
         color=INK, fontsize=14, ha="center", va="center")
fig.text(mid_cx, foot_y, "applied to every postcode",
         color=MUTED, fontsize=11, ha="center", va="center")


# ---------------------------------------------------------------------
# 3. Thin strip-plot — proof line at the bottom
# ---------------------------------------------------------------------
ax = fig.add_axes([0.08, 0.10, 0.84, 0.13])
rng = np.random.default_rng(7)
y_jitter = rng.normal(0, 0.30, size=len(risk))
colors = [_band_color(s) for s in risk]
ax.scatter(risk, y_jitter, s=10, c=colors, alpha=0.55, edgecolor="none")

# city avg vertical line
ax.axvline(mean_risk, color=INK, linestyle="--", linewidth=1.2, zorder=4)

# highlight the two named tracts
for tract, color in [(low_tract, GREEN), (high_tract, RED)]:
    s = float(tract["risk_score"])
    ax.scatter([s], [0], s=120, facecolor=color, edgecolor=INK,
               linewidth=1.3, zorder=5)

ax.set_xlim(-2, 102)
ax.set_ylim(-1.6, 1.6)
ax.set_yticks([])
ax.set_xticks([0, 25, 50, 75, 100])
ax.tick_params(axis="x", colors=MUTED, labelsize=10, length=0, pad=6)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(RULE)
ax.spines["bottom"].set_linewidth(0.8)

# tiny labels under the axis ticks
ax.text(0,  -2.7, "quiet",   color=MUTED, fontsize=10, ha="left",   va="top")
ax.text(100, -2.7, "highest", color=MUTED, fontsize=10, ha="right",  va="top")

# Strip caption (above the dots, left-aligned editorial)
fig.text(
    0.08, 0.245,
    "EVERY DOT IS ONE REAL POSTCODE IN THE SAME CITY",
    color=MUTED, fontsize=10, fontweight="bold", ha="left",
)
fig.text(
    0.92, 0.245,
    f"{n_tracts:,} postcodes  ·  predicted risk score, 0–100",
    color=MUTED, fontsize=10, ha="right",
)

# Source line, bottom-right
fig.text(
    0.99, 0.022,
    "CrimeScope  ·  Cook County hold-out (Dec 2025)  ·  stand-in for one UK force area",
    ha="right", va="bottom", color=MUTED, fontsize=9, family="monospace",
)

fig.savefig(OUT / "13_problem.png", bbox_inches="tight",
            facecolor=BG, pad_inches=0.35)
plt.close(fig)

print(f"Wrote {(OUT / '13_problem.png').relative_to(ROOT.parent)}")
print(f"  postcodes plotted : {n_tracts:,}")
print(f"  city-wide average : {mean_risk:.1f}")
print(f"  POSTCODE A        : {int(low_tract['tract_geoid'])}  "
      f"score {low_tract['risk_score']:.0f}  "
      f"incidents {int(low_tract['y_incidents_12m'])}")
print(f"  POSTCODE B        : {int(high_tract['tract_geoid'])}  "
      f"score {high_tract['risk_score']:.0f}  "
      f"incidents {int(high_tract['y_incidents_12m'])}")
