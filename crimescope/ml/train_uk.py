"""
CrimeScope ML — UK & Wales local training pipeline (DEV ONLY).

This is a thin local mirror of the Databricks notebooks 02-uk -> 05-uk so a
contributor without a cluster can iterate on a small slice of data.police.uk
data (default: 1 force, 12 months). It is **not** the canonical path that
produces the JSON files shipped to the backend — that always runs on Databricks
(see crimescope/notebooks/ML/02_uk_ingest_and_geos.ipynb onwards).

Usage:

    # Quick smoke test — 1 force, 12 months
    python3 crimescope/ml/train_uk.py

    # All E&W forces, 60 months (slow, ~30 min on a laptop)
    python3 crimescope/ml/train_uk.py --forces all --months 60

Outputs to crimescope/ml/artifacts/uk/:
  - model_log.joblib            — LightGBM (log1p) overall model
  - model_metadata.json         — params + metrics
  - feature_importance.csv
  - lsoa_scores_latest.csv      — latest-month per-LSOA risk scores
  - evaluation_report.txt
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import percentileofscore
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts" / "uk"
CACHE = ROOT / ".cache" / "uk"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

ARCHIVE_BASE = "https://data.police.uk/data/archive"

VIOLENT_CATS = {
    "Violence and sexual offences",
    "Robbery",
    "Possession of weapons",
    "Public order",
}
PROPERTY_CATS = {
    "Burglary",
    "Vehicle crime",
    "Theft from the person",
    "Bicycle theft",
    "Other theft",
    "Shoplifting",
    "Criminal damage and arson",
}

FEATURE_COLS = [
    "lag_1m_count", "lag_2m_count", "lag_3m_count", "lag_6m_count", "lag_12m_count",
    "rolling_mean_3m", "rolling_mean_6m", "rolling_mean_12m",
    "rolling_std_6m", "rolling_max_6m", "rolling_min_6m",
    "violent_lag_1m", "violent_lag_3m", "violent_lag_6m",
    "violent_rolling_3m", "violent_rolling_6m",
    "property_lag_1m", "property_lag_3m", "property_lag_6m",
    "property_rolling_3m", "property_rolling_6m",
    "violent_ratio", "violent_ratio_6m",
    "month_of_year", "month_sin", "month_cos", "year",
    "same_month_last_year", "yoy_change",
    "log_pop", "crime_rate_per_1k",
]


# ---------------------------------------------------------------------------
# 1. Ingest data.police.uk monthly archives
# ---------------------------------------------------------------------------

def months_back(n: int) -> list[str]:
    today = date.today().replace(day=1)
    cursor = (today - timedelta(days=62)).replace(day=1)
    out = []
    for _ in range(n):
        out.append(cursor.strftime("%Y-%m"))
        cursor = (cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def fetch_month(ym: str) -> Path | None:
    dst = CACHE / f"{ym}.zip"
    if dst.exists() and dst.stat().st_size > 1_000_000:
        return dst
    url = f"{ARCHIVE_BASE}/{ym}.zip"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CrimeScope-UK-local/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp, dst.open("wb") as f:
            while True:
                buf = resp.read(1 << 20)
                if not buf:
                    break
                f.write(buf)
        print(f"  fetched {ym}.zip ({dst.stat().st_size / 1_048_576:.1f} MB)")
        return dst
    except urllib.error.HTTPError as e:
        print(f"  skip {ym}: HTTP {e.code}")
        return None


def parse_archive(path: Path, force_filter: str | None) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.endswith("-street.csv"):
                continue
            if force_filter and force_filter not in name:
                continue
            with zf.open(name) as fh:
                try:
                    df = pd.read_csv(fh, dtype=str, usecols=[
                        "Crime ID", "Month", "Falls within",
                        "Longitude", "Latitude",
                        "LSOA code", "LSOA name", "Crime type", "Last outcome category",
                    ])
                except Exception:  # noqa: BLE001
                    continue
            df.columns = [
                "crime_id", "month", "force",
                "longitude", "latitude",
                "lsoa_code", "lsoa_name", "crime_type", "last_outcome",
            ]
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["month_start"] = pd.to_datetime(df["month"] + "-01", errors="coerce")
    df = df[df["lsoa_code"].fillna("").str.startswith(("E0", "W0"))]
    df["category"] = df["crime_type"].fillna("Other crime")
    df["is_violent"] = df["category"].isin(VIOLENT_CATS).astype(int)
    df["is_property"] = df["category"].isin(PROPERTY_CATS).astype(int)
    return df


def ingest(months: int, force_filter: str | None) -> pd.DataFrame:
    cache_path = CACHE / f"crimes_{force_filter or 'all'}_{months}m.parquet"
    if cache_path.exists():
        print(f"[ingest] using cache {cache_path.name}")
        return pd.read_parquet(cache_path)

    target_months = months_back(months)
    print(f"[ingest] {len(target_months)} months ({target_months[0]} .. {target_months[-1]})")
    frames: list[pd.DataFrame] = []
    for ym in target_months:
        zpath = fetch_month(ym)
        if zpath is None:
            continue
        df = parse_archive(zpath, force_filter)
        if not df.empty:
            frames.append(df)
            print(f"  {ym}: cumulative {sum(len(f) for f in frames):,} rows")
    crimes = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    crimes.to_parquet(cache_path, index=False)
    print(f"[ingest] cached {len(crimes):,} rows -> {cache_path.name}")
    return crimes


# ---------------------------------------------------------------------------
# 2. Build LSOA × month panel + features
# ---------------------------------------------------------------------------

def build_panel(crimes: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        crimes.groupby(["lsoa_code", "month_start"])
        .agg(incident_count=("crime_id", "count"),
             violent_count=("is_violent", "sum"),
             property_count=("is_property", "sum"))
        .reset_index()
    )
    all_lsoa = crimes["lsoa_code"].dropna().unique()
    all_months = pd.date_range(monthly["month_start"].min(), monthly["month_start"].max(), freq="MS")
    idx = pd.MultiIndex.from_product([all_lsoa, all_months], names=["lsoa_code", "month_start"])
    panel = pd.DataFrame(index=idx).reset_index()
    panel = panel.merge(monthly, on=["lsoa_code", "month_start"], how="left")
    for c in ["incident_count", "violent_count", "property_count"]:
        panel[c] = panel[c].fillna(0).astype(int)
    panel = panel.sort_values(["lsoa_code", "month_start"]).reset_index(drop=True)
    return panel


def engineer(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    g = df.groupby("lsoa_code")["incident_count"]
    gv = df.groupby("lsoa_code")["violent_count"]
    gp = df.groupby("lsoa_code")["property_count"]

    df["y_next_30d_count"] = g.shift(-1)
    df = df.dropna(subset=["y_next_30d_count"])
    df["y_next_30d_count"] = df["y_next_30d_count"].astype(int)

    for lag in [1, 2, 3, 6, 12]:
        df[f"lag_{lag}m_count"] = g.shift(lag)
    for period in [3, 6, 12]:
        df[f"rolling_mean_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).mean())
        if period >= 6:
            df[f"rolling_std_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).std())
            df[f"rolling_max_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).max())
            df[f"rolling_min_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).min())

    for typ, grp in [("violent", gv), ("property", gp)]:
        for lag in [1, 3, 6]:
            df[f"{typ}_lag_{lag}m"] = grp.shift(lag)
        for period in [3, 6]:
            df[f"{typ}_rolling_{period}m"] = grp.transform(
                lambda x: x.shift(1).rolling(period, min_periods=1).mean()
            )
    df["violent_ratio"] = np.where(df["incident_count"] > 0, df["violent_count"] / df["incident_count"], 0.0)
    df["violent_ratio_6m"] = df.groupby("lsoa_code")["violent_ratio"].transform(
        lambda x: x.shift(1).rolling(6, min_periods=1).mean()
    )

    dt = pd.to_datetime(df["month_start"])
    df["month_of_year"] = dt.dt.month
    df["month_sin"] = np.sin(2 * math.pi * df["month_of_year"] / 12)
    df["month_cos"] = np.cos(2 * math.pi * df["month_of_year"] / 12)
    df["year"] = dt.dt.year
    df["same_month_last_year"] = g.shift(12)
    df["yoy_change"] = np.where(df["same_month_last_year"].notna(),
                                df["incident_count"] - df["same_month_last_year"], np.nan)

    # Dev-mode demographics: a deterministic per-LSOA pseudo-population so the
    # log_pop / crime_rate_per_1k features have something to consume. The
    # canonical numbers come from the Databricks Census + IMD join.
    rng = np.random.default_rng(42)
    pop_map = {c: rng.integers(1200, 4500) for c in df["lsoa_code"].unique()}
    df["total_pop"] = df["lsoa_code"].map(pop_map).astype(int)
    df["log_pop"] = np.log(df["total_pop"])
    rm12 = df["rolling_mean_12m"].fillna(0)
    df["crime_rate_per_1k"] = np.where((df["total_pop"] > 0) & (rm12 > 0),
                                        rm12 / (df["total_pop"] / 1000.0), 0.0)
    return df


# ---------------------------------------------------------------------------
# 3. Train + evaluate (single LightGBM log1p model — no Optuna locally)
# ---------------------------------------------------------------------------

def train(features: pd.DataFrame) -> dict:
    df = features.copy()
    df = df.dropna(subset=["lag_1m_count", "y_next_30d_count"])
    feats = [c for c in FEATURE_COLS if c in df.columns]
    for c in feats:
        df[c] = df[c].fillna(0.0)

    dt = pd.to_datetime(df["month_start"])
    cutoff = (dt.max() - pd.DateOffset(months=2)).replace(day=1)
    train_df = df[dt < cutoff]
    test_df = df[dt >= cutoff]
    if len(test_df) == 0:
        cutoff = (dt.max() - pd.DateOffset(months=1)).replace(day=1)
        train_df = df[dt < cutoff]
        test_df = df[dt >= cutoff]

    X_tr, y_tr = train_df[feats].astype(float), train_df["y_next_30d_count"].astype(float)
    X_te, y_te = test_df[feats].astype(float), test_df["y_next_30d_count"].astype(float)
    print(f"[train] feats={len(feats)} train={len(X_tr):,} test={len(X_te):,} cutoff={cutoff.date()}")

    weights = np.log1p(y_tr) + 1.0
    model = lgb.LGBMRegressor(
        objective="regression", metric="rmse",
        n_estimators=400, learning_rate=0.05, num_leaves=63,
        min_child_samples=20, subsample=0.85, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=0.5, random_state=42, verbosity=-1,
    )
    model.fit(
        X_tr, np.log1p(y_tr), sample_weight=weights,
        eval_set=[(X_te, np.log1p(y_te))],
        callbacks=[lgb.early_stopping(40, verbose=False)],
    )
    pred = np.maximum(np.expm1(np.maximum(model.predict(X_te), 0)), 0)
    mae = mean_absolute_error(y_te, pred)
    rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
    r2 = r2_score(y_te, pred)
    print(f"[eval] MAE={mae:.3f} RMSE={rmse:.3f} R2={r2:.3f}")

    joblib.dump(model, ARTIFACTS / "model_log.joblib")
    pd.DataFrame({"feature": feats, "importance": model.feature_importances_}) \
        .sort_values("importance", ascending=False) \
        .to_csv(ARTIFACTS / "feature_importance.csv", index=False)

    metadata = {
        "model_type": "LGBMRegressor",
        "geography": "UK & Wales LSOA (data.police.uk)",
        "features": feats,
        "n_features": len(feats),
        "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)},
        "split": {"test_start": str(cutoff.date()), "n_train": len(X_tr), "n_test": len(X_te)},
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (ARTIFACTS / "model_metadata.json").write_text(json.dumps(metadata, indent=2))

    # Latest-month per-LSOA scores
    latest = df[dt == dt.max()].copy()
    if not latest.empty:
        Xl = latest[feats].astype(float).fillna(0.0)
        p = np.maximum(np.expm1(np.maximum(model.predict(Xl), 0)), 0)
        latest["predicted_next_30d"] = np.round(p, 2)
        pct = np.array([percentileofscore(p, v, kind="rank") for v in p])
        log_p = np.log1p(p)
        lo, hi = log_p.min(), log_p.max()
        abs_s = (log_p - lo) / (hi - lo) * 100 if hi > lo else np.full_like(log_p, 50.0)
        latest["risk_score"] = np.round(0.7 * pct + 0.3 * abs_s, 1)
        latest[["lsoa_code", "month_start", "incident_count",
                "predicted_next_30d", "risk_score"]] \
            .to_csv(ARTIFACTS / "lsoa_scores_latest.csv", index=False)

    (ARTIFACTS / "evaluation_report.txt").write_text(
        f"CrimeScope UK (local dev mirror) — {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"Geography: LSOA  |  Features: {len(feats)}  |  Train: {len(X_tr):,}  Test: {len(X_te):,}\n"
        f"MAE: {mae:.4f}  |  RMSE: {rmse:.4f}  |  R2: {r2:.4f}\n"
        f"Test cutoff: {cutoff.date()}\n"
    )
    return metadata


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Local UK & Wales training (dev mirror)")
    parser.add_argument("--months", type=int, default=12, help="Months back to ingest (default 12).")
    parser.add_argument(
        "--forces", type=str, default="metropolitan",
        help="Substring filter on per-month CSV name (e.g. 'metropolitan', 'west-midlands'). "
             "Use 'all' to ingest every force (slow).",
    )
    args = parser.parse_args()

    force_filter = None if args.forces.lower() == "all" else args.forces

    t0 = time.time()
    print("=" * 60)
    print(f"CrimeScope UK (local mirror) — months={args.months} forces={args.forces}")
    print("=" * 60)
    crimes = ingest(args.months, force_filter)
    if crimes.empty:
        print("No data ingested — aborting.")
        return 1
    panel = build_panel(crimes)
    print(f"[panel] {len(panel):,} rows, {panel['lsoa_code'].nunique()} LSOAs, "
          f"{panel['month_start'].nunique()} months")
    feats = engineer(panel)
    train(feats)
    print(f"\nDone in {time.time() - t0:.1f}s. Artifacts in {ARTIFACTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
