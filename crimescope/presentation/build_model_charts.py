"""
CrimeScope — Build model-metrics charts for the deck / docs.

Reads:
  - crimescope/ml/artifacts/model_metadata.json
  - crimescope/ml/artifacts/feature_importance.csv
  - crimescope/ml/artifacts/tract_scores_latest.csv

Writes a set of PNG figures into:
  - crimescope/presentation/figures/

Run:
  python3 crimescope/presentation/build_model_charts.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

# ---------- paths ----------
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ml" / "artifacts"
OUT = ROOT / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- theme (CrimeScope light) ----------
BG = "#ffffff"
PANEL = "#ffffff"
SURFACE = "#f8fafc"
BORDER = "#e2e8f0"
BORDER_HI = "#cbd5e1"
TEXT = "#0f172a"
GRAY1 = "#475569"
GRAY2 = "#64748b"
GRAY3 = "#94a3b8"
ACCENT = "#2563eb"
ACCENT_LO = "#dbeafe"
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#ea580c"
AMBER = "#d97706"
CYAN = "#0891b2"

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "savefig.facecolor": BG,
        "savefig.edgecolor": BG,
        "axes.edgecolor": BORDER_HI,
        "axes.labelcolor": GRAY1,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": GRAY1,
        "ytick.color": GRAY1,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "text.color": TEXT,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "grid.color": BORDER,
        "grid.linewidth": 0.7,
        "legend.frameon": False,
        "legend.labelcolor": TEXT,
        "legend.fontsize": 10,
        "figure.dpi": 140,
    }
)


def _hairline(ax: plt.Axes) -> None:
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BORDER_HI)
        ax.spines[spine].set_linewidth(0.8)


def _annot_caption(fig: plt.Figure, text: str) -> None:
    fig.text(
        0.99,
        0.01,
        text,
        ha="right",
        va="bottom",
        color=GRAY2,
        fontsize=8,
        fontfamily="monospace",
    )


# ---------- load ----------
meta = json.loads((ART / "model_metadata.json").read_text())
fi = pd.read_csv(ART / "feature_importance.csv")
scores = pd.read_csv(ART / "tract_scores_latest.csv")

m = meta["metrics"]
split = meta["split"]
data = meta["data"]
caption = (
    f"CrimeScope • {meta['model_type']} • "
    f"trained {meta['trained_at'][:10]} • "
    f"{data['geography']}"
)

# =====================================================================
# 1) Headline metrics — LightGBM vs Lag-1 Baseline
# =====================================================================
fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))
labels = ["Lag-1 baseline", "CrimeScope LightGBM"]
colors = [GRAY3, ACCENT]

panels = [
    ("MAE", [m["baseline_mae"], m["mae"]], "lower is better", "{:.2f}"),
    ("RMSE", [m["baseline_rmse"], m["rmse"]], "lower is better", "{:.2f}"),
    ("R²", [m["baseline_r2"], m["r2"]], "higher is better", "{:.3f}"),
]

for ax, (name, values, hint, fmt) in zip(axes, panels):
    bars = ax.bar(labels, values, color=colors, width=0.55, edgecolor=BORDER_HI, linewidth=1)
    ax.set_title(name)
    ax.set_xlabel(hint, color=GRAY2, fontsize=9, labelpad=8)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, color=BORDER)
    ax.set_axisbelow(True)
    _hairline(ax)
    ymax = max(values) * 1.25
    ax.set_ylim(0, ymax)
    for b, v in zip(bars, values):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + ymax * 0.025,
            fmt.format(v),
            ha="center",
            va="bottom",
            color=TEXT,
            fontsize=12,
            fontweight="bold",
        )

fig.suptitle(
    "Model performance vs naive baseline   ·   6-month hold-out test",
    color=TEXT,
    fontsize=15,
    fontweight="bold",
    y=0.99,
)
fig.text(
    0.5,
    0.92,
    f"Test window: {split['test_start'][:10]} onward   ·   "
    f"{split['n_train']:,} train rows   ·   {split['n_test']:,} test rows",
    ha="center",
    color=GRAY1,
    fontsize=10,
)
_annot_caption(fig, caption)
fig.tight_layout(rect=[0, 0.03, 1, 0.9])
fig.savefig(OUT / "01_metrics_vs_baseline.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 2) Improvement % — MAE / RMSE
# =====================================================================
fig, ax = plt.subplots(figsize=(9, 4.6))
imp_labels = ["MAE\nimprovement", "RMSE\nimprovement"]
imp_values = [m["mae_improvement_pct"], m["rmse_improvement_pct"]]
bars = ax.barh(imp_labels, imp_values, color=[ACCENT, CYAN], height=0.55, edgecolor=BORDER_HI, linewidth=1)
ax.set_xlim(0, max(imp_values) * 1.35)
ax.set_xlabel("% reduction in error vs lag-1 baseline", color=GRAY1, labelpad=10)
ax.set_title("How much smarter is the model than 'last month repeats'?")
ax.grid(axis="x", linestyle=":", linewidth=0.7, color=BORDER)
ax.set_axisbelow(True)
_hairline(ax)
for b, v in zip(bars, imp_values):
    ax.text(v + 1, b.get_y() + b.get_height() / 2, f"+{v:.1f}%",
            va="center", color=TEXT, fontsize=14, fontweight="bold")
_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "02_improvement_vs_baseline.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 3) Feature importance (top 15)
# =====================================================================
fi_top = fi.sort_values("importance", ascending=True).tail(15)
fig, ax = plt.subplots(figsize=(10, 7))
norm = (fi_top["importance"] - fi_top["importance"].min()) / (
    fi_top["importance"].max() - fi_top["importance"].min() + 1e-9
)
bar_colors = [
    (
        norm.iloc[i] * np.array([0.231, 0.510, 0.965])
        + (1 - norm.iloc[i]) * np.array([0.20, 0.32, 0.45])
    )
    for i in range(len(fi_top))
]
bars = ax.barh(fi_top["feature"], fi_top["importance"], color=bar_colors,
               edgecolor=BORDER_HI, linewidth=0.8)
ax.set_title("Top 15 features by LightGBM split importance")
ax.set_xlabel("number of splits using feature", color=GRAY1, labelpad=8)
ax.grid(axis="x", linestyle=":", linewidth=0.7, color=BORDER)
ax.set_axisbelow(True)
_hairline(ax)
for b, v in zip(bars, fi_top["importance"]):
    ax.text(v + max(fi_top["importance"]) * 0.012, b.get_y() + b.get_height() / 2,
            f"{int(v)}", va="center", color=TEXT, fontsize=9, fontfamily="monospace")
_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "03_feature_importance.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 4) Risk score distribution (latest month)
# =====================================================================
fig, ax = plt.subplots(figsize=(10, 5))
risk = scores["risk_score"].clip(0, 100)
n, bins, patches = ax.hist(risk, bins=40, edgecolor="#ffffff", linewidth=0.7)
# colour bins by risk band
for patch, left in zip(patches, bins[:-1]):
    if left < 30:
        patch.set_facecolor(GREEN)
    elif left < 60:
        patch.set_facecolor(AMBER)
    elif left < 80:
        patch.set_facecolor(ORANGE)
    else:
        patch.set_facecolor(RED)

# percentile markers
p50, p90, p95 = np.percentile(risk, [50, 90, 95])
for p, lab in [(p50, "P50"), (p90, "P90"), (p95, "P95")]:
    ax.axvline(p, color=TEXT, linestyle="--", linewidth=1, alpha=0.6)
    ax.text(p, ax.get_ylim()[1] * 0.92 if False else max(n) * 0.95,
            f"{lab}\n{p:.0f}", color=TEXT, fontsize=9,
            ha="center", va="top",
            bbox=dict(boxstyle="round,pad=0.25", facecolor=SURFACE, edgecolor=BORDER_HI, linewidth=0.6))

ax.set_title(f"Risk-score distribution across {len(scores):,} census tracts ({scores['month_start'].iloc[0][:7]})")
ax.set_xlabel("risk score (0–100, percentile-calibrated)", color=GRAY1, labelpad=8)
ax.set_ylabel("number of tracts", color=GRAY1)
ax.grid(axis="y", linestyle=":", linewidth=0.7, color=BORDER)
ax.set_axisbelow(True)
_hairline(ax)

# legend swatches
import matplotlib.patches as mpatches
legend_handles = [
    mpatches.Patch(color=GREEN, label="Low (<30)"),
    mpatches.Patch(color=AMBER, label="Moderate (30–60)"),
    mpatches.Patch(color=ORANGE, label="Elevated (60–80)"),
    mpatches.Patch(color=RED, label="High (≥80)"),
]
ax.legend(handles=legend_handles, loc="upper right", ncol=2)

_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "04_risk_distribution.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 5) Predicted vs lag-1 — model is non-trivially different from "last month"
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 7.5))
x = scores["lag_1m_count"].values
y = scores["predicted_next_30d"].values
ax.scatter(x, y, s=14, alpha=0.55, color=ACCENT, edgecolor="none")
lim = max(x.max(), y.max()) * 1.05
ax.plot([0, lim], [0, lim], color=GRAY2, linestyle="--", linewidth=1, label="y = x  (lag-1 baseline)")
ax.set_xlim(0, lim)
ax.set_ylim(0, lim)
ax.set_xlabel("incidents in previous 30 days  (lag-1 baseline)", color=GRAY1, labelpad=8)
ax.set_ylabel("model-predicted incidents in next 30 days", color=GRAY1, labelpad=8)
ax.set_title("Model predictions vs naive 'last month repeats' baseline")
ax.grid(True, linestyle=":", linewidth=0.7, color=BORDER)
ax.set_axisbelow(True)
_hairline(ax)

# correlation annotation
corr = np.corrcoef(x, y)[0, 1]
ax.text(
    0.04, 0.96,
    f"Pearson r = {corr:.3f}\nMAE on test = {m['mae']:.2f}\nRMSE on test = {m['rmse']:.2f}",
    transform=ax.transAxes,
    ha="left", va="top", color=TEXT, fontsize=10, fontfamily="monospace",
    bbox=dict(boxstyle="round,pad=0.5", facecolor=SURFACE, edgecolor=BORDER_HI, linewidth=0.8),
)
ax.legend(loc="lower right")
_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "05_predicted_vs_lag1.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 6) Model card — single summary infographic
# =====================================================================
fig = plt.figure(figsize=(13, 7.2))
fig.patch.set_facecolor(BG)
gs = fig.add_gridspec(3, 4, hspace=0.55, wspace=1.2,
                      left=0.06, right=0.97, top=0.88, bottom=0.08)

# title
fig.text(0.06, 0.94, "CrimeScope — Model Card",
         color=TEXT, fontsize=22, fontweight="bold", ha="left", va="center")
fig.text(0.06, 0.905,
         f"{meta['model_type']}  ·  target: next-30-day incident count (log1p)  ·  "
         f"trained {meta['trained_at'][:10]}",
         color=GRAY1, fontsize=11, ha="left", va="center")
fig.text(0.97, 0.94,
         data["geography"], color=ACCENT, fontsize=12, ha="right", va="center",
         fontweight="bold")
fig.text(0.97, 0.905,
         f"data: {data['min_month'][:7]} to {data['max_month'][:7]}  ·  "
         f"{split['n_train']+split['n_test']:,} tract-months",
         color=GRAY1, fontsize=10, ha="right", va="center")

# stat cards (top row)
def stat_card(ax, label, value, sub, color=ACCENT):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_facecolor(PANEL)
    box = FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.9,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        transform=ax.transAxes, facecolor=PANEL,
        edgecolor=BORDER_HI, linewidth=1.0,
    )
    ax.add_patch(box)
    ax.text(0.5, 0.78, label, transform=ax.transAxes,
            color=GRAY1, fontsize=10, ha="center", va="center")
    ax.text(0.5, 0.45, value, transform=ax.transAxes,
            color=color, fontsize=26, fontweight="bold", ha="center", va="center")
    ax.text(0.5, 0.18, sub, transform=ax.transAxes,
            color=GRAY2, fontsize=9, ha="center", va="center")

ax_a = fig.add_subplot(gs[0, 0]); stat_card(ax_a, "MAE",  f"{m['mae']:.2f}",  f"baseline {m['baseline_mae']:.2f}", ACCENT)
ax_b = fig.add_subplot(gs[0, 1]); stat_card(ax_b, "RMSE", f"{m['rmse']:.2f}", f"baseline {m['baseline_rmse']:.2f}", CYAN)
ax_c = fig.add_subplot(gs[0, 2]); stat_card(ax_c, "R²",   f"{m['r2']:.3f}",   f"baseline {m['baseline_r2']:.3f}", GREEN)
ax_d = fig.add_subplot(gs[0, 3]); stat_card(ax_d, "Error reduction",
                                            f"+{m['mae_improvement_pct']:.0f}%",
                                            f"RMSE +{m['rmse_improvement_pct']:.0f}% vs baseline",
                                            ORANGE)

# bottom-left: comparison bars
ax_cmp = fig.add_subplot(gs[1:, :2])
labels = ["MAE", "RMSE"]
base = [m["baseline_mae"], m["baseline_rmse"]]
ours = [m["mae"], m["rmse"]]
xpos = np.arange(len(labels))
w = 0.36
b1 = ax_cmp.bar(xpos - w/2, base, width=w, color=GRAY3, label="Lag-1 baseline",
                edgecolor=BORDER_HI, linewidth=1)
b2 = ax_cmp.bar(xpos + w/2, ours, width=w, color=ACCENT, label="CrimeScope LightGBM",
                edgecolor=BORDER_HI, linewidth=1)
ax_cmp.set_xticks(xpos); ax_cmp.set_xticklabels(labels)
ax_cmp.set_title("Error metrics  ·  6-month hold-out")
ax_cmp.set_ylabel("error (incidents/month)", color=GRAY1)
ax_cmp.grid(axis="y", linestyle=":", linewidth=0.7, color=BORDER)
ax_cmp.set_axisbelow(True)
_hairline(ax_cmp)
ax_cmp.set_ylim(0, max(base) * 1.45)
ax_cmp.legend(loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
for bars in (b1, b2):
    for b in bars:
        v = b.get_height()
        ax_cmp.text(b.get_x() + b.get_width()/2, v + max(base) * 0.025, f"{v:.2f}",
                    ha="center", va="bottom", color=TEXT, fontsize=10, fontweight="bold")

# bottom-right: top features mini
ax_f = fig.add_subplot(gs[1:, 2:])
fi_top10 = fi.sort_values("importance", ascending=True).tail(10)
ax_f.barh(fi_top10["feature"], fi_top10["importance"], color=ACCENT,
          edgecolor=BORDER_HI, linewidth=0.6)
ax_f.set_title("Top 10 drivers (LightGBM split importance)")
ax_f.set_xlabel("splits", color=GRAY1)
ax_f.grid(axis="x", linestyle=":", linewidth=0.7, color=BORDER)
ax_f.set_axisbelow(True)
_hairline(ax_f)
ax_f.tick_params(axis="y", labelsize=9)

_annot_caption(fig, caption)
fig.savefig(OUT / "06_model_card.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# =====================================================================
# 7) Train / test split timeline
# =====================================================================
fig, ax = plt.subplots(figsize=(11, 3.2))
start = pd.to_datetime(data["min_month"])
end = pd.to_datetime(data["max_month"])
test_start = pd.to_datetime(split["test_start"])

ax.barh([0], [(test_start - start).days], left=[start], color=ACCENT,
        edgecolor=ACCENT, linewidth=1.2, height=0.45, alpha=0.85, label=f"Train  ({split['n_train']:,} rows)")
ax.barh([0], [(end - test_start).days], left=[test_start], color=ORANGE,
        edgecolor=ORANGE, linewidth=1.2, alpha=0.8, height=0.45, label=f"Test  ({split['n_test']:,} rows)")

ax.set_yticks([])
ax.set_ylim(-0.7, 0.9)
ax.set_xlim(start - pd.Timedelta(days=30), end + pd.Timedelta(days=30))
ax.set_title("Temporal train / test split")
ax.grid(axis="x", linestyle=":", linewidth=0.7, color=BORDER)
ax.set_axisbelow(True)
_hairline(ax)
ax.legend(loc="upper right", ncol=2)

# annotate dates
for d, label, color, ypos, va in [
    (start, data["min_month"][:7], GRAY1, -0.45, "top"),
    (test_start, f"split · {split['test_start'][:7]}", AMBER, 0.55, "bottom"),
    (end, data["max_month"][:7], GRAY1, -0.45, "top"),
]:
    ax.text(d, ypos, label, ha="center", va=va, color=color, fontsize=9, fontfamily="monospace")
    ax.axvline(d, color=color, linestyle=":", linewidth=0.6, alpha=0.6, ymin=0.15, ymax=0.85)

_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "07_train_test_split.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)

# ---------- summary ----------
print("Wrote:")
for p in sorted(OUT.glob("*.png")):
    print(f"  {p.relative_to(ROOT.parent)}")
