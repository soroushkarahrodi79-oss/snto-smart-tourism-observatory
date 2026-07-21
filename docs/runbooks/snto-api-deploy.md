# Runbook: deploy the `/api/v2` HTTP surface (`snto-api`)

Implements **ADR-012 Option C**: a second scale-to-zero Container App running
the *same image* as the dashboard, with a command override that starts uvicorn
instead of Streamlit. No new image, no Dockerfile change — `fastapi` and
`uvicorn[standard]` are already in the image, and the ASGI app is
`src.api.main:app` (verified: it mounts `/api/v2/*` and a `GET /health`).

> **Do not run this until a trigger from ADR-012 §Decision has fired** (a named
> external consumer, the #26 field-capture workflow, or a split frontend).
> Standing the API up with zero consumers is cost and attack surface for
> nothing. This runbook is the *how*, not a go-ahead.

## 🔴 The one non-negotiable

`SNTO_API_KEY` **must be set in the same `az containerapp create` command that
exposes the app** — never "create now, add the key later". Reads are open by
design (ADR-011); writes are gated *only* when `SNTO_API_KEY` is set
(`src/api/v2/deps.py::require_write_auth`). An externally-reachable API with no
key = an open public write surface into production Postgres. Creating with the
key set means writes are gated from the very first request.

## Preflight (gather real values — don't hardcode)

Run in Azure Cloud Shell (Bash), already signed in:

```bash
RG=rg-snto-observatory-app
SRC_APP=snto-observatory
API_APP=snto-api

# Reuse the dashboard's environment and its exact current image, so the API and
# the dashboard start from the same build.
ENV_ID=$(az containerapp show -g $RG -n $SRC_APP --query properties.environmentId -o tsv)
IMAGE=$(az containerapp show -g $RG -n $SRC_APP --query properties.template.containers[0].image -o tsv)
echo "ENV_ID=$ENV_ID"
echo "IMAGE=$IMAGE"

# Non-secret DB coordinates (same server the dashboard uses). Confirm against
# the snto-db resource if unsure.
DB_HOST=$(az containerapp show -g $RG -n $SRC_APP \
  --query "properties.template.containers[0].env[?name=='SNTO_DB_HOST'].value | [0]" -o tsv)
DB_NAME=$(az containerapp show -g $RG -n $SRC_APP \
  --query "properties.template.containers[0].env[?name=='SNTO_DB_NAME'].value | [0]" -o tsv)
DB_USER=$(az containerapp show -g $RG -n $SRC_APP \
  --query "properties.template.containers[0].env[?name=='SNTO_DB_USER'].value | [0]" -o tsv)
echo "DB_HOST=$DB_HOST  DB_NAME=$DB_NAME  DB_USER=$DB_USER"

# The DB password is a secret. Read it back from the source app (you have rights),
# or paste the known value.
DB_PASS=$(az containerapp secret show -g $RG -n $SRC_APP --secret-name <db-pass-secret-name> --query value -o tsv)
# If SNTO_DB_PASS is a plain env var rather than a secretref on the source app,
# instead: DB_PASS=$(az containerapp show ... env[?name=='SNTO_DB_PASS'].value | [0])
```

Generate a strong API key (32 bytes, URL-safe) and **save it in your password
manager now** — it is shown once:

```bash
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "SNTO_API_KEY (store this): $API_KEY"
```

## Create the app (key set atomically)

```bash
az containerapp create -g $RG -n $API_APP \
  --environment "$ENV_ID" \
  --image "$IMAGE" \
  --registry-server acrsnto1781009309.azurecr.io \
  --registry-username "$(az acr credential show -n acrsnto1781009309 --query username -o tsv)" \
  --registry-password "$(az acr credential show -n acrsnto1781009309 --query passwords[0].value -o tsv)" \
  --command "uvicorn" \
  --args "src.api.main:app" "--host" "0.0.0.0" "--port" "8000" \
  --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 1 \
  --secrets snto-db-pass="$DB_PASS" snto-api-key="$API_KEY" \
  --env-vars \
     SNTO_DB_HOST="$DB_HOST" \
     SNTO_DB_PORT=5432 \
     SNTO_DB_NAME="$DB_NAME" \
     SNTO_DB_USER="$DB_USER" \
     SNTO_DB_PASS=secretref:snto-db-pass \
     SNTO_API_KEY=secretref:snto-api-key
```

Notes:
- `USE_MOCK_DATA` is `true` in the image default, but the API path never reads
  it — persistence uses `SNTO_DB_*`. Leaving it as-is is fine.
- If your `az` version rejects the inline `--command/--args`, create from a
  minimal YAML instead (`az containerapp create --yaml api.yaml`) with the same
  `command`/`args`/`ingress`/`secrets`/`env` — the shape is identical.
- ACR pull here still uses the admin credentials (same as today's dashboard).
  Moving both apps to managed-identity pull is the separate
  [`keyvault-secrets.md`](keyvault-secrets.md) runbook.

## Smoke test (in this order)

```bash
FQDN=$(az containerapp show -g $RG -n $API_APP --query properties.configuration.ingress.fqdn -o tsv)

# 1. Health (open) → 200 {"status":"ok","version":"2.1.0.dev0"}
curl -s "https://$FQDN/health"; echo

# 2. A read (open by design) → 200 with JSON
curl -s -o /dev/null -w "read: %{http_code}\n" "https://$FQDN/api/v2/managed-assets"

# 3. A write WITHOUT the key → MUST be 401 (proves the gate is on)
curl -s -o /dev/null -w "unauth write: %{http_code}\n" \
  -X POST "https://$FQDN/api/v2/managed-assets" -H "Content-Type: application/json" -d '{}'

# 4. A write WITH the key → 4xx-validation or 2xx, NOT 401 (proves the key works).
#    (An empty body is expected to 422; the point is it got PAST auth.)
curl -s -o /dev/null -w "authed write: %{http_code}\n" \
  -X POST "https://$FQDN/api/v2/managed-assets" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d '{}'
```

If step 3 returns anything other than `401`, **the write surface is open** —
tear the app down (`az containerapp delete -g $RG -n $API_APP --yes`) and retry
with the key set.

## Wire the CD pipeline to roll BOTH apps

ADR-012 §Consequences: once `snto-api` exists, every release must roll it too or
its image drifts behind the dashboard. Add a second roll step to
[`.github/workflows/deploy-azure-container-apps.yml`](../../.github/workflows/deploy-azure-container-apps.yml),
right after the existing "Roll Container App to new image" step:

```yaml
      - name: Roll API app to new image
        run: |
          IMG="${{ secrets.ACR_LOGIN_SERVER }}/${IMAGE_REPO}:${DEPLOY_SHA::8}"
          az containerapp update -g "${RESOURCE_GROUP}" -n snto-api \
            --image "${IMG}" \
            --revision-suffix "s${DEPLOY_SHA::8}"
```

The UAMI `id-snto-gha-deployer` is Contributor on the whole RG, so it already
has rights over `snto-api` — no new role or federated credential is needed. The
command override and ingress are set on the app and are preserved across
`update`, so only the image tag changes per release. **The agent can make this
workflow edit for you in a PR — ask it to.**

## Rollback

```bash
# Full teardown (the API has no independent state — all data lives in snto-db):
az containerapp delete -g rg-snto-observatory-app -n snto-api --yes
# Then revert the workflow's "Roll API app" step in a follow-up commit.
```

Rolling back to a previous API image (keep the app, change the tag) follows the
same pattern as the dashboard rollback in [`../../DEPLOY.md`](../../DEPLOY.md).
