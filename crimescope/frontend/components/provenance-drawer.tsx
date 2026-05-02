"use client";

import { useAppStore } from "../lib/store";
import { getCity } from "../lib/cities";

type DataSource = {
  name: string;
  type: string;
  confidence: "high" | "medium" | "low";
  coverage: string;
  records: string;
};

const CHICAGO_DATA_SOURCES: DataSource[] = [
  { name: "Chicago Open Crime Data", type: "Historical", confidence: "high", coverage: "2020–2025", records: "~7.9M" },
  { name: "Census ACS 5-Year", type: "Contextual", confidence: "high", coverage: "2019–2023", records: "Census tracts" },
  { name: "TIGER/Line Tract Geometry", type: "Geospatial", confidence: "high", coverage: "2024", records: "1,332 tracts" },
  { name: "Official Bulletins", type: "Live", confidence: "high", coverage: "Rolling 7d", records: "Variable" },
  { name: "Local News RSS", type: "Live", confidence: "medium", coverage: "Rolling 24h", records: "Variable" },
  { name: "Public Alert Feeds", type: "Live", confidence: "medium", coverage: "Rolling 48h", records: "Variable" },
];

const UK_DATA_SOURCES: DataSource[] = [
  { name: "data.police.uk Street-Level Crime", type: "Historical", confidence: "high", coverage: "60 months, 43 E&W forces", records: "~30M incidents" },
  { name: "ONS Census 2021 (Nomis)", type: "Contextual", confidence: "high", coverage: "England & Wales 2021", records: "Per-LSOA pop / age" },
  { name: "MHCLG English IMD 2019", type: "Contextual", confidence: "high", coverage: "England LSOAs", records: "7 domain scores" },
  { name: "StatsWales WIMD 2019", type: "Contextual", confidence: "high", coverage: "Wales LSOAs", records: "Domain ranks" },
  { name: "ONS LSOA / MSOA 2021 Boundaries", type: "Geospatial", confidence: "high", coverage: "England & Wales 2021", records: "~33k LSOA / 7,264 MSOA" },
  { name: "ONS LSOA→MSOA→LAD Lookup", type: "Geospatial", confidence: "high", coverage: "Dec 2021", records: "Official ONS" },
];

const CHICAGO_LIMITATIONS = [
  "Scores are modeled estimates based on historical patterns and do not represent ground truth.",
  "Live signals are governed but may contain unverified or partially corroborated information.",
  "Underreporting is a known issue in crime data. Areas with low incident counts may reflect reporting gaps rather than low risk.",
  "Model accuracy varies by tract density and data availability. Sparse tracts may have lower confidence.",
  "Census data has a built-in lag. ACS 5-year estimates reflect conditions from the survey period, not the present.",
  "Seasonal and temporal patterns are accounted for but cannot predict unprecedented events.",
  "The baseline vs ML comparison highlights model divergence but does not indicate which is more accurate.",
];

const UK_LIMITATIONS = [
  "Scores are model estimates from a LightGBM ensemble trained on data.police.uk; they predict next-30-day reported incident counts, not ground truth victimization.",
  "data.police.uk locations are anonymized to LSOA snap points, so within-LSOA spatial precision is intentionally limited.",
  "Underreporting is a known issue — areas with low incident counts may reflect reporting gaps rather than low risk.",
  "English IMD (2019) and Welsh IMD (2019) use different methodologies; we harmonize via national-rank percentiles, but cross-border comparisons should be read with care.",
  "Boundaries are ONS LSOA / MSOA 2021. The ~3% of LSOAs that changed between 2011 and 2021 inherit IMD 2019 (2011-LSOA basis) via best-match.",
  "Last 2 months are excluded from training as a maturity buffer; the demo scoring window is whatever month notebook 05 wrote last.",
];

const CHICAGO_METHODOLOGY = [
  { step: "01", title: "Data Ingestion", detail: "Historical crime, ACS demographics, and tract geometries loaded and validated." },
  { step: "02", title: "Feature Engineering", detail: "Tract-level features computed: crime density, temporal trends, demographic context, spatial lags." },
  { step: "03", title: "Baseline Scoring", detail: "Weighted index model using rules-based crime type aggregation and temporal decay." },
  { step: "04", title: "ML Scoring", detail: "LightGBM model trained on tract features with SHAP-based driver extraction." },
  { step: "05", title: "Calibration", detail: "Score normalization (0–100), tier assignment, and confidence/completeness estimation." },
  { step: "06", title: "Live Signal Integration", detail: "Governed live events resolved to tracts with source confidence tagging." },
];

const UK_METHODOLOGY = [
  { step: "01", title: "Crime Ingest", detail: "60 months of data.police.uk monthly archives (~30M rows) staged in a UC Volume and landed as a Delta table." },
  { step: "02", title: "Geographic Join", detail: "Aggregated to LSOA × month with violent / property / other split; rolled up to MSOA via the official ONS LSOA→MSOA lookup." },
  { step: "03", title: "Demographic Merge", detail: "ONS Census 2021 population + English IMD 2019 + Welsh WIMD 2019 (harmonized) joined per LSOA; population-weighted to MSOA." },
  { step: "04", title: "Feature Engineering", detail: "~50 features per area×month: lag/rolling/yoy crime stats, violent-property splits, calendar, IMD domains, MSOA & LAD context." },
  { step: "05", title: "Train + Tune (Databricks)", detail: "Optuna-tuned LightGBM ensemble (log1p + sqrt) trained at LSOA + MSOA, plus violent / property sub-models. MLflow tracking." },
  { step: "06", title: "Score + Calibrate", detail: "Champion model from UC Registry scores all areas for the latest mature month. Blended 0–100 score = 0.7 × percentile + 0.3 × log-normalized." },
  { step: "07", title: "SHAP Drivers", detail: "TreeExplainer top-5 drivers per area surfaced verbatim in the per-region drill-down." },
];

const CHICAGO_EVAL = [
  { label: "ML MODEL", value: "LightGBM" },
  { label: "BASELINE", value: "Weighted Index" },
  { label: "EVAL METRIC", value: "MAE + SHAP" },
  { label: "COVERAGE", value: "Cook County" },
  { label: "TRACTS", value: "1,332" },
  { label: "FRESHNESS", value: "< 2 hours" },
];

const UK_EVAL = [
  { label: "ML MODEL", value: "LightGBM ensemble" },
  { label: "BASELINE", value: "Weighted Index" },
  { label: "EVAL METRIC", value: "MAE + SHAP" },
  { label: "COVERAGE", value: "England & Wales" },
  { label: "AREAS", value: "~33k LSOA / 7,264 MSOA" },
  { label: "FRESHNESS", value: "Monthly retrain" },
];

export default function ProvenanceDrawer() {
  const provenanceOpen = useAppStore((s) => s.provenanceOpen);
  const setProvenanceOpen = useAppStore((s) => s.setProvenanceOpen);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);

  if (!provenanceOpen) return null;

  const isUK = cityCfg.country === "UK";
  const sources = isUK ? UK_DATA_SOURCES : CHICAGO_DATA_SOURCES;
  const limitations = isUK ? UK_LIMITATIONS : CHICAGO_LIMITATIONS;
  const methodology = isUK ? UK_METHODOLOGY : CHICAGO_METHODOLOGY;
  const evalGrid = isUK ? UK_EVAL : CHICAGO_EVAL;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={() => setProvenanceOpen(false)}
    >
      <div
        className="flex flex-col h-full overflow-y-auto"
        style={{
          width: 460,
          background: "var(--cs-bg)",
          borderLeft: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 shrink-0"
          style={{ height: 36, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)" }}
        >
          <span className="text-[11px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>
            PROVENANCE & EVIDENCE · {cityCfg.shortLabel}
          </span>
          <button
            onClick={() => setProvenanceOpen(false)}
            className="text-[10px] font-bold px-2 py-0.5"
            style={{ color: "var(--cs-gray1)", background: "var(--cs-panel2)", border: "1px solid var(--cs-border)" }}
          >
            CLOSE
          </button>
        </div>

        {/* Data Sources */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--cs-border)" }}>
          <div className="text-[9px] font-bold tracking-[1.5px] uppercase mb-2" style={{ color: "var(--cs-accent)" }}>
            DATA SOURCES
          </div>
          <div className="space-y-2">
            {sources.map((s) => (
              <div key={s.name} className="flex items-start gap-2">
                <span
                  className="w-2 h-2 rounded-full shrink-0 mt-1"
                  style={{
                    background:
                      s.confidence === "high"
                        ? "var(--cs-green)"
                        : s.confidence === "medium"
                        ? "var(--cs-amber)"
                        : "var(--cs-gray2)",
                  }}
                />
                <div className="flex-1">
                  <div className="text-[10px] font-medium" style={{ color: "var(--cs-text)" }}>{s.name}</div>
                  <div className="flex gap-3 mt-0.5">
                    <span className="text-[8px] uppercase" style={{ color: "var(--cs-gray2)" }}>{s.type}</span>
                    <span className="text-[8px]" style={{ color: "var(--cs-gray2)" }}>{s.coverage}</span>
                    <span className="text-[8px]" style={{ color: "var(--cs-gray2)" }}>{s.records}</span>
                    <span
                      className="text-[8px] uppercase font-bold"
                      style={{
                        color:
                          s.confidence === "high"
                            ? "var(--cs-green)"
                            : s.confidence === "medium"
                            ? "var(--cs-amber)"
                            : "var(--cs-gray2)",
                      }}
                    >
                      {s.confidence}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Methodology */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--cs-border)" }}>
          <div className="text-[9px] font-bold tracking-[1.5px] uppercase mb-2" style={{ color: "var(--cs-accent)" }}>
            SCORING METHODOLOGY
          </div>
          <div className="space-y-2">
            {methodology.map((m) => (
              <div key={m.step} className="flex gap-2">
                <span className="text-[9px] font-bold shrink-0" style={{ color: "var(--cs-accent)" }}>{m.step}</span>
                <div>
                  <div className="text-[10px] font-medium" style={{ color: "var(--cs-text)" }}>{m.title}</div>
                  <div className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{m.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Limitations */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--cs-border)" }}>
          <div className="text-[9px] font-bold tracking-[1.5px] uppercase mb-2" style={{ color: "var(--cs-amber)" }}>
            LIMITATIONS & UNCERTAINTY
          </div>
          <ul className="space-y-1.5">
            {limitations.map((l, i) => (
              <li key={i} className="text-[9px] flex gap-1.5" style={{ color: "var(--cs-gray1)" }}>
                <span className="shrink-0" style={{ color: "var(--cs-amber)" }}>•</span>
                {l}
              </li>
            ))}
          </ul>
        </div>

        {/* Evaluation summary */}
        <div className="px-4 py-3">
          <div className="text-[9px] font-bold tracking-[1.5px] uppercase mb-2" style={{ color: "var(--cs-accent)" }}>
            MODEL EVALUATION
          </div>
          <div className="grid grid-cols-2 gap-2">
            {evalGrid.map((m) => (
              <div key={m.label} className="py-1.5 px-2" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                <div className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>{m.label}</div>
                <div className="text-[10px] font-bold" style={{ color: "var(--cs-text)" }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
