#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${AAC_API_BASE_URL:-http://127.0.0.1:18000}"
RUN_ID="${AAC_SMOKE_RUN_ID:-$(date +%s)}"
ADMIN_USERNAME="admin_${RUN_ID}"
ADMIN_PASSWORD="${AAC_SMOKE_ADMIN_PASSWORD:-Admin1234!}"
PROJECT_KEY="DEMO_${RUN_ID}"

TOKEN=""
PROJECT_ID=""
ACTIVE_PROFILE_ID=""
PLEAD_ID=""
QENG_ID=""
DEV_ID=""
SSR_ID=""
TC_ID=""
REL_ID=""

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

fail() {
  printf '\nFAIL: %s\n' "$*" >&2
  exit 1
}

json_get() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin)
path = sys.argv[1].split(".")
value = data
for part in path:
    if part.isdigit():
        value = value[int(part)]
    else:
        value = value[part]
print(value)
' "$1"
}

json_has_rule() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin)
rule_id = sys.argv[1]
issues = data.get("data") or []
raise SystemExit(0 if any(issue.get("rule_id") == rule_id for issue in issues) else 1)
' "$1"
}

json_trace_has_backward_relationship() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin).get("data") or {}
source_id = sys.argv[1]
target_id = sys.argv[2]
for item in data.get("backward") or []:
    if (
        item.get("relationship_type") == "verifies"
        and item.get("source_artefact_id") == source_id
        and item.get("target_artefact_id") == target_id
    ):
        raise SystemExit(0)
raise SystemExit(1)
' "$1" "$2"
}

api_get() {
  local path="$1"
  curl -fsS "${API_BASE_URL}${path}" \
    -H "Authorization: Bearer ${TOKEN}"
}

api_post() {
  local path="$1"
  local payload="$2"
  curl -fsS -X POST "${API_BASE_URL}${path}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${payload}"
}

api_post_status() {
  local path="$1"
  local payload="$2"
  local body_file="$3"
  curl -sS -o "${body_file}" -w "%{http_code}" -X POST "${API_BASE_URL}${path}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${payload}"
}

poll_job() {
  local job_id="$1"
  local expected_terminal="${2:-completed}"
  local attempts="${3:-60}"
  local response state
  for _ in $(seq 1 "${attempts}"); do
    response="$(api_get "/api/v1/jobs/${job_id}")"
    state="$(printf '%s' "${response}" | json_get data.state)"
    if [[ "${state}" == "${expected_terminal}" ]]; then
      printf '%s' "${response}"
      return 0
    fi
    if [[ "${state}" == "failed" || "${state}" == "cancelled" ]]; then
      if [[ "${expected_terminal}" == "${state}" ]]; then
        printf '%s' "${response}"
        return 0
      fi
      printf '%s\n' "${response}" | python3 -m json.tool >&2
      fail "job ${job_id} reached unexpected terminal state ${state}"
    fi
    sleep 1
  done
  response="$(api_get "/api/v1/jobs/${job_id}")"
  printf '%s\n' "${response}" | python3 -m json.tool >&2
  fail "job ${job_id} did not reach ${expected_terminal}"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_command curl
require_command python3
require_command docker

log "Checking API health at ${API_BASE_URL}"
curl -fsS "${API_BASE_URL}/api/v1/health" >/dev/null || fail "API health check failed"

log "Creating admin user ${ADMIN_USERNAME}"
docker compose exec -T api python -m aac_backend.cli create-admin \
  --username "${ADMIN_USERNAME}" \
  --display-name "Admin User ${RUN_ID}" \
  --email "${ADMIN_USERNAME}@example.com" \
  --password "${ADMIN_PASSWORD}" >/tmp/aac_smoke_admin.out
cat /tmp/aac_smoke_admin.out

log "Logging in"
LOGIN_RESPONSE="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
TOKEN="$(printf '%s' "${LOGIN_RESPONSE}" | json_get data.access_token)"
[[ -n "${TOKEN}" ]] || fail "empty token"

log "Creating ASIL D + ASPICE PAM 4.0 CL3 project"
PROJECT_RESPONSE="$(api_post "/api/v1/projects" "$(cat <<JSON
{
  "project_key": "${PROJECT_KEY}",
  "name": "Demo Safety Project ${RUN_ID}",
  "description": "End-to-end usability test",
  "active_profile_id": "ASIL_D_DEFAULT",
  "assurance_configuration": {
    "project_type": "software_system",
    "asil_level": "ASIL_D",
    "aspice_model": "ASPICE_PAM_4_0",
    "aspice_default_capability_level": 3,
    "aspice_scoped_processes": ["MAN.3", "SWE.1", "SWE.2", "SWE.3", "SWE.4", "SWE.5", "SWE.6", "SUP.1", "SUP.8", "SUP.9", "SUP.10", "VAL.1"],
    "aspice_process_overrides": {},
    "r155_applicable": false,
    "r156_applicable": false,
    "test_scope": ["unit", "integration", "software_qualification"],
    "visibility_policy": "relevant_first"
  }
}
JSON
)")"
PROJECT_ID="$(printf '%s' "${PROJECT_RESPONSE}" | json_get data.project_id)"
ACTIVE_PROFILE_ID="$(printf '%s' "${PROJECT_RESPONSE}" | json_get data.active_profile_id)"
[[ -n "${PROJECT_ID}" && -n "${ACTIVE_PROFILE_ID}" ]] || fail "project creation did not return IDs"
printf 'PROJECT_ID=%s\nACTIVE_PROFILE_ID=%s\n' "${PROJECT_ID}" "${ACTIVE_PROFILE_ID}"

log "Checking profiles and derived applicability"
api_get "/api/v1/projects/${PROJECT_ID}/config" | python3 -m json.tool >/tmp/aac_smoke_config.json
api_get "/api/v1/projects/${PROJECT_ID}/profiles" | python3 -m json.tool >/tmp/aac_smoke_profiles.json
PROFILE_EVAL="$(api_post "/api/v1/projects/${PROJECT_ID}/profiles/${ACTIVE_PROFILE_ID}/evaluate" "{}")"
printf '%s' "${PROFILE_EVAL}" | python3 -m json.tool >/tmp/aac_smoke_profile_eval.json
python3 - <<'PY' /tmp/aac_smoke_profiles.json /tmp/aac_smoke_profile_eval.json
import json
import sys

profiles = json.load(open(sys.argv[1], encoding="utf-8"))["data"]
evaluation = json.load(open(sys.argv[2], encoding="utf-8"))["data"]
assert any(profile["profile_id"] == "ASIL_D_DEFAULT" for profile in profiles)
config = evaluation["assurance_configuration"]
assert config["asil_level"] == "ASIL_D"
assert config["aspice_model"] == "ASPICE_PAM_4_0"
assert config["aspice_default_capability_level"] == 3
assert "SoftwareSafetyRequirement" in evaluation["mandatory_artefact_types"]
assert "AAC-RULE-RULE-005" in evaluation["enabled_rules"]
PY

log "Creating users and assigning project roles"
PLEAD_RESPONSE="$(api_post "/api/v1/users" "{\"username\":\"plead_${RUN_ID}\",\"display_name\":\"Paula Lead\",\"email\":\"plead_${RUN_ID}@example.com\",\"password\":\"Lead1234!\",\"roles\":[]}")"
QENG_RESPONSE="$(api_post "/api/v1/users" "{\"username\":\"qeng_${RUN_ID}\",\"display_name\":\"Quinn Eng\",\"email\":\"qeng_${RUN_ID}@example.com\",\"password\":\"Qeng1234!\",\"roles\":[]}")"
DEV_RESPONSE="$(api_post "/api/v1/users" "{\"username\":\"devuser_${RUN_ID}\",\"display_name\":\"Dev User\",\"email\":\"devuser_${RUN_ID}@example.com\",\"password\":\"Dev1234!\",\"roles\":[]}")"
PLEAD_ID="$(printf '%s' "${PLEAD_RESPONSE}" | json_get data.user_id)"
QENG_ID="$(printf '%s' "${QENG_RESPONSE}" | json_get data.user_id)"
DEV_ID="$(printf '%s' "${DEV_RESPONSE}" | json_get data.user_id)"
api_post "/api/v1/projects/${PROJECT_ID}/members" "{\"user_id\":\"${PLEAD_ID}\",\"role\":\"project_lead\"}" >/dev/null
api_post "/api/v1/projects/${PROJECT_ID}/members" "{\"user_id\":\"${QENG_ID}\",\"role\":\"quality_engineer\"}" >/dev/null
api_post "/api/v1/projects/${PROJECT_ID}/members" "{\"user_id\":\"${DEV_ID}\",\"role\":\"user\"}" >/dev/null
MEMBERS_RESPONSE="$(api_get "/api/v1/projects/${PROJECT_ID}/members")"
python3 - <<'PY' "${MEMBERS_RESPONSE}"
import json
import sys

roles = {member["role"] for member in json.loads(sys.argv[1])["data"]}
assert {"project_lead", "quality_engineer", "user"} <= roles
PY

log "Creating V-model artefacts"
SSR_RESPONSE="$(api_post "/api/v1/projects/${PROJECT_ID}/artefacts" "$(cat <<JSON
{
  "artefact_type": "SoftwareSafetyRequirement",
  "title": "SW shall detect sensor timeout within 10ms",
  "source": {
    "source_kind": "api",
    "source_tool": "smoke-test",
    "source_document": "demo-reqs",
    "source_object_id": "SSR-001"
  },
  "payload": {
    "statement": "The software shall detect a sensor timeout within 10 ms and set the safe state.",
    "asil_level": "ASIL_D",
    "safety_relevant": true,
    "verification_intent": {"methods": ["test"]}
  }
}
JSON
)")"
SSR_ID="$(printf '%s' "${SSR_RESPONSE}" | json_get data.artefact_id)"

TC_RESPONSE="$(api_post "/api/v1/projects/${PROJECT_ID}/artefacts" "$(cat <<JSON
{
  "artefact_type": "TestCase",
  "title": "Verify sensor timeout detection",
  "source": {
    "source_kind": "api",
    "source_tool": "smoke-test",
    "source_document": "demo-tests",
    "source_object_id": "TC-001"
  },
  "payload": {
    "test_specification": "TS-001",
    "expected_results": ["Safe state flag set within 10 ms of sensor signal loss"],
    "pass_fail_criteria": "Response time <= 10 ms measured on HiL bench",
    "expected_result": "Safe state flag set within 10 ms of sensor signal loss",
    "pass_criteria": "Response time <= 10 ms measured on HiL bench"
  }
}
JSON
)")"
TC_ID="$(printf '%s' "${TC_RESPONSE}" | json_get data.artefact_id)"
printf 'SSR_ID=%s\nTC_ID=%s\n' "${SSR_ID}" "${TC_ID}"

log "Creating verifies relationship"
REL_RESPONSE="$(api_post "/api/v1/projects/${PROJECT_ID}/relationships" "{\"relationship_type\":\"verifies\",\"source_artefact_id\":\"${TC_ID}\",\"target_artefact_id\":\"${SSR_ID}\",\"payload\":{}}")"
REL_ID="$(printf '%s' "${REL_RESPONSE}" | json_get data.relationship_id)"
[[ -n "${REL_ID}" ]] || fail "relationship was not created"

log "Running validation and checking ASIL D mandatory gaps"
VALIDATION_RESPONSE="$(api_post "/api/v1/projects/${PROJECT_ID}/validation/run" "{\"type\":\"project\",\"mode\":\"baseline\"}")"
VALIDATION_JOB_ID="$(printf '%s' "${VALIDATION_RESPONSE}" | json_get data.job.job_id)"
poll_job "${VALIDATION_JOB_ID}" completed >/tmp/aac_smoke_validation_job.json
ISSUES_RESPONSE="$(api_get "/api/v1/projects/${PROJECT_ID}/validation/issues")"
printf '%s' "${ISSUES_RESPONSE}" | json_has_rule "AAC-RULE-RULE-005" || fail "RULE-005 was not raised"

log "Checking traceability"
TRACE_RESPONSE="$(api_get "/api/v1/projects/${PROJECT_ID}/trace/${SSR_ID}")"
printf '%s' "${TRACE_RESPONSE}" | json_trace_has_backward_relationship "${TC_ID}" "${SSR_ID}" || fail "trace did not contain TestCase -> SSR verifies relationship"

log "Attempting baseline and expecting gate block"
BASELINE_BODY=/tmp/aac_smoke_baseline_response.json
BASELINE_STATUS="$(api_post_status "/api/v1/projects/${PROJECT_ID}/baselines" "{\"name\":\"v0.1-demo\",\"description\":\"First test baseline\"}" "${BASELINE_BODY}")"
if [[ "${BASELINE_STATUS}" == "409" ]]; then
  grep -q "baseline eligibility failed" "${BASELINE_BODY}" || fail "baseline returned 409 for unexpected reason"
elif [[ "${BASELINE_STATUS}" == "200" ]]; then
  BASELINE_JOB_ID="$(json_get data.job.job_id < "${BASELINE_BODY}")"
  poll_job "${BASELINE_JOB_ID}" failed >/tmp/aac_smoke_baseline_job.json
  grep -q "baseline eligibility failed" /tmp/aac_smoke_baseline_job.json || true
else
  cat "${BASELINE_BODY}" >&2
  fail "unexpected baseline HTTP status ${BASELINE_STATUS}"
fi

log "Checking validation status"
VALIDATION_STATUS="$(api_get "/api/v1/projects/${PROJECT_ID}/validation/status")"
python3 - <<'PY' "${VALIDATION_STATUS}"
import json
import sys

status = json.loads(sys.argv[1])["data"]
assert status["open_issue_count"] > 0
assert status["critical_open_issue_count"] > 0
PY

log "Smoke test passed"
cat <<EOF
PROJECT_ID=${PROJECT_ID}
ACTIVE_PROFILE_ID=${ACTIVE_PROFILE_ID}
SSR_ID=${SSR_ID}
TC_ID=${TC_ID}
REL_ID=${REL_ID}
EOF
