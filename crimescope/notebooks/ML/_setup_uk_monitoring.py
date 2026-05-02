# Databricks notebook source — one-shot setup for Lakehouse Monitoring + endpoint init.
#
# Run once after the first end-to-end pipeline run, or when the schema of the
# scoring tables changes. Idempotent.
#
# Creates:
#   - Snapshot Lakehouse Monitor on varanasi.default.uk_lsoa_risk_scores
#     keyed by (tract_geoid, scored_at) so we can track drift in score
#     distribution and SHAP-driver mix run-over-run.
#   - Snapshot Lakehouse Monitor on varanasi.default.uk_msoa_risk_scores
#   - (Optional) refresh of the @champion alias for the serving endpoint.

# COMMAND ----------
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    MonitorInfo,
    MonitorSnapshot,
    MonitorMetric,
    MonitorMetricType,
)

w = WorkspaceClient()

CATALOG = "varanasi"
SCHEMA = "default"

LSOA_TABLE = f"{CATALOG}.{SCHEMA}.uk_lsoa_risk_scores"
MSOA_TABLE = f"{CATALOG}.{SCHEMA}.uk_msoa_risk_scores"

# COMMAND ----------
def ensure_monitor(table_full_name: str) -> None:
    try:
        existing = w.quality_monitors.get(table_name=table_full_name)
        print(f"  monitor exists for {table_full_name}: status={existing.status}")
    except Exception:
        print(f"  creating snapshot monitor for {table_full_name}…")
        w.quality_monitors.create(
            table_name=table_full_name,
            assets_dir=f"/Workspace/Shared/Team_varanasi/monitors/{table_full_name.split('.')[-1]}",
            output_schema_name=f"{CATALOG}.{SCHEMA}",
            snapshot=MonitorSnapshot(),
            slicing_exprs=["risk_tier"],
        )

ensure_monitor(LSOA_TABLE)
ensure_monitor(MSOA_TABLE)
print("Monitoring bootstrap complete.")

# COMMAND ----------
# Optional: refresh the serving endpoint to point at the latest @champion version.
import mlflow
mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()

mv = client.get_model_version_by_alias(
    f"{CATALOG}.{SCHEMA}.crimescope_uk_risk_model_lsoa", "champion"
)
print(f"Champion LSOA model version: {mv.version}")

from databricks.sdk.service.serving import (
    ServedEntityInput, EndpointCoreConfigInput,
    TrafficConfig, Route, AutoCaptureConfigInput,
)

endpoint_name = "crimescope-uk-risk"
config = EndpointCoreConfigInput(
    served_entities=[
        ServedEntityInput(
            entity_name=f"{CATALOG}.{SCHEMA}.crimescope_uk_risk_model_lsoa",
            entity_version=str(mv.version),
            workload_size="Small",
            scale_to_zero_enabled=True,
            name=f"crimescope_uk_risk_model_lsoa-{mv.version}",
        )
    ],
    traffic_config=TrafficConfig(
        routes=[Route(served_model_name=f"crimescope_uk_risk_model_lsoa-{mv.version}", traffic_percentage=100)]
    ),
    auto_capture_config=AutoCaptureConfigInput(
        catalog_name=CATALOG,
        schema_name=SCHEMA,
        table_name_prefix="crimescope_uk_inference",
        enabled=True,
    ),
)

try:
    w.serving_endpoints.update_config(name=endpoint_name, **config.as_dict())
    print(f"Updated endpoint {endpoint_name} -> v{mv.version}")
except Exception as e:
    print(f"  (endpoint update skipped: {e})")
