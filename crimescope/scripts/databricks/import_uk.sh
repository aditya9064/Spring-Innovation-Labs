#!/usr/bin/env bash
# CrimeScope UK & Wales — one-shot Databricks import + deploy + run.
#
# Pushes the notebooks to /Workspace/Shared/Team_varanasi/ML, deploys the DABs
# bundle (Workflow + Model Serving endpoint), kicks off the pipeline, and
# pulls the JSON exports back into crimescope/backend/app/data/.
#
# Prereqs:
#   - databricks CLI v0.250+ installed
#   - profile "team_varanasi" valid (run `databricks auth login --host https://dbc-42cdc781-8591.cloud.databricks.com --profile team_varanasi`)
#
# Usage:
#   ./crimescope/scripts/databricks/import_uk.sh         # full pipeline (push + deploy + run + pull)
#   ./crimescope/scripts/databricks/import_uk.sh push    # push notebooks only
#   ./crimescope/scripts/databricks/import_uk.sh deploy  # deploy bundle only
#   ./crimescope/scripts/databricks/import_uk.sh run     # trigger workflow run only
#   ./crimescope/scripts/databricks/import_uk.sh pull    # pull JSON exports back

set -euo pipefail

PROFILE="${DATABRICKS_PROFILE:-team_varanasi}"
TARGET="${DATABRICKS_TARGET:-prod}"
WORKSPACE_ML_PATH="/Workspace/Shared/Team_varanasi/ML"
EXPORT_VOLUME_PATH="dbfs:/Volumes/varanasi/default/ml_data_uk/exports/latest"

# Resolve repo root from this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NOTEBOOKS_LOCAL="${REPO_ROOT}/notebooks/ML"
BUNDLE_DIR="${REPO_ROOT}/databricks"
BACKEND_DATA_DIR="${REPO_ROOT}/backend/app/data"

step() { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }
ok()   { printf "    \033[1;32m✓\033[0m %s\n" "$1"; }
warn() { printf "    \033[1;33m!\033[0m %s\n" "$1"; }

require_auth() {
  if ! databricks --profile "${PROFILE}" current-user me >/dev/null 2>&1; then
    cat <<EOF >&2
Cannot reach Databricks with profile "${PROFILE}".

Re-authenticate:

    databricks auth login \\
      --host https://dbc-42cdc781-8591.cloud.databricks.com \\
      --profile ${PROFILE}

EOF
    exit 1
  fi
}

push_notebooks() {
  step "Importing notebooks → ${WORKSPACE_ML_PATH}"
  databricks workspace import-dir \
    "${NOTEBOOKS_LOCAL}" \
    "${WORKSPACE_ML_PATH}" \
    --overwrite \
    --profile "${PROFILE}"
  ok "Notebooks imported"
}

deploy_bundle() {
  step "Validating DABs bundle"
  ( cd "${BUNDLE_DIR}" && databricks bundle validate --target "${TARGET}" --profile "${PROFILE}" )
  ok "Bundle validates"

  step "Deploying DABs bundle (Workflow + Model Serving endpoint)"
  ( cd "${BUNDLE_DIR}" && databricks bundle deploy --target "${TARGET}" --profile "${PROFILE}" )
  ok "Bundle deployed"
}

run_pipeline() {
  step "Triggering crimescope_uk_pipeline"
  ( cd "${BUNDLE_DIR}" && databricks bundle run crimescope_uk_pipeline --target "${TARGET}" --profile "${PROFILE}" )
  ok "Pipeline run completed"
}

pull_exports() {
  step "Pulling JSON exports from UC Volume → ${BACKEND_DATA_DIR}"
  mkdir -p "${BACKEND_DATA_DIR}"
  databricks fs cp -r "${EXPORT_VOLUME_PATH}/" "${BACKEND_DATA_DIR}/" \
    --profile "${PROFILE}" --overwrite
  ok "Exports synced"
  ls -lh "${BACKEND_DATA_DIR}"/uk_*.json | sed 's/^/    /'
}

verify_outputs() {
  step "Verifying Databricks objects"
  databricks tables list varanasi default --profile "${PROFILE}" \
    | grep -E "^uk_(crime|lsoa|msoa|risk)" || warn "no UK tables matched yet"
  databricks serving-endpoints get crimescope-uk-risk --profile "${PROFILE}" \
    --output json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('    serving endpoint:', d.get('state', {}).get('ready', '?'))" \
    || warn "serving endpoint not READY (or not yet created)"
}

watch_pipeline() {
  step "Watching crimescope-uk-pipeline"
  local job_id
  job_id=$(databricks jobs list --profile "${PROFILE}" --output json \
    | python3 -c "import sys,json; jobs=json.load(sys.stdin); print(next(j['job_id'] for j in jobs if j['settings']['name']=='crimescope-uk-pipeline'))")

  local run_id
  run_id=$(databricks jobs list-runs --job-id "${job_id}" --profile "${PROFILE}" --output json \
    | python3 -c "
import sys,json
d=json.load(sys.stdin)
runs=d.get('runs',d) if isinstance(d,dict) else d
# Prefer a currently-running run; fall back to most recent
running = [r for r in runs if r['state']['life_cycle_state'] in ('RUNNING','PENDING')]
print((running[0] if running else runs[0])['run_id'])")

  echo "    Run ID: ${run_id}"
  while true; do
    local snapshot
    snapshot=$(databricks jobs get-run "${run_id}" --profile "${PROFILE}" --output json)
    local life
    life=$(echo "${snapshot}" | python3 -c "import sys,json; print(json.load(sys.stdin)['state']['life_cycle_state'])")
    local result
    result=$(echo "${snapshot}" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'].get('result_state','-'))")
    local elapsed
    elapsed=$(echo "${snapshot}" | python3 -c "import sys,json,time; r=json.load(sys.stdin); print(f\"{(time.time()*1000-r.get('start_time',0))/60000:.1f}\")")
    local tasks
    tasks=$(echo "${snapshot}" | python3 -c "import sys,json; r=json.load(sys.stdin); print(' | '.join(f\"{t['task_key']}={t['state']['life_cycle_state'][:3]}\" for t in r['tasks']))")
    printf "\r    [%5s min] state=%s result=%s   %s          " "${elapsed}" "${life}" "${result}" "${tasks}"
    case "${life}" in
      TERMINATED|SKIPPED|INTERNAL_ERROR) echo ""; break ;;
    esac
    sleep 30
  done
  echo ""
  if [[ "${result}" != "SUCCESS" ]]; then
    warn "run ended with result=${result}"
    return 1
  fi
  ok "Pipeline finished SUCCESS"
}

deploy_serving() {
  step "Promoting deferred serving endpoint"
  local pending="${BUNDLE_DIR}/resources/crimescope_uk_risk.serving_endpoint.yml.pending"
  local active="${BUNDLE_DIR}/resources/crimescope_uk_risk.serving_endpoint.yml"
  if [[ -f "${pending}" ]]; then
    mv "${pending}" "${active}"
    ok "moved serving endpoint yml into resources/"
  fi
  ( cd "${BUNDLE_DIR}" && databricks bundle deploy --target "${TARGET}" --profile "${PROFILE}" )
  ok "Serving endpoint deployed"
}

cmd="${1:-all}"
case "${cmd}" in
  push)         require_auth; push_notebooks ;;
  deploy)       require_auth; deploy_bundle ;;
  run)          require_auth; run_pipeline ;;
  watch)        require_auth; watch_pipeline ;;
  pull)         require_auth; pull_exports ;;
  verify)       require_auth; verify_outputs ;;
  serve)        require_auth; deploy_serving ;;
  all)
    require_auth
    push_notebooks
    deploy_bundle
    run_pipeline
    verify_outputs
    pull_exports
    deploy_serving
    ;;
  finish)
    # Use this once the active run completes: pulls exports + deploys serving endpoint
    require_auth
    pull_exports
    deploy_serving
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    echo "Usage: $0 [push|deploy|run|watch|pull|verify|serve|finish|all]" >&2
    exit 2
    ;;
esac
