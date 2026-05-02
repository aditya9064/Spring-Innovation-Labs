"""
CrimeScope — Classification-style metrics for the deck / docs.

The CrimeScope model is a regressor (predicts next-30-day incident counts), but
for the insurer/operator workflow the operational question is binary:
"Is this tract a hot-spot next month?".

This script reloads model.joblib + features.parquet, reproduces the temporal
test split, and turns the regression output into:

  Binary task  : hot-spot = top 10% incident-count tract per month.
                 -> Accuracy, Precision, Recall, F1, ROC AUC, PR AUC
                 -> Precision@K curve, ROC curve, PR curve, confusion matrix
  4-tier task  : Low / Moderate / Elevated / High using per-month percentiles.
                 -> Macro F1, per-class precision/recall, confusion matrix

Reads:
  - crimescope/ml/artifacts/model.joblib
  - crimescope/ml/artifacts/features.parquet
  - crimescope/ml/artifacts/model_metadata.json

Writes:
  - crimescope/presentation/figures/08_confusion_matrix_binary.png
  - crimescope/presentation/figures/09_roc_pr_curves.png
  - crimescope/presentation/figures/10_precision_at_k.png
  - crimescope/presentation/figures/11_confusion_matrix_4tier.png
  - crimescope/presentation/figures/12_classification_card.png
  - crimescope/ml/artifacts/classification_metrics.json
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

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
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#ea580c"
AMBER = "#d97706"
CYAN = "#0891b2"

# RGB tuple of the panel base color, used to blend confusion-matrix cells
_PANEL_RGB = np.array([1.0, 1.0, 1.0])

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
        0.99, 0.01, text,
        ha="right", va="bottom",
        color=GRAY2, fontsize=8, fontfamily="monospace",
    )


# ---------- load ----------
meta = json.loads((ART / "model_metadata.json").read_text())
features = meta["features"]
test_start = pd.to_datetime(meta["split"]["test_start"])

model = joblib.load(ART / "model.joblib")
df = pd.read_parquet(ART / "features.parquet")

# reproduce temporal split, drop rows without label (immature months)
df = df.dropna(subset=["y_next_30d_count"])
test = df[df["month_start"] >= test_start].copy()
X_test = test[features]
y_test = test["y_next_30d_count"].values.astype(float)

# model was trained on log1p target -> invert
pred_log = model.predict(X_test)
y_pred = np.clip(np.expm1(pred_log), 0, None)
test["pred"] = y_pred
test["actual"] = y_test

caption = (
    f"CrimeScope • {meta['model_type']} • test {meta['split']['test_start'][:7]}+ "
    f"• {len(test):,} tract-months • {test['tract_geoid'].nunique():,} tracts"
)


# =====================================================================
# Per-month percentile binning (hot-spot definition is per-month, so a quiet
# month doesn't auto-make every tract a hot-spot, and a busy month doesn't
# punish good tracts).
# =====================================================================
def per_month_percentile(series: pd.Series, group: pd.Series) -> pd.Series:
    return series.groupby(group).rank(pct=True, method="average")


test["actual_pct"] = per_month_percentile(test["actual"], test["month_start"])
test["pred_pct"] = per_month_percentile(test["pred"], test["month_start"])

# Binary: hot-spot if in top 10% (per month)
HOT_PCT = 0.90
y_true_bin = (test["actual_pct"] >= HOT_PCT).astype(int).values
y_pred_bin = (test["pred_pct"] >= HOT_PCT).astype(int).values
y_score = test["pred"].values  # raw regression score for ROC/PR

acc = accuracy_score(y_true_bin, y_pred_bin)
prec = precision_score(y_true_bin, y_pred_bin, zero_division=0)
rec = recall_score(y_true_bin, y_pred_bin, zero_division=0)
f1 = f1_score(y_true_bin, y_pred_bin, zero_division=0)
roc_auc = roc_auc_score(y_true_bin, y_score)
pr_auc = average_precision_score(y_true_bin, y_score)

cm = confusion_matrix(y_true_bin, y_pred_bin)  # [[TN FP] [FN TP]]
tn, fp, fn, tp = cm.ravel()
specificity = tn / (tn + fp) if (tn + fp) else 0.0
balanced_acc = 0.5 * (rec + specificity)

# Pretty per-month base rate sanity-check
base_rate = y_true_bin.mean()


# =====================================================================
# 4-tier classification (Low / Moderate / Elevated / High) using per-month
# percentile of the ACTUAL counts as the ground-truth class, and same cuts
# on PREDICTED counts.
# =====================================================================
def to_tier(p: pd.Series) -> pd.Series:
    bins = [-0.001, 0.50, 0.80, 0.95, 1.001]
    labels = ["Low", "Moderate", "Elevated", "High"]
    return pd.cut(p, bins=bins, labels=labels)


CLASSES = ["Low", "Moderate", "Elevated", "High"]
CLASS_COLORS = {"Low": GREEN, "Moderate": AMBER, "Elevated": ORANGE, "High": RED}

y_true_t = to_tier(test["actual_pct"])
y_pred_t = to_tier(test["pred_pct"])

cm4 = confusion_matrix(y_true_t, y_pred_t, labels=CLASSES)
acc4 = accuracy_score(y_true_t, y_pred_t)
macro_f1 = f1_score(y_true_t, y_pred_t, labels=CLASSES, average="macro", zero_division=0)
weighted_f1 = f1_score(y_true_t, y_pred_t, labels=CLASSES, average="weighted", zero_division=0)
per_class_prec = precision_score(y_true_t, y_pred_t, labels=CLASSES, average=None, zero_division=0)
per_class_rec = recall_score(y_true_t, y_pred_t, labels=CLASSES, average=None, zero_division=0)
per_class_f1 = f1_score(y_true_t, y_pred_t, labels=CLASSES, average=None, zero_division=0)


# =====================================================================
# Save metrics JSON
# =====================================================================
metrics_payload = {
    "task": "regression -> classification (top-10% hot-spot per month)",
    "test_start": meta["split"]["test_start"],
    "n_test": int(len(test)),
    "n_tracts": int(test["tract_geoid"].nunique()),
    "binary_hotspot_top_10pct": {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "specificity": round(specificity, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "base_rate": round(base_rate, 4),
        "confusion_matrix": {
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        },
    },
    "tiered_4class": {
        "classes": CLASSES,
        "accuracy": round(acc4, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": {
            c: {
                "precision": round(float(per_class_prec[i]), 4),
                "recall": round(float(per_class_rec[i]), 4),
                "f1": round(float(per_class_f1[i]), 4),
            }
            for i, c in enumerate(CLASSES)
        },
        "confusion_matrix": cm4.tolist(),
    },
}
(ART / "classification_metrics.json").write_text(json.dumps(metrics_payload, indent=2))


# =====================================================================
# 8) Binary confusion matrix
# =====================================================================
def draw_confusion(ax, cm_arr, labels, title, cmap_color=ACCENT):
    cm_norm = cm_arr.astype(float) / max(cm_arr.sum(), 1)
    n = len(labels)
    ax.imshow(np.zeros((n, n)), cmap="binary", vmin=0, vmax=1)
    # custom cell coloring by intensity
    for i in range(n):
        for j in range(n):
            v = cm_arr[i, j]
            intensity = cm_norm[i, j]
            # blend PANEL -> cmap_color by intensity
            target = np.array([
                int(cmap_color[1:3], 16) / 255,
                int(cmap_color[3:5], 16) / 255,
                int(cmap_color[5:7], 16) / 255,
            ])
            blend = 0.06 + 0.94 * intensity
            color = _PANEL_RGB + (target - _PANEL_RGB) * blend
            rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                 facecolor=color, edgecolor=BORDER_HI, linewidth=1)
            ax.add_patch(rect)
            # high-intensity cells get white text, low-intensity (light fill) get dark text
            text_color = "#ffffff" if blend > 0.55 else TEXT
            sub_color = "#e2e8f0" if blend > 0.55 else GRAY1
            ax.text(j, i - 0.12, f"{v:,}", ha="center", va="center",
                    color=text_color, fontsize=14, fontweight="bold")
            ax.text(j, i + 0.22, f"{cm_norm[i,j]*100:.1f}%",
                    ha="center", va="center",
                    color=sub_color, fontsize=9, fontfamily="monospace")
    ax.set_xticks(range(n)); ax.set_xticklabels(labels)
    ax.set_yticks(range(n)); ax.set_yticklabels(labels)
    ax.set_xlim(-0.5, n - 0.5); ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlabel("Predicted", color=GRAY1, labelpad=10)
    ax.set_ylabel("Actual", color=GRAY1, labelpad=10)
    ax.set_title(title)
    for s in ("left", "bottom", "top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


fig, ax = plt.subplots(figsize=(8.5, 8.0))
draw_confusion(ax, cm, ["Not hot-spot", "Hot-spot"],
               "Binary confusion matrix  ·  hot-spot = top 10% per month",
               cmap_color=ACCENT)
fig.tight_layout(rect=[0, 0.12, 1, 1])
fig.text(0.5, 0.075,
         f"Accuracy  {acc:.3f}    Precision  {prec:.3f}    Recall  {rec:.3f}    "
         f"F1  {f1:.3f}    ROC AUC  {roc_auc:.3f}",
         ha="center", color=TEXT, fontsize=11, fontfamily="monospace")
_annot_caption(fig, caption)
fig.savefig(OUT / "08_confusion_matrix_binary.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)


# =====================================================================
# 9) ROC + PR curves
# =====================================================================
fpr, tpr, _ = roc_curve(y_true_bin, y_score)
prec_curve, rec_curve, _ = precision_recall_curve(y_true_bin, y_score)

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# ROC
ax = axes[0]
ax.plot(fpr, tpr, color=ACCENT, linewidth=2.5, label=f"Model (AUC = {roc_auc:.3f})")
ax.plot([0, 1], [0, 1], color=GRAY2, linewidth=1, linestyle="--", label="Random (AUC = 0.500)")
ax.fill_between(fpr, tpr, color=ACCENT, alpha=0.12)
ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
ax.set_xlabel("False positive rate", color=GRAY1)
ax.set_ylabel("True positive rate (recall)", color=GRAY1)
ax.set_title("ROC curve  ·  hot-spot detection")
ax.grid(True, linestyle=":", linewidth=0.7, color=BORDER); ax.set_axisbelow(True)
_hairline(ax)
ax.legend(loc="lower right")

# PR
ax = axes[1]
ax.plot(rec_curve, prec_curve, color=GREEN, linewidth=2.5,
        label=f"Model (AP = {pr_auc:.3f})")
ax.axhline(base_rate, color=GRAY2, linewidth=1, linestyle="--",
           label=f"Base rate ({base_rate:.3f})")
ax.fill_between(rec_curve, prec_curve, color=GREEN, alpha=0.12)
ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
ax.set_xlabel("Recall", color=GRAY1)
ax.set_ylabel("Precision", color=GRAY1)
ax.set_title("Precision–Recall curve")
ax.grid(True, linestyle=":", linewidth=0.7, color=BORDER); ax.set_axisbelow(True)
_hairline(ax)
ax.legend(loc="lower left")

fig.suptitle("Discrimination & ranking quality on the test window",
             color=TEXT, fontsize=15, fontweight="bold", y=1.0)
_annot_caption(fig, caption)
fig.tight_layout(rect=[0, 0.03, 1, 0.95])
fig.savefig(OUT / "09_roc_pr_curves.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)


# =====================================================================
# 10) Precision @ K  (top-K tracts by predicted score, per month)
# =====================================================================
# For each month, sort tracts by predicted, take top-K%, compute precision
# (fraction that are actual top-10% hot-spots) and recall.
ks = np.arange(1, 51)  # 1% through 50% of tracts per month

per_month_metrics = []
for month, g in test.groupby("month_start"):
    g = g.sort_values("pred", ascending=False).reset_index(drop=True)
    n = len(g)
    actual_top = (g["actual_pct"] >= HOT_PCT).astype(int).values
    n_actual_hot = actual_top.sum()
    for k in ks:
        kk = max(1, int(round(n * k / 100)))
        hits = actual_top[:kk].sum()
        per_month_metrics.append(
            {
                "month": month,
                "k_pct": k,
                "precision_at_k": hits / kk,
                "recall_at_k": (hits / n_actual_hot) if n_actual_hot else np.nan,
            }
        )

pmm = pd.DataFrame(per_month_metrics)
agg = pmm.groupby("k_pct").agg(
    precision_mean=("precision_at_k", "mean"),
    precision_lo=("precision_at_k", lambda x: np.percentile(x, 25)),
    precision_hi=("precision_at_k", lambda x: np.percentile(x, 75)),
    recall_mean=("recall_at_k", "mean"),
).reset_index()

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.fill_between(agg["k_pct"], agg["precision_lo"], agg["precision_hi"],
                color=ACCENT, alpha=0.18, label="Precision  (IQR across months)")
ax.plot(agg["k_pct"], agg["precision_mean"], color=ACCENT, linewidth=2.5,
        marker="o", markersize=4, label="Precision  (mean across months)")
ax.plot(agg["k_pct"], agg["recall_mean"], color=GREEN, linewidth=2.5,
        marker="s", markersize=4, label="Recall  (mean across months)")
ax.axhline(base_rate, color=GRAY2, linewidth=1, linestyle="--",
           label=f"Random precision ≈ {base_rate:.2f}")
ax.set_xlim(0, 50); ax.set_ylim(0, 1.02)
ax.set_xlabel("Top K % of tracts inspected per month  (ranked by predicted score)",
              color=GRAY1, labelpad=8)
ax.set_ylabel("Precision  /  Recall", color=GRAY1)
ax.set_title("Precision@K and Recall@K  ·  if the operator focuses on top-K% tracts")
ax.grid(True, linestyle=":", linewidth=0.7, color=BORDER); ax.set_axisbelow(True)
_hairline(ax)

# Annotate top-10% point (the operational hot-spot definition)
p10 = agg.loc[agg["k_pct"] == 10].iloc[0]
ax.scatter([10, 10], [p10["precision_mean"], p10["recall_mean"]],
           s=70, facecolor="none", edgecolor=TEXT, linewidth=1.2, zorder=5)
ax.annotate(
    f"top 10% inspected\nprecision {p10['precision_mean']:.2f}  ·  recall {p10['recall_mean']:.2f}",
    xy=(10, p10["precision_mean"]),
    xytext=(20, min(p10["precision_mean"] + 0.18, 0.95)),
    color=TEXT, fontsize=10,
    arrowprops=dict(arrowstyle="-", color=GRAY1, linewidth=0.8),
    bbox=dict(boxstyle="round,pad=0.4", facecolor=SURFACE, edgecolor=BORDER_HI, linewidth=0.7),
)

ax.legend(loc="lower right")
_annot_caption(fig, caption)
fig.tight_layout()
fig.savefig(OUT / "10_precision_at_k.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)


# =====================================================================
# 11) 4-tier confusion matrix
# =====================================================================
fig, ax = plt.subplots(figsize=(10, 9.0))
draw_confusion(ax, cm4, CLASSES,
               "4-tier confusion matrix  ·  Low / Moderate / Elevated / High",
               cmap_color=ACCENT)
fig.tight_layout(rect=[0, 0.18, 1, 1])
fig.text(0.5, 0.13,
         f"Accuracy  {acc4:.3f}    Macro F1  {macro_f1:.3f}    Weighted F1  {weighted_f1:.3f}",
         ha="center", color=TEXT, fontsize=12, fontfamily="monospace")
# per-class lines stacked
y0 = 0.085
for i, (c, p, r, f) in enumerate(zip(CLASSES, per_class_prec, per_class_rec, per_class_f1)):
    fig.text(0.5, y0 - i * 0.018,
             f"{c:<10}   P {p:.3f}    R {r:.3f}    F1 {f:.3f}",
             ha="center", color=CLASS_COLORS[c],
             fontsize=10, fontfamily="monospace")
_annot_caption(fig, caption)
fig.savefig(OUT / "11_confusion_matrix_4tier.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)


# =====================================================================
# 12) Classification Report Card — single summary infographic
# =====================================================================
fig = plt.figure(figsize=(13, 7.4))
fig.patch.set_facecolor(BG)
gs = fig.add_gridspec(3, 4, hspace=0.55, wspace=1.2,
                      left=0.06, right=0.97, top=0.86, bottom=0.08)

fig.text(0.06, 0.94, "CrimeScope — Classification Report Card",
         color=TEXT, fontsize=22, fontweight="bold", ha="left", va="center")
fig.text(0.06, 0.905,
         f"Operational hot-spot detection  ·  top 10% per month  ·  test window {meta['split']['test_start'][:7]}+",
         color=GRAY1, fontsize=11, ha="left", va="center")
fig.text(0.97, 0.94,
         f"{len(test):,} tract-months", color=ACCENT, fontsize=12, ha="right", va="center",
         fontweight="bold")
fig.text(0.97, 0.905,
         f"{test['tract_geoid'].nunique():,} census tracts  ·  base rate {base_rate:.1%}",
         color=GRAY1, fontsize=10, ha="right", va="center")

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

ax_a = fig.add_subplot(gs[0, 0]); stat_card(ax_a, "Accuracy",  f"{acc:.3f}",  f"balanced {balanced_acc:.3f}", ACCENT)
ax_b = fig.add_subplot(gs[0, 1]); stat_card(ax_b, "Precision", f"{prec:.3f}", f"of flagged tracts", GREEN)
ax_c = fig.add_subplot(gs[0, 2]); stat_card(ax_c, "Recall",    f"{rec:.3f}",  f"of true hot-spots caught", AMBER)
ax_d = fig.add_subplot(gs[0, 3]); stat_card(ax_d, "ROC AUC",   f"{roc_auc:.3f}", f"F1 {f1:.3f}  ·  PR-AUC {pr_auc:.3f}", CYAN)

# ROC mini
ax_r = fig.add_subplot(gs[1:, :2])
ax_r.plot(fpr, tpr, color=ACCENT, linewidth=2.5)
ax_r.plot([0, 1], [0, 1], color=GRAY2, linewidth=1, linestyle="--")
ax_r.fill_between(fpr, tpr, color=ACCENT, alpha=0.15)
ax_r.set_xlim(0, 1); ax_r.set_ylim(0, 1.02)
ax_r.set_xlabel("False positive rate", color=GRAY1)
ax_r.set_ylabel("True positive rate", color=GRAY1)
ax_r.set_title(f"ROC curve  ·  AUC = {roc_auc:.3f}")
ax_r.grid(True, linestyle=":", linewidth=0.7, color=BORDER); ax_r.set_axisbelow(True)
_hairline(ax_r)

# Per-class F1 bars (4-tier task)
ax_p = fig.add_subplot(gs[1:, 2:])
xpos = np.arange(len(CLASSES))
w = 0.27
b1 = ax_p.bar(xpos - w, per_class_prec, width=w, color=ACCENT,
              edgecolor=BORDER_HI, linewidth=0.6, label="Precision")
b2 = ax_p.bar(xpos,     per_class_rec,  width=w, color=AMBER,
              edgecolor=BORDER_HI, linewidth=0.6, label="Recall")
b3 = ax_p.bar(xpos + w, per_class_f1,   width=w, color=GREEN,
              edgecolor=BORDER_HI, linewidth=0.6, label="F1")
ax_p.set_xticks(xpos); ax_p.set_xticklabels(CLASSES)
ax_p.set_ylim(0, 1.05)
ax_p.set_title(f"4-tier per-class scores  ·  Acc {acc4:.3f}  ·  Macro F1 {macro_f1:.3f}")
ax_p.set_ylabel("score", color=GRAY1)
ax_p.grid(axis="y", linestyle=":", linewidth=0.7, color=BORDER); ax_p.set_axisbelow(True)
_hairline(ax_p)
ax_p.legend(loc="upper right", ncol=3, frameon=False)

_annot_caption(fig, caption)
fig.savefig(OUT / "12_classification_card.png", bbox_inches="tight", facecolor=BG)
plt.close(fig)


# ---------- print summary ----------
print("Wrote figures:")
for p in sorted(OUT.glob("*.png")):
    print(f"  {p.relative_to(ROOT.parent)}")
print()
print("Wrote metrics JSON:")
print(f"  {(ART / 'classification_metrics.json').relative_to(ROOT.parent)}")
print()
print("Headline classification metrics (binary hot-spot, top 10% per month):")
print(f"  Accuracy  {acc:.4f}     Balanced acc  {balanced_acc:.4f}")
print(f"  Precision {prec:.4f}     Recall        {rec:.4f}")
print(f"  F1        {f1:.4f}     ROC AUC       {roc_auc:.4f}")
print(f"  PR AUC    {pr_auc:.4f}     Base rate     {base_rate:.4f}")
print(f"  Confusion: TN {tn}  FP {fp}  FN {fn}  TP {tp}")
print()
print("4-tier classification:")
print(f"  Accuracy {acc4:.4f}   Macro F1 {macro_f1:.4f}   Weighted F1 {weighted_f1:.4f}")
for c, p, r, f in zip(CLASSES, per_class_prec, per_class_rec, per_class_f1):
    print(f"    {c:<10} P {p:.3f}  R {r:.3f}  F1 {f:.3f}")
