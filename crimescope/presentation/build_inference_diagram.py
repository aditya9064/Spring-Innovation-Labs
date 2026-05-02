"""
CrimeScope — Inference pipeline diagram for the deck.

Same visual language as the reference architecture slide (App Cluster on the
left, Inference Cluster in the middle, Model Registry on the right, governed
storage + alerting along the bottom), retargeted to the CrimeScope stack:

  Incoming streams : Chicago SODA crime feed, 311 service calls,
                     NOAA weather, Census ACS, FBI NIBRS reference
  App Cluster      : Next.js web, iOS SwiftUI, FastAPI backend
  Inference        : Ray Serve model router →
                       baseline (lag-1)
                       LightGBM regressor (next-30d count)
                       4-tier risk classifier (Low / Mod / Elev / High)
  Registry         : MLflow on Databricks
  Governance       : Unity Catalog (varanasi.default) → retrain pipeline
                     → dashboard → alerting

Writes:
  - crimescope/presentation/figures/14_inference_pipeline.png

Run:
  python3 crimescope/presentation/build_inference_diagram.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, RegularPolygon

# ---------- paths ----------
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- theme ----------
BG = "#ffffff"
PANEL = "#ffffff"
SURFACE = "#f8fafc"
BORDER = "#e2e8f0"
BORDER_HI = "#cbd5e1"
INK = "#0f172a"
GRAY1 = "#475569"
GRAY2 = "#64748b"
GRAY3 = "#94a3b8"

# Brand-ish accents (used for logo tiles, not real marks)
DBX_ORANGE = "#ff3621"     # Databricks
RAY_BLUE = "#00a2c7"       # Ray
MLFLOW_BLUE = "#0194e2"    # MLflow
NEXT_BLACK = "#0a0a0a"     # Next.js
FASTAPI_GREEN = "#009688"  # FastAPI
APPLE_GRAY = "#1f2937"     # iOS / Apple
LGBM_GREEN = "#2e7d32"     # LightGBM
AMBER = "#d97706"
RED = "#dc2626"
GREEN = "#16a34a"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": PANEL,
    "savefig.facecolor": BG,
    "savefig.edgecolor": BG,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.dpi": 160,
})


# =====================================================================
# Drawing helpers
# =====================================================================
def rounded(ax, x, y, w, h, *, fc=PANEL, ec=BORDER_HI, lw=1.6, radius=1.6, z=2):
    """A rounded panel."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.2,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z,
    )
    ax.add_patch(box)
    return box


def chip(ax, cx, cy, label, *, fc, text_color="#ffffff", w=11, h=4.6, fontsize=9.5,
        weight="bold", family="sans-serif"):
    """Rounded label chip — used as a stand-in for a brand logo."""
    box = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.05,rounding_size=1.2",
        facecolor=fc, edgecolor="none", zorder=4,
    )
    ax.add_patch(box)
    ax.text(cx, cy, label, color=text_color, fontsize=fontsize,
            fontweight=weight, ha="center", va="center", family=family,
            zorder=5)


def caption(ax, cx, cy, text, *, color=INK, fontsize=10.5, weight="bold"):
    ax.text(cx, cy, text, color=color, fontsize=fontsize, fontweight=weight,
            ha="center", va="center", zorder=5)


def databricks_mark(ax, cx, cy, *, size=2.6, color=DBX_ORANGE):
    """A small stack of three offset orange diamonds — Databricks-ish accent."""
    for i, offset in enumerate([(-0.6, -0.6), (0.0, 0.0), (0.6, 0.6)]):
        poly = RegularPolygon(
            (cx + offset[0], cy + offset[1]),
            numVertices=4, radius=size,
            orientation=0, facecolor=color, edgecolor="white",
            linewidth=1.2, zorder=6 + i, alpha=0.92,
        )
        ax.add_patch(poly)


def arrow(ax, p0, p1, *, color=INK, lw=1.6, style="-|>", head=10, z=3,
         connection="arc3,rad=0", dashed=False):
    ls = (0, (4, 3)) if dashed else "-"
    a = FancyArrowPatch(
        p0, p1,
        arrowstyle=f"{style},head_length={head},head_width={head*0.55}",
        color=color, linewidth=lw, mutation_scale=12,
        connectionstyle=connection, linestyle=ls, zorder=z,
    )
    ax.add_patch(a)


def stream_card(ax, cx, cy, *, title, sub):
    """A compact 'incoming stream' tile (sits in the top strip)."""
    w, h = 17, 10.5
    rounded(ax, cx - w / 2, cy - h / 2, w, h,
            fc=SURFACE, ec=BORDER_HI, lw=1.2, radius=1.2)
    ax.text(cx, cy + 1.6, title, color=INK, fontsize=10.5,
            fontweight="bold", ha="center", va="center")
    ax.text(cx, cy - 2.2, sub, color=GRAY1, fontsize=8.5,
            ha="center", va="center", family="monospace")


# =====================================================================
# Canvas
# =====================================================================
fig = plt.figure(figsize=(15.5, 10))
fig.patch.set_facecolor(BG)

ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
ax.set_xlim(0, 200)
ax.set_ylim(0, 130)
ax.set_xticks([]); ax.set_yticks([])
ax.set_facecolor(BG)
for s in ax.spines.values():
    s.set_visible(False)

# ----- Title -----
ax.text(100, 125, "CrimeScope · Inference Pipeline",
        color=INK, fontsize=20, fontweight="bold", ha="center", va="center")
ax.text(100, 120,
        "Verified historical scoring, governed live signals — one explainable risk per postcode.",
        color=GRAY1, fontsize=11, ha="center", va="center")

# =====================================================================
# TOP STRIP — Incoming streams (sources -> Lakeflow ingest)
# =====================================================================
TOP_Y = 100.5
TOP_H = 14
rounded(ax, 4, TOP_Y - TOP_H / 2, 192, TOP_H,
        fc=PANEL, ec=INK, lw=2.0, radius=2)

ax.text(15, TOP_Y + 4.6, "Incoming",
        color=INK, fontsize=11, fontweight="bold", ha="center", va="center")
ax.text(15, TOP_Y + 0.2, "Streams",
        color=INK, fontsize=11, fontweight="bold", ha="center", va="center")

# Lakeflow-ish ingest tile
chip(ax, 32, TOP_Y + 2, "Lakeflow", fc=NEXT_BLACK, w=15, h=6, fontsize=11)
ax.text(32, TOP_Y - 4, "Ingest", color=GRAY1, fontsize=9,
        ha="center", va="center", family="monospace")

# Source tiles
sources = [
    (62,  "Chicago SODA",   "police incidents"),
    (88,  "311 Service",    "service calls"),
    (114, "NOAA Weather",   "hourly + daily"),
    (140, "Census ACS",     "demographics"),
    (166, "FBI NIBRS",      "reference"),
]
for sx, title, sub in sources:
    stream_card(ax, sx, TOP_Y + 1, title=title, sub=sub)

# arrows: Lakeflow → each source tile, then bus → down into App Cluster + Inference
for sx, _, _ in sources:
    arrow(ax, (39.5, TOP_Y + 2), (sx - 8.5, TOP_Y + 1),
          color=GRAY1, lw=1.2, head=7)

# =====================================================================
# LEFT — App Cluster
# =====================================================================
APP_X, APP_Y, APP_W, APP_H = 6, 26, 42, 66
rounded(ax, APP_X, APP_Y, APP_W, APP_H, fc=PANEL, ec=INK, lw=2.0, radius=2)
ax.text(APP_X + 4, APP_Y + APP_H - 5, "App Cluster",
        color=INK, fontsize=11, fontweight="bold", ha="left", va="center")
databricks_mark(ax, APP_X + APP_W - 5, APP_Y + APP_H - 5, size=2.2)

# Next.js frontend
chip(ax, APP_X + APP_W / 2, APP_Y + APP_H - 16, "Next.js",
     fc=NEXT_BLACK, w=18, h=7, fontsize=12)
ax.text(APP_X + APP_W / 2, APP_Y + APP_H - 22, "Web Dashboard",
        color=GRAY1, fontsize=9, ha="center", va="center", family="monospace")

# iOS SwiftUI
chip(ax, APP_X + APP_W / 2, APP_Y + APP_H - 32, "iOS · SwiftUI",
     fc=APPLE_GRAY, w=22, h=6.5, fontsize=10.5)
ax.text(APP_X + APP_W / 2, APP_Y + APP_H - 37.5, "Field App",
        color=GRAY1, fontsize=9, ha="center", va="center", family="monospace")

# FastAPI backend
chip(ax, APP_X + APP_W / 2, APP_Y + APP_H - 48, "FastAPI",
     fc=FASTAPI_GREEN, w=18, h=7, fontsize=12)
ax.text(APP_X + APP_W / 2, APP_Y + APP_H - 54, "Python Backend",
        color=GRAY1, fontsize=9, ha="center", va="center", family="monospace")

# arrows down within app cluster
arrow(ax, (APP_X + APP_W / 2, APP_Y + APP_H - 19.5),
      (APP_X + APP_W / 2, APP_Y + APP_H - 28.5), color=INK, lw=1.4, head=8)
arrow(ax, (APP_X + APP_W / 2, APP_Y + APP_H - 35.5),
      (APP_X + APP_W / 2, APP_Y + APP_H - 44.5), color=INK, lw=1.4, head=8)

# =====================================================================
# CENTER — Inference Cluster
# =====================================================================
INF_X, INF_Y, INF_W, INF_H = 58, 26, 96, 66
rounded(ax, INF_X, INF_Y, INF_W, INF_H, fc=PANEL, ec=INK, lw=2.0, radius=2)
ax.text(INF_X + 4, INF_Y + INF_H - 5, "Inference Cluster",
        color=INK, fontsize=11, fontweight="bold", ha="left", va="center")
databricks_mark(ax, INF_X + INF_W - 5, INF_Y + INF_H - 5, size=2.2)
databricks_mark(ax, INF_X + INF_W - 5, INF_Y + 5, size=2.2)
databricks_mark(ax, INF_X + 5, INF_Y + 5, size=2.2)

# Model router (Ray Serve)
ROUTER_CX = INF_X + 22
ROUTER_CY = INF_Y + INF_H / 2
chip(ax, ROUTER_CX, ROUTER_CY, "Ray Serve",
     fc=RAY_BLUE, w=22, h=8, fontsize=12.5)
ax.text(ROUTER_CX, ROUTER_CY - 8.5, "Model Router",
        color=GRAY1, fontsize=9.5, ha="center", va="center", family="monospace")

# Three model heads
HEAD_X = INF_X + INF_W - 24
HEADS = [
    ("Baseline · lag-1",   "naive monthly carry-forward",   ROUTER_CY + 16, "#475569"),
    ("LightGBM Regressor", "predicts next-30d incidents",   ROUTER_CY,      LGBM_GREEN),
    ("4-Tier Classifier",  "Low · Moderate · Elevated · High", ROUTER_CY - 16, AMBER),
]
for label, sub, hy, color in HEADS:
    rounded(ax, HEAD_X - 18, hy - 5, 36, 10,
            fc=SURFACE, ec=color, lw=1.8, radius=1.4)
    ax.text(HEAD_X, hy + 1.2, label, color=INK, fontsize=10.5,
            fontweight="bold", ha="center", va="center")
    ax.text(HEAD_X, hy - 2.6, sub, color=GRAY1, fontsize=8.5,
            ha="center", va="center", family="monospace")
    # arrow router -> head
    arrow(ax, (ROUTER_CX + 11, ROUTER_CY), (HEAD_X - 18, hy),
          color=INK, lw=1.4, head=9, connection="arc3,rad=0.05")

# =====================================================================
# RIGHT — Model Registry (MLflow)
# =====================================================================
REG_CX = 178
REG_CY = INF_Y + INF_H / 2
chip(ax, REG_CX, REG_CY + 2, "MLflow",
     fc=MLFLOW_BLUE, w=24, h=10, fontsize=15)
ax.text(REG_CX, REG_CY - 7, "Model Registry",
        color=INK, fontsize=10.5, fontweight="bold",
        ha="center", va="center")
ax.text(REG_CX, REG_CY - 11, "Databricks · varanasi",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# arrows: registry -> each head (versioned model load)
for _, _, hy, color in HEADS:
    arrow(ax, (REG_CX - 12, REG_CY + 2), (HEAD_X + 18, hy),
          color=color, lw=1.4, head=8, dashed=True,
          connection="arc3,rad=-0.15")

# =====================================================================
# Connections: App Cluster <-> Inference Cluster
# =====================================================================
# FastAPI -> Ray router (request risk)
arrow(ax, (APP_X + APP_W, APP_Y + APP_H - 48), (ROUTER_CX - 11, ROUTER_CY),
      color=INK, lw=1.8, head=10, connection="arc3,rad=-0.15")
ax.text((APP_X + APP_W + ROUTER_CX) / 2, ROUTER_CY + 14,
        "score request",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# Ray router -> FastAPI (return risk + explanation)
arrow(ax, (ROUTER_CX - 11, ROUTER_CY - 2), (APP_X + APP_W, APP_Y + APP_H - 51),
      color=GRAY1, lw=1.2, head=8, dashed=True,
      connection="arc3,rad=0.15")

# Top ingest -> App Cluster (live events)
arrow(ax, (APP_X + 8, TOP_Y - TOP_H / 2),
      (APP_X + APP_W / 2, APP_Y + APP_H - 1),
      color=INK, lw=1.4, head=9)
# Top ingest -> Inference Cluster (features)
arrow(ax, (INF_X + 16, TOP_Y - TOP_H / 2),
      (INF_X + 16, INF_Y + INF_H - 1),
      color=INK, lw=1.4, head=9)

# =====================================================================
# BOTTOM — Unity Catalog → Retrain → Dashboard → Alerting
# =====================================================================
BOT_Y = 13
# Unity Catalog
UC_CX = 36
chip(ax, UC_CX, BOT_Y + 3, "Unity Catalog", fc=DBX_ORANGE, w=26, h=8, fontsize=11.5)
ax.text(UC_CX, BOT_Y - 3.2, "varanasi.default · features + scores",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# Retrain pipeline
RT_CX = 86
rounded(ax, RT_CX - 16, BOT_Y - 1, 32, 10,
        fc=SURFACE, ec=DBX_ORANGE, lw=1.8, radius=1.4)
ax.text(RT_CX, BOT_Y + 5, "Retrain Pipeline",
        color=INK, fontsize=10.5, fontweight="bold",
        ha="center", va="center")
ax.text(RT_CX, BOT_Y + 1.4, "monthly · drift + freshness",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# Dashboard
DASH_CX = 132
chip(ax, DASH_CX, BOT_Y + 3, "Dashboard", fc=DBX_ORANGE, w=24, h=8, fontsize=11.5)
ax.text(DASH_CX, BOT_Y - 3.2, "trust · lift · calibration",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# Alerting
ALERT_CX = 174
rounded(ax, ALERT_CX - 14, BOT_Y - 1, 28, 10,
        fc="#fee2e2", ec=RED, lw=1.8, radius=1.4)
ax.text(ALERT_CX, BOT_Y + 5, "Alerting",
        color=INK, fontsize=10.5, fontweight="bold",
        ha="center", va="center")
ax.text(ALERT_CX, BOT_Y + 1.4, "drift · risk-spike · stale data",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# arrows along the bottom
arrow(ax, (UC_CX + 13, BOT_Y + 3), (RT_CX - 16, BOT_Y + 4),
      color=INK, lw=1.4, head=9)
arrow(ax, (RT_CX + 16, BOT_Y + 4), (DASH_CX - 12, BOT_Y + 3),
      color=INK, lw=1.4, head=9)
arrow(ax, (DASH_CX + 12, BOT_Y + 3), (ALERT_CX - 14, BOT_Y + 4),
      color=INK, lw=1.4, head=9)

# Inference Cluster -> Unity Catalog (publish scores)
arrow(ax, (INF_X + 30, INF_Y), (UC_CX, BOT_Y + 7),
      color=INK, lw=1.4, head=9, connection="arc3,rad=-0.1")
ax.text(46, 24, "publish\nscores",
        color=GRAY1, fontsize=8.5, ha="center", va="center", family="monospace")

# Retrain -> MLflow (register new version)
arrow(ax, (RT_CX, BOT_Y + 9), (REG_CX - 4, REG_CY - 5),
      color=MLFLOW_BLUE, lw=1.4, head=9, dashed=True,
      connection="arc3,rad=-0.25")

# App Cluster -> Unity Catalog (write live events / audit)
arrow(ax, (APP_X + APP_W / 2, APP_Y), (UC_CX - 8, BOT_Y + 7),
      color=GRAY1, lw=1.2, head=8, dashed=True, connection="arc3,rad=0.1")

# =====================================================================
# Footer
# =====================================================================
fig.text(0.99, 0.012,
         "CrimeScope · inference pipeline · Databricks (varanasi catalog) · MLflow · Ray Serve",
         ha="right", va="bottom", color=GRAY2, fontsize=8.5, family="monospace")

fig.savefig(OUT / "14_inference_pipeline.png",
            bbox_inches="tight", facecolor=BG, pad_inches=0.25)
plt.close(fig)

print(f"Wrote {(OUT / '14_inference_pipeline.png').relative_to(ROOT.parent)}")
