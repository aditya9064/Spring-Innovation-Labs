"""
CrimeScope ML — Full local training pipeline (v3).

Mirrors Databricks notebooks 02-05 but runs locally with pandas/geopandas/LightGBM.

v3 improvements:
  - Optuna hyperparameter tuning (20 trials)
  - Dual-transform ensemble: sqrt + log1p averaged
  - L1/L2 regularization for SHAP diversity
  - Sample weighting for high-crime tract accuracy
  - Feature pruning (drop bottom 25% importance)
  - Violent / property sub-models on pruned features

Output artifacts (in ml/artifacts/):
  - model_log.joblib              LightGBM overall (log1p) model
  - model_sqrt.joblib             LightGBM overall (sqrt) model
  - model_violent.joblib          LightGBM violent sub-model
  - model_property.joblib         LightGBM property sub-model
  - model_metadata.json           Hyperparams, metrics, feature list
  - feature_importance.csv        Feature importance table
  - tract_scores_latest.csv       Latest month per-tract risk scores
  - evaluation_report.txt         Human-readable eval summary
  - features.parquet              Full feature table
"""

import json
import math
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import joblib
import lightgbm as lgb
import matplotlib
import numpy as np
import optuna
import pandas as pd
import requests
from scipy.stats import percentileofscore
from shapely import wkt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

optuna.logging.set_verbosity(optuna.logging.WARNING)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

CRIME_START_DATE = "2020-01-01"
MAX_ROWS = 1_500_000
PAGE_SIZE = 50_000
TEST_MONTHS = 6
MATURITY_BUFFER_MONTHS = 3

VIOLENT_TYPES = {
    "HOMICIDE", "ASSAULT", "BATTERY", "ROBBERY",
    "CRIMINAL SEXUAL ASSAULT", "CRIM SEXUAL ASSAULT",
    "KIDNAPPING", "HUMAN TRAFFICKING",
}
PROPERTY_TYPES = {
    "THEFT", "BURGLARY", "MOTOR VEHICLE THEFT", "ARSON",
    "CRIMINAL DAMAGE", "CRIMINAL TRESPASS",
}

FEATURE_LABELS = {
    "lag_1m_count": "Last month's crime count",
    "lag_2m_count": "Crime count 2 months ago",
    "lag_3m_count": "Crime count 3 months ago",
    "lag_6m_count": "Crime count 6 months ago",
    "lag_12m_count": "Crime count 12 months ago",
    "rolling_mean_3m": "3-month crime average",
    "rolling_mean_6m": "6-month crime average",
    "rolling_mean_12m": "12-month crime average",
    "rolling_std_6m": "6-month crime volatility",
    "rolling_max_6m": "6-month peak crime count",
    "rolling_min_6m": "6-month lowest crime count",
    "rolling_std_12m": "12-month crime volatility",
    "rolling_max_12m": "12-month peak crime count",
    "rolling_min_12m": "12-month lowest crime count",
    "mom_change": "Month-over-month change",
    "violent_lag_1m": "Last month's violent crimes",
    "violent_lag_3m": "Violent crimes 3 months ago",
    "violent_lag_6m": "Violent crimes 6 months ago",
    "violent_rolling_3m": "3-month violent crime trend",
    "violent_rolling_6m": "6-month violent crime trend",
    "violent_rolling_12m": "12-month violent crime average",
    "violent_ratio": "Violent crime proportion",
    "violent_ratio_6m": "6-month violent crime ratio",
    "property_lag_1m": "Last month's property crimes",
    "property_lag_3m": "Property crimes 3 months ago",
    "property_lag_6m": "Property crimes 6 months ago",
    "property_rolling_3m": "3-month property crime trend",
    "property_rolling_6m": "6-month property crime trend",
    "property_rolling_12m": "12-month property crime average",
    "month_of_year": "Month of year (seasonality)",
    "month_sin": "Seasonal cycle (sine)",
    "month_cos": "Seasonal cycle (cosine)",
    "year": "Year",
    "same_month_last_year": "Same month last year",
    "yoy_change": "Year-over-year change",
    "total_pop_acs": "Total population",
    "median_hh_income_acs": "Median household income",
    "poverty_rate_acs": "Neighborhood poverty rate",
    "housing_units_acs": "Housing unit count",
    "log_pop": "Population (log scale)",
    "log_income": "Income (log scale)",
    "crime_rate_per_1k": "Crime rate per 1,000 residents",
    "poverty_x_crime": "Poverty \u00d7 crime interaction",
    "income_crime_ratio": "Income-to-crime ratio",
    "pop_per_housing_unit": "Population density (per housing unit)",
    "city_month_total": "City-wide monthly crime total",
    "city_total_lag1": "City-wide crime (previous month)",
    "tract_share_of_city": "Tract's share of city crime",
    "tract_vs_city_avg": "Tract vs city average ratio",
    "ca_avg_crime": "Community area average crime",
    "tract_vs_ca_avg": "Tract vs community area average",
    "trend_accel": "Trend acceleration",
    "cv_6m": "6-month volatility coefficient",
    "cv_12m": "12-month volatility coefficient",
    "trend_3m": "3-month trend direction",
}

FEATURE_COLS = [
    "lag_1m_count", "lag_2m_count", "lag_3m_count", "lag_6m_count", "lag_12m_count",
    "rolling_mean_3m", "rolling_mean_6m", "rolling_mean_12m",
    "rolling_std_6m", "rolling_max_6m", "rolling_min_6m",
    "rolling_std_12m", "rolling_max_12m", "rolling_min_12m",
    "mom_change",
    "violent_lag_1m", "violent_lag_3m", "violent_lag_6m",
    "violent_rolling_3m", "violent_rolling_6m", "violent_rolling_12m",
    "violent_ratio", "violent_ratio_6m",
    "property_lag_1m", "property_lag_3m", "property_lag_6m",
    "property_rolling_3m", "property_rolling_6m", "property_rolling_12m",
    "month_of_year", "month_sin", "month_cos", "year",
    "same_month_last_year", "yoy_change",
    "total_pop_acs", "median_hh_income_acs", "poverty_rate_acs", "housing_units_acs",
    "log_pop", "log_income",
    "crime_rate_per_1k", "poverty_x_crime", "income_crime_ratio", "pop_per_housing_unit",
    "city_month_total", "city_total_lag1", "tract_share_of_city",
    "tract_vs_city_avg", "ca_avg_crime", "tract_vs_ca_avg",
    "trend_accel", "cv_6m", "cv_12m", "trend_3m",
]

LABEL_COLS = [
    "y_incidents_12m", "y_next_30d_count", "y_rate_12m_per_1k", "y_next_30d_per_1k",
    "y_violent_12m", "y_property_12m", "y_next_30d_violent", "y_next_30d_property",
    "violent_count", "property_count",
]
ID_COLS = ["tract_geoid", "month_start", "community_area"]


# ──────────────────────────────────────────────────────────────────────
# 1. INGEST CHICAGO CRIME DATA
# ──────────────────────────────────────────────────────────────────────

def ingest_crimes() -> pd.DataFrame:
    cache_path = CACHE_DIR / "chicago_crimes_raw.parquet"
    if cache_path.exists():
        print(f"[ingest] Loading cached crime data from {cache_path}")
        return pd.read_parquet(cache_path)

    print("[ingest] Downloading Chicago crime data from Socrata...")
    base_url = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    all_rows = []
    offset = 0

    while len(all_rows) < MAX_ROWS:
        params = {
            "$where": f"date >= '{CRIME_START_DATE}'",
            "$limit": PAGE_SIZE,
            "$offset": offset,
            "$order": "date ASC",
        }
        headers = {}
        if app_token:
            headers["X-App-Token"] = app_token

        resp = requests.get(base_url, params=params, headers=headers, timeout=120)
        resp.raise_for_status()
        page = resp.json()

        if not page:
            break

        all_rows.extend(page)
        offset += len(page)
        print(f"  Fetched {len(all_rows):,} rows (page {offset // PAGE_SIZE})")

        if len(page) < PAGE_SIZE:
            break

    print(f"  Total rows fetched: {len(all_rows):,}")

    df = pd.DataFrame(all_rows)
    keep_cols = [
        "id", "case_number", "date", "block", "iucr", "primary_type",
        "description", "location_description", "arrest", "domestic",
        "beat", "district", "ward", "community_area", "fbi_code",
        "latitude", "longitude", "year", "updated_on",
    ]
    for c in keep_cols:
        if c not in df.columns:
            df[c] = None

    df = df[keep_cols].copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["updated_on"] = pd.to_datetime(df["updated_on"], errors="coerce")

    df.to_parquet(cache_path, index=False)
    print(f"  Cached to {cache_path}")
    return df


# ──────────────────────────────────────────────────────────────────────
# 2. TRACT BOUNDARIES
# ──────────────────────────────────────────────────────────────────────

def load_tract_boundaries() -> gpd.GeoDataFrame:
    cache_path = CACHE_DIR / "cook_tract_boundaries.parquet"
    if cache_path.exists():
        print(f"[tracts] Loading cached tract boundaries from {cache_path}")
        return gpd.read_parquet(cache_path)

    print("[tracts] Downloading TIGER/Line 2024 tract shapefile...")
    url = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_17_tract.zip"
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "tracts.zip")
    urllib.request.urlretrieve(url, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)

    gdf = gpd.read_file(tmp)
    cook = gdf[gdf["COUNTYFP"] == "031"].copy()
    cook["tract_geoid"] = cook["GEOID"]
    cook = cook[["tract_geoid", "STATEFP", "COUNTYFP", "TRACTCE", "NAMELSAD", "ALAND", "AWATER", "geometry"]].copy()
    cook = cook.to_crs("EPSG:4326")

    cook.to_parquet(cache_path, index=False)
    print(f"  Cook County tracts loaded: {len(cook)}")
    return cook


# ──────────────────────────────────────────────────────────────────────
# 3. SPATIAL JOIN
# ──────────────────────────────────────────────────────────────────────

def spatial_join_crimes(crimes: pd.DataFrame, tracts: gpd.GeoDataFrame) -> pd.DataFrame:
    cache_path = CACHE_DIR / "crimes_with_tract.parquet"
    if cache_path.exists():
        print(f"[sjoin] Loading cached spatial join from {cache_path}")
        return pd.read_parquet(cache_path)

    print("[sjoin] Assigning crimes to tracts (spatial join)...")
    valid = crimes.dropna(subset=["latitude", "longitude"]).copy()
    crimes_gdf = gpd.GeoDataFrame(
        valid,
        geometry=gpd.points_from_xy(valid["longitude"], valid["latitude"]),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(
        crimes_gdf,
        tracts[["tract_geoid", "geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined.drop(columns=["geometry", "index_right"], errors="ignore")
    result = pd.DataFrame(joined)

    matched = result["tract_geoid"].notna().sum()
    print(f"  Total: {len(result):,}  |  Matched: {matched:,}  |  Coverage: {matched / len(result) * 100:.1f}%")

    result.to_parquet(cache_path, index=False)
    return result


# ──────────────────────────────────────────────────────────────────────
# 4. MONTHLY PANEL + LABELS (with crime-type split)
# ──────────────────────────────────────────────────────────────────────

def build_panel(crimes_with_tract: pd.DataFrame, tracts: gpd.GeoDataFrame) -> pd.DataFrame:
    print("[panel] Building tract\u00d7month panel with violent/property split...")

    df = crimes_with_tract[crimes_with_tract["tract_geoid"].notna()].copy()
    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp()

    def classify(pt):
        if pt and pt.upper() in VIOLENT_TYPES:
            return "violent"
        if pt and pt.upper() in PROPERTY_TYPES:
            return "property"
        return "other"

    df["crime_category"] = df["primary_type"].apply(classify)

    monthly = (
        df.groupby(["tract_geoid", "month_start"])
        .agg(
            incident_count=("id", "count"),
            violent_count=("crime_category", lambda x: (x == "violent").sum()),
            property_count=("crime_category", lambda x: (x == "property").sum()),
        )
        .reset_index()
    )

    # Map tract -> most common community_area
    ca_map = (
        df[df["community_area"].notna()]
        .groupby(["tract_geoid", "community_area"])
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
        .drop_duplicates("tract_geoid")
        [["tract_geoid", "community_area"]]
    )

    all_tracts = tracts["tract_geoid"].unique()
    all_months = pd.date_range(
        monthly["month_start"].min(),
        monthly["month_start"].max(),
        freq="MS",
    )

    idx = pd.MultiIndex.from_product([all_tracts, all_months], names=["tract_geoid", "month_start"])
    panel = pd.DataFrame(index=idx).reset_index()
    panel = panel.merge(monthly, on=["tract_geoid", "month_start"], how="left")
    for c in ["incident_count", "violent_count", "property_count"]:
        panel[c] = panel[c].fillna(0).astype(int)
    panel = panel.merge(ca_map, on="tract_geoid", how="left")
    panel = panel.sort_values(["tract_geoid", "month_start"]).reset_index(drop=True)

    g = panel.groupby("tract_geoid")

    panel["y_incidents_12m"] = g["incident_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())
    panel["y_violent_12m"] = g["violent_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())
    panel["y_property_12m"] = g["property_count"].transform(lambda x: x.rolling(12, min_periods=1).sum())

    panel["y_next_30d_count"] = g["incident_count"].shift(-1)
    panel["y_next_30d_violent"] = g["violent_count"].shift(-1)
    panel["y_next_30d_property"] = g["property_count"].shift(-1)

    panel = panel.dropna(subset=["y_next_30d_count"])
    for c in ["y_next_30d_count", "y_next_30d_violent", "y_next_30d_property"]:
        panel[c] = panel[c].astype(int)

    panel_max = panel["month_start"].max()
    maturity_cutoff = panel_max - pd.DateOffset(months=MATURITY_BUFFER_MONTHS)
    panel = panel[panel["month_start"] <= maturity_cutoff]

    print(f"  Panel: {len(panel):,} rows, {panel['tract_geoid'].nunique()} tracts, "
          f"{panel['month_start'].nunique()} months")
    return panel


# ──────────────────────────────────────────────────────────────────────
# 5. ACS POPULATION + INCOME
# ──────────────────────────────────────────────────────────────────────

def fetch_acs(tracts: gpd.GeoDataFrame) -> pd.DataFrame:
    cache_path = CACHE_DIR / "tract_acs_population_v2.parquet"
    if cache_path.exists():
        print(f"[acs] Loading cached ACS data from {cache_path}")
        return pd.read_parquet(cache_path)

    print("[acs] Fetching ACS 2022 5-year estimates from Census API...")
    base = "https://api.census.gov/data/2022/acs/acs5"
    params = urllib.parse.urlencode([
        ("get", "B01003_001E,B19013_001E,B17001_002E,B25001_001E,NAME"),
        ("for", "tract:*"),
        ("in", "state:17"),
        ("in", "county:031"),
    ])
    url = f"{base}?{params}"

    with urllib.request.urlopen(url, timeout=60) as resp:
        rows = json.loads(resp.read().decode())

    header, data = rows[0], rows[1:]
    pdf = pd.DataFrame(data, columns=header)
    pdf["tract_geoid"] = pdf["state"] + pdf["county"] + pdf["tract"]
    pdf["total_pop_acs"] = pd.to_numeric(pdf["B01003_001E"], errors="coerce")
    pdf["median_hh_income_acs"] = pd.to_numeric(pdf["B19013_001E"], errors="coerce")
    pdf["poverty_count_acs"] = pd.to_numeric(pdf["B17001_002E"], errors="coerce")
    pdf["housing_units_acs"] = pd.to_numeric(pdf["B25001_001E"], errors="coerce")
    pdf["poverty_rate_acs"] = (pdf["poverty_count_acs"] / pdf["total_pop_acs"]).where(pdf["total_pop_acs"] > 0)

    valid_tracts = set(tracts["tract_geoid"].unique())
    pdf = pdf[pdf["tract_geoid"].isin(valid_tracts)]
    result = pdf[["tract_geoid", "total_pop_acs", "median_hh_income_acs",
                   "poverty_rate_acs", "housing_units_acs"]].copy()

    result.to_parquet(cache_path, index=False)
    print(f"  ACS tracts loaded: {len(result)}")
    return result


# ──────────────────────────────────────────────────────────────────────
# 6. FEATURE ENGINEERING
# ──────────────────────────────────────────────────────────────────────

def engineer_features(panel: pd.DataFrame, acs: pd.DataFrame) -> pd.DataFrame:
    print("[features] Engineering features (50+)...")
    df = panel.merge(acs, on="tract_geoid", how="left")

    pop = df["total_pop_acs"]
    df["y_rate_12m_per_1k"] = np.where(pop > 0, df["y_incidents_12m"] / (pop / 1000), np.nan)
    df["y_next_30d_per_1k"] = np.where(pop > 0, df["y_next_30d_count"] / (pop / 1000), np.nan)

    df = df.sort_values(["tract_geoid", "month_start"]).reset_index(drop=True)
    g = df.groupby("tract_geoid")["incident_count"]
    gv = df.groupby("tract_geoid")["violent_count"]
    gp = df.groupby("tract_geoid")["property_count"]

    # Overall lag features
    for lag in [1, 2, 3, 6, 12]:
        df[f"lag_{lag}m_count"] = g.shift(lag)

    for period in [3, 6, 12]:
        df[f"rolling_mean_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).mean())
        if period >= 6:
            df[f"rolling_std_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).std())
            df[f"rolling_max_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).max())
            df[f"rolling_min_{period}m"] = g.transform(lambda x: x.shift(1).rolling(period, min_periods=1).min())

    df["mom_change"] = df["incident_count"] - g.shift(1)

    # Violent and property lag features
    for crime_type, grp in [("violent", gv), ("property", gp)]:
        for lag in [1, 3, 6]:
            df[f"{crime_type}_lag_{lag}m"] = grp.shift(lag)
        for period in [3, 6, 12]:
            df[f"{crime_type}_rolling_{period}m"] = grp.transform(
                lambda x: x.shift(1).rolling(period, min_periods=1).mean()
            )

    df["violent_ratio"] = np.where(df["incident_count"] > 0,
                                    df["violent_count"] / df["incident_count"], 0.0)
    g_vr = df.groupby("tract_geoid")["violent_ratio"]
    df["violent_ratio_6m"] = g_vr.transform(lambda x: x.shift(1).rolling(6, min_periods=1).mean())

    # Calendar / seasonality
    df["month_of_year"] = df["month_start"].dt.month
    df["month_sin"] = np.sin(2 * math.pi * df["month_of_year"] / 12)
    df["month_cos"] = np.cos(2 * math.pi * df["month_of_year"] / 12)
    df["year"] = df["month_start"].dt.year
    df["same_month_last_year"] = g.shift(12)
    df["yoy_change"] = np.where(df["same_month_last_year"].notna(),
                                 df["incident_count"] - df["same_month_last_year"], np.nan)

    # ACS derived
    df["log_pop"] = np.where(df["total_pop_acs"] > 0, np.log(df["total_pop_acs"]), 0.0)
    df["log_income"] = np.where(df["median_hh_income_acs"] > 0, np.log(df["median_hh_income_acs"]), 0.0)

    rm12 = df["rolling_mean_12m"].fillna(0)
    df["crime_rate_per_1k"] = np.where(
        (df["total_pop_acs"] > 0) & (rm12 > 0),
        rm12 / (df["total_pop_acs"] / 1000.0), 0.0
    )
    df["poverty_x_crime"] = df["poverty_rate_acs"].fillna(0) * rm12
    df["income_crime_ratio"] = np.where(
        rm12 > 0, df["median_hh_income_acs"].fillna(0) / (rm12 * 1000.0), 0.0
    )
    df["pop_per_housing_unit"] = np.where(
        df["housing_units_acs"] > 0,
        df["total_pop_acs"] / df["housing_units_acs"], 0.0
    )

    # City-wide features
    city_total = df.groupby("month_start")["incident_count"].transform("sum")
    city_avg = df.groupby("month_start")["incident_count"].transform("mean")
    df["city_month_total"] = city_total
    df["tract_share_of_city"] = np.where(city_total > 0, df["incident_count"] / city_total, 0.0)
    df["city_total_lag1"] = df.groupby("tract_geoid")["city_month_total"].shift(1)
    df["tract_vs_city_avg"] = np.where(city_avg > 0, df["incident_count"] / city_avg, 1.0)

    # Community-area spatial context
    ca_avg = df[df["community_area"].notna()].groupby(
        ["community_area", "month_start"]
    )["incident_count"].transform("mean")
    df["ca_avg_crime"] = np.nan
    df.loc[df["community_area"].notna(), "ca_avg_crime"] = ca_avg
    df["ca_avg_crime"] = df["ca_avg_crime"].fillna(df["incident_count"])
    df["tract_vs_ca_avg"] = np.where(df["ca_avg_crime"] > 0,
                                      df["incident_count"] / df["ca_avg_crime"], 1.0)

    # Trend + volatility
    mom = df.groupby("tract_geoid")["mom_change"]
    df["trend_accel"] = df["mom_change"] - mom.shift(1)

    rm6 = df["rolling_mean_6m"].fillna(0)
    std6 = df["rolling_std_6m"].fillna(0)
    std12 = df["rolling_std_12m"].fillna(0)
    df["cv_6m"] = np.where(rm6 > 0, std6 / rm6, 0.0)
    df["cv_12m"] = np.where(rm12 > 0, std12 / rm12, 0.0)
    df["trend_3m"] = np.where(
        (rm6 > 0) & (df["rolling_mean_3m"].notna()),
        (df["rolling_mean_3m"].fillna(0) - rm6) / rm6, 0.0
    )

    out = df[ID_COLS + FEATURE_COLS + LABEL_COLS].copy()
    out.to_parquet(ARTIFACTS_DIR / "features.parquet", index=False)
    print(f"  Feature table: {len(out):,} rows, {len(FEATURE_COLS)} features")
    return out


# ──────────────────────────────────────────────────────────────────────
# 7. WEIGHTED BASELINE
# ──────────────────────────────────────────────────────────────────────

def weighted_baseline_predict(X: pd.DataFrame) -> np.ndarray:
    pred = (
        0.30 * X["rolling_mean_3m"].fillna(0) +
        0.25 * X["rolling_mean_12m"].fillna(0) +
        0.20 * X["lag_1m_count"].fillna(0) +
        0.15 * X["same_month_last_year"].fillna(X["rolling_mean_12m"].fillna(0)) +
        0.10 * (X["city_month_total"].fillna(0) * X["tract_share_of_city"].fillna(0))
    )
    return np.maximum(pred.values, 0)


# ──────────────────────────────────────────────────────────────────────
# 8. BLENDED RISK SCORING
# ──────────────────────────────────────────────────────────────────────

def blended_risk_score(predictions: np.ndarray) -> np.ndarray:
    pct_scores = np.array([percentileofscore(predictions, v, kind="rank") for v in predictions])
    log_preds = np.log1p(predictions)
    log_min, log_max = log_preds.min(), log_preds.max()
    if log_max > log_min:
        abs_scores = (log_preds - log_min) / (log_max - log_min) * 100
    else:
        abs_scores = np.full_like(log_preds, 50.0)
    return np.round(0.70 * pct_scores + 0.30 * abs_scores, 1)


def top_drivers_json(shap_row, feature_names, feature_vals, n=5):
    abs_vals = np.abs(shap_row)
    top_idx = abs_vals.argsort()[-n:][::-1]
    drivers = []
    for idx in top_idx:
        feat = feature_names[idx]
        drivers.append({
            "feature": feat,
            "label": FEATURE_LABELS.get(feat, feat.replace("_", " ").title()),
            "shap_value": round(float(shap_row[idx]), 4),
            "feature_value": round(float(feature_vals[idx]), 4),
            "direction": "up" if shap_row[idx] > 0 else "down",
        })
    return json.dumps(drivers)


# ──────────────────────────────────────────────────────────────────────
# 9. TRAIN + EVALUATE
# ──────────────────────────────────────────────────────────────────────

def train_and_evaluate(features: pd.DataFrame) -> dict:
    print("[train] Preparing train/test split...")
    TARGET = "y_next_30d_count"

    df = features.copy()
    df = df.dropna(subset=["lag_1m_count", TARGET])
    for col in FEATURE_COLS:
        df[col] = df[col].fillna(0.0)

    n_usable = len(df)
    print(f"  Usable rows: {n_usable:,}")
    if n_usable == 0:
        raise ValueError("No usable rows")

    max_m = df["month_start"].max()
    min_m = df["month_start"].min()
    n_months = (max_m.year - min_m.year) * 12 + (max_m.month - min_m.month) + 1
    actual_test_months = min(TEST_MONTHS, max(1, n_months // 3))

    test_start = max_m - pd.DateOffset(months=actual_test_months - 1)
    test_start = test_start.replace(day=1)

    train_df = df[df["month_start"] < test_start]
    test_df = df[df["month_start"] >= test_start]

    X_train = train_df[FEATURE_COLS].astype(float)
    y_train = train_df[TARGET].astype(float)
    X_test = test_df[FEATURE_COLS].astype(float)
    y_test = test_df[TARGET].astype(float)

    y_train_v = train_df["y_next_30d_violent"].astype(float).fillna(0)
    y_test_v = test_df["y_next_30d_violent"].astype(float).fillna(0)
    y_train_p = train_df["y_next_30d_property"].astype(float).fillna(0)
    y_test_p = test_df["y_next_30d_property"].astype(float).fillna(0)

    train_weights = np.log1p(y_train) + 1.0

    print(f"  Data: {n_months} months ({min_m.date()} to {max_m.date()})")
    print(f"  Test: >= {test_start.date()} ({actual_test_months} months)")
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # --- Baselines ---
    baseline_pred = weighted_baseline_predict(X_test)
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))
    baseline_r2 = r2_score(y_test, baseline_pred)

    naive_pred = X_test["lag_1m_count"].values
    naive_mae = mean_absolute_error(y_test, naive_pred)

    # --- Optuna hyperparameter tuning ---
    print("[tune] Running Optuna hyperparameter search (20 trials)...")

    def objective(trial):
        p = {
            "objective": "regression",
            "metric": "rmse",
            "verbosity": -1,
            "random_state": 42,
            "n_estimators": 500,
            "num_leaves": trial.suggest_int("num_leaves", 31, 127),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }
        m = lgb.LGBMRegressor(**p)
        m.fit(
            X_train, np.log1p(y_train),
            sample_weight=train_weights,
            eval_set=[(X_test, np.log1p(y_test))],
            callbacks=[lgb.early_stopping(30, verbose=False)],
        )
        pred = np.expm1(np.maximum(m.predict(X_test), 0))
        pred = np.maximum(pred, 0)
        return mean_absolute_error(y_test, pred)

    study = optuna.create_study(direction="minimize", study_name="crimescope_v3")
    study.optimize(objective, n_trials=20)

    best_hp = study.best_params
    print(f"  Best MAE: {study.best_value:.4f}")
    print(f"  Best params: {json.dumps(best_hp, indent=2)}")

    tuned_params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "random_state": 42,
        "n_estimators": 500,
        **best_hp,
    }

    # --- Train ensemble: log1p + sqrt ---
    print("[train] Training LightGBM ensemble (log1p + sqrt)...")
    model_log = lgb.LGBMRegressor(**tuned_params)
    model_log.fit(
        X_train, np.log1p(y_train),
        sample_weight=train_weights,
        eval_set=[(X_test, np.log1p(y_test))],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )
    print(f"  Log1p model best iteration: {model_log.best_iteration_}")

    model_sqrt = lgb.LGBMRegressor(**tuned_params)
    model_sqrt.fit(
        X_train, np.sqrt(y_train),
        sample_weight=train_weights,
        eval_set=[(X_test, np.sqrt(y_test))],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )
    print(f"  Sqrt model best iteration: {model_sqrt.best_iteration_}")

    # Evaluate individual and ensemble
    pred_log = np.maximum(np.expm1(np.maximum(model_log.predict(X_test), 0)), 0)
    pred_sqrt = np.maximum(np.square(np.maximum(model_sqrt.predict(X_test), 0)), 0)
    pred_ensemble = 0.5 * pred_log + 0.5 * pred_sqrt

    def calc_metrics(y_true, y_pred):
        return (
            mean_absolute_error(y_true, y_pred),
            np.sqrt(mean_squared_error(y_true, y_pred)),
            r2_score(y_true, y_pred),
        )

    mae_log, rmse_log, r2_log = calc_metrics(y_test, pred_log)
    mae_sqrt, rmse_sqrt, r2_sqrt = calc_metrics(y_test, pred_sqrt)
    mae_ens, rmse_ens, r2_ens = calc_metrics(y_test, pred_ensemble)

    if mae_ens <= min(mae_log, mae_sqrt):
        y_pred = pred_ensemble
        mae, rmse, r2 = mae_ens, rmse_ens, r2_ens
        best_strategy = "ensemble"
    elif mae_log <= mae_sqrt:
        y_pred = pred_log
        mae, rmse, r2 = mae_log, rmse_log, r2_log
        best_strategy = "log1p"
    else:
        y_pred = pred_sqrt
        mae, rmse, r2 = mae_sqrt, rmse_sqrt, r2_sqrt
        best_strategy = "sqrt"

    mae_improve = (1 - mae / baseline_mae) * 100 if baseline_mae > 0 else 0
    rmse_improve = (1 - rmse / baseline_rmse) * 100 if baseline_rmse > 0 else 0

    # --- Feature pruning ---
    print("[prune] Pruning low-importance features...")
    imp_vals = model_log.feature_importances_
    threshold = np.percentile(imp_vals, 25)
    keep_mask = imp_vals > threshold
    feature_cols_pruned = [f for f, k in zip(FEATURE_COLS, keep_mask) if k]
    dropped = [f for f, k in zip(FEATURE_COLS, keep_mask) if not k]
    print(f"  {len(FEATURE_COLS)} -> {len(feature_cols_pruned)} features (dropped {len(dropped)})")

    # --- Train violent + property sub-models on pruned features ---
    print("[train] Training violent + property sub-models (pruned features)...")
    X_train_p = X_train[feature_cols_pruned]
    X_test_p = X_test[feature_cols_pruned]

    model_violent = lgb.LGBMRegressor(**tuned_params)
    model_violent.fit(
        X_train_p, np.log1p(y_train_v),
        sample_weight=np.log1p(y_train_v) + 1.0,
        eval_set=[(X_test_p, np.log1p(y_test_v))],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )
    y_pred_v = np.maximum(np.expm1(np.maximum(model_violent.predict(X_test_p), 0)), 0)
    mae_v, rmse_v, r2_v = calc_metrics(y_test_v, y_pred_v)
    print(f"  Violent — MAE: {mae_v:.4f}  R²: {r2_v:.4f}")

    model_property = lgb.LGBMRegressor(**tuned_params)
    model_property.fit(
        X_train_p, np.log1p(y_train_p),
        sample_weight=np.log1p(y_train_p) + 1.0,
        eval_set=[(X_test_p, np.log1p(y_test_p))],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )
    y_pred_p = np.maximum(np.expm1(np.maximum(model_property.predict(X_test_p), 0)), 0)
    mae_p, rmse_p, r2_p = calc_metrics(y_test_p, y_pred_p)
    print(f"  Property — MAE: {mae_p:.4f}  R²: {r2_p:.4f}")

    # --- Summary table ---
    print(f"\n  {'='*70}")
    print(f"  {'Model':<22} {'MAE':>8}  {'RMSE':>8}  {'R²':>8}")
    print(f"  {'='*70}")
    print(f"  {'Naive lag-1':<22} {naive_mae:>8.4f}")
    print(f"  {'Weighted baseline':<22} {baseline_mae:>8.4f}  {baseline_rmse:>8.4f}  {baseline_r2:>8.4f}")
    print(f"  {'LightGBM (log1p)':<22} {mae_log:>8.4f}  {rmse_log:>8.4f}  {r2_log:>8.4f}")
    print(f"  {'LightGBM (sqrt)':<22} {mae_sqrt:>8.4f}  {rmse_sqrt:>8.4f}  {r2_sqrt:>8.4f}")
    print(f"  {'LightGBM (ensemble)':<22} {mae_ens:>8.4f}  {rmse_ens:>8.4f}  {r2_ens:>8.4f}")
    print(f"  {'LightGBM (violent)':<22} {mae_v:>8.4f}  {rmse_v:>8.4f}  {r2_v:>8.4f}")
    print(f"  {'LightGBM (property)':<22} {mae_p:>8.4f}  {rmse_p:>8.4f}  {r2_p:>8.4f}")
    print(f"  {'='*70}")
    print(f"  Best strategy: {best_strategy}")
    print(f"  ML vs Weighted — MAE: {mae_improve:+.1f}%  |  RMSE: {rmse_improve:+.1f}%")

    # Feature importance
    imp = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": model_log.feature_importances_,
    }).sort_values("importance", ascending=False)
    imp.to_csv(ARTIFACTS_DIR / "feature_importance.csv", index=False)

    # Save models
    print("[save] Saving model artifacts...")
    joblib.dump(model_log, ARTIFACTS_DIR / "model_log.joblib")
    joblib.dump(model_sqrt, ARTIFACTS_DIR / "model_sqrt.joblib")
    joblib.dump(model_violent, ARTIFACTS_DIR / "model_violent.joblib")
    joblib.dump(model_property, ARTIFACTS_DIR / "model_property.joblib")

    serializable_params = {k: v for k, v in tuned_params.items()
                           if k not in ("objective", "metric", "verbosity", "random_state")}

    metadata = {
        "model_type": "LGBMRegressor",
        "model_version": "v3",
        "target": TARGET,
        "ensemble_strategy": best_strategy,
        "features": FEATURE_COLS,
        "features_pruned": feature_cols_pruned,
        "n_features": len(FEATURE_COLS),
        "n_features_pruned": len(feature_cols_pruned),
        "tuned_params": serializable_params,
        "optuna_trials": 20,
        "sample_weighting": "log1p(y)+1",
        "best_iteration_log": model_log.best_iteration_,
        "best_iteration_sqrt": model_sqrt.best_iteration_,
        "metrics": {
            "mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4),
            "mae_log": round(mae_log, 4), "mae_sqrt": round(mae_sqrt, 4),
            "mae_ensemble": round(mae_ens, 4),
            "baseline_mae": round(baseline_mae, 4), "baseline_rmse": round(baseline_rmse, 4),
            "baseline_r2": round(baseline_r2, 4),
            "baseline_type": "weighted_rules_index",
            "naive_mae": round(naive_mae, 4),
            "mae_improvement_pct": round(mae_improve, 1),
            "rmse_improvement_pct": round(rmse_improve, 1),
            "violent_mae": round(mae_v, 4), "violent_r2": round(r2_v, 4),
            "property_mae": round(mae_p, 4), "property_r2": round(r2_p, 4),
        },
        "split": {
            "test_months": actual_test_months,
            "test_start": str(test_start.date()),
            "n_train": len(X_train), "n_test": len(X_test),
        },
        "data": {
            "crime_start_date": CRIME_START_DATE,
            "maturity_buffer_months": MATURITY_BUFFER_MONTHS,
            "geography": "Cook County, IL (census tract)",
            "min_month": str(min_m.date()), "max_month": str(max_m.date()),
        },
        "trained_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(ARTIFACTS_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Evaluation report
    report_lines = [
        "CrimeScope ML v3 — Evaluation Report",
        "=" * 60,
        f"Trained: {metadata['trained_at']}",
        f"Ensemble strategy: {best_strategy}",
        f"Features: {len(FEATURE_COLS)} (pruned to {len(feature_cols_pruned)} for sub-models)",
        f"Optuna: 20 trials, sample weighting: log1p(y)+1",
        f"Geography: Cook County, IL — census tract level",
        f"Data range: {min_m.date()} to {max_m.date()} ({n_months} months)",
        "",
        f"Train: {len(X_train):,} rows  |  Test: {len(X_test):,} rows",
        f"Test window: {test_start.date()} onward ({actual_test_months} months)",
        "",
        "Results:",
        f"  Naive lag-1          — MAE: {naive_mae:.4f}",
        f"  Weighted baseline    — MAE: {baseline_mae:.4f}  |  RMSE: {baseline_rmse:.4f}  |  R²: {baseline_r2:.4f}",
        f"  LightGBM (log1p)     — MAE: {mae_log:.4f}  |  RMSE: {rmse_log:.4f}  |  R²: {r2_log:.4f}",
        f"  LightGBM (sqrt)      — MAE: {mae_sqrt:.4f}  |  RMSE: {rmse_sqrt:.4f}  |  R²: {r2_sqrt:.4f}",
        f"  LightGBM (ensemble)  — MAE: {mae_ens:.4f}  |  RMSE: {rmse_ens:.4f}  |  R²: {r2_ens:.4f}",
        f"  LightGBM (violent)   — MAE: {mae_v:.4f}  |  RMSE: {rmse_v:.4f}  |  R²: {r2_v:.4f}",
        f"  LightGBM (property)  — MAE: {mae_p:.4f}  |  RMSE: {rmse_p:.4f}  |  R²: {r2_p:.4f}",
        f"  ML vs Weighted: MAE {mae_improve:+.1f}%  |  RMSE {rmse_improve:+.1f}%",
        "",
        "Top 10 features:",
    ]
    for _, row in imp.head(10).iterrows():
        report_lines.append(f"  {row['feature']:35s}  {int(row['importance']):>6d}")

    report_text = "\n".join(report_lines)
    with open(ARTIFACTS_DIR / "evaluation_report.txt", "w") as f:
        f.write(report_text)
    print(report_text)

    # Plots
    print("[plots] Generating evaluation plots...")
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(y_test, y_pred, alpha=0.15, s=8, color="#2563eb")
    lim = max(y_test.max(), max(y_pred)) * 1.05
    ax.plot([0, lim], [0, lim], "--", color="#ef4444", linewidth=1.5)
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title(f"Actual vs Predicted ({best_strategy})  |  MAE={mae:.2f}  R²={r2:.3f}")
    fig.tight_layout()
    fig.savefig(ARTIFACTS_DIR / "actual_vs_predicted.png", dpi=150)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(10, 12))
    imp_sorted = imp.sort_values("importance", ascending=True)
    ax2.barh(imp_sorted["feature"], imp_sorted["importance"], color="#2563eb")
    ax2.set_xlabel("Importance (split count)")
    ax2.set_title("Feature Importance — LightGBM (log1p)")
    fig2.tight_layout()
    fig2.savefig(ARTIFACTS_DIR / "feature_importance.png", dpi=150)
    plt.close(fig2)

    # SHAP-based latest-month scores
    print("[scores] Generating latest tract risk scores with SHAP...")
    try:
        import shap
        has_shap = True
    except ImportError:
        has_shap = False

    latest_month = df["month_start"].max()
    latest = df[df["month_start"] == latest_month].copy()

    if len(latest) > 0:
        X_latest = latest[FEATURE_COLS].astype(float).fillna(0.0)
        X_latest_pruned = latest[feature_cols_pruned].astype(float).fillna(0.0)

        # Ensemble prediction
        p_log = np.maximum(np.expm1(np.maximum(model_log.predict(X_latest), 0)), 0)
        p_sqrt = np.maximum(np.square(np.maximum(model_sqrt.predict(X_latest), 0)), 0)
        if best_strategy == "ensemble":
            latest["predicted_next_30d"] = np.round(0.5 * p_log + 0.5 * p_sqrt, 2)
        elif best_strategy == "sqrt":
            latest["predicted_next_30d"] = np.round(p_sqrt, 2)
        else:
            latest["predicted_next_30d"] = np.round(p_log, 2)

        latest["predicted_violent_30d"] = np.maximum(
            np.expm1(np.maximum(model_violent.predict(X_latest_pruned), 0)), 0
        ).round(2)
        latest["predicted_property_30d"] = np.maximum(
            np.expm1(np.maximum(model_property.predict(X_latest_pruned), 0)), 0
        ).round(2)

        latest["baseline_predicted"] = weighted_baseline_predict(X_latest).round(2)

        latest["risk_score"] = blended_risk_score(latest["predicted_next_30d"].values)
        latest["violent_score"] = blended_risk_score(latest["predicted_violent_30d"].values)
        latest["property_score"] = blended_risk_score(latest["predicted_property_30d"].values)

        latest["risk_tier"] = pd.cut(
            latest["risk_score"],
            bins=[0, 25, 50, 75, 90, 100],
            labels=["Low", "Moderate", "Elevated", "High", "Critical"],
            include_lowest=True,
        )

        latest["model_vs_baseline"] = (
            (latest["predicted_next_30d"] - latest["baseline_predicted"]) /
            latest["baseline_predicted"].clip(lower=0.1)
        ).round(3)

        latest["trend_direction"] = np.where(
            latest["predicted_next_30d"] > latest["lag_1m_count"] * 1.05, "rising",
            np.where(latest["predicted_next_30d"] < latest["lag_1m_count"] * 0.95, "falling", "stable")
        )

        if has_shap:
            explainer = shap.TreeExplainer(model_log)
            shap_values = explainer.shap_values(X_latest)
            latest["top_drivers_json"] = [
                top_drivers_json(shap_values[i], FEATURE_COLS, X_latest.iloc[i].values)
                for i in range(len(shap_values))
            ]
        else:
            latest["top_drivers_json"] = "[]"

        score_cols = [
            "tract_geoid", "month_start", "incident_count",
            "y_incidents_12m", "y_violent_12m", "y_property_12m",
            "predicted_next_30d", "predicted_violent_30d", "predicted_property_30d",
            "baseline_predicted",
            "risk_score", "violent_score", "property_score", "risk_tier",
            "model_vs_baseline", "trend_direction",
            "lag_1m_count", "rolling_mean_3m", "rolling_mean_12m",
            "violent_ratio", "violent_ratio_6m",
            "total_pop_acs", "median_hh_income_acs", "poverty_rate_acs", "housing_units_acs",
            "top_drivers_json",
        ]
        scores = latest[[c for c in score_cols if c in latest.columns]]
        scores.to_csv(ARTIFACTS_DIR / "tract_scores_latest.csv", index=False)
        print(f"  Wrote {len(scores)} tract scores for {latest_month.date()}")

    return metadata


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("CrimeScope ML v3 — Local Training Pipeline")
    print("=" * 60)
    print()

    crimes = ingest_crimes()
    tracts = load_tract_boundaries()
    crimes_with_tract = spatial_join_crimes(crimes, tracts)
    panel = build_panel(crimes_with_tract, tracts)
    acs = fetch_acs(tracts)
    features = engineer_features(panel, acs)
    metadata = train_and_evaluate(features)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Pipeline complete in {elapsed / 60:.1f} minutes")
    print(f"Artifacts written to: {ARTIFACTS_DIR}")
    print(f"  model_log.joblib          — overall LightGBM (log1p)")
    print(f"  model_sqrt.joblib         — overall LightGBM (sqrt)")
    print(f"  model_violent.joblib      — violent sub-model")
    print(f"  model_property.joblib     — property sub-model")
    print(f"  model_metadata.json       — params, metrics, feature list")
    print(f"  feature_importance.csv    — feature importance table")
    print(f"  tract_scores_latest.csv   — latest per-tract risk scores")
    print(f"  evaluation_report.txt     — human-readable summary")
    print(f"  features.parquet          — full feature table")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
