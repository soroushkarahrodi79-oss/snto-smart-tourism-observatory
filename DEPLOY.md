# Deploying SNTO to Azure Container Apps

This deploys the **Streamlit dashboard** (`app.py`) to Azure Container Apps on an
**Azure for Students** subscription, in **mock-data mode** (no database required).

> **Operational runbooks** (owner-executed, step-by-step `az`):
> [`docs/runbooks/`](docs/runbooks/README.md) — deploying the `/api/v2` HTTP
> surface (`snto-api`, ADR-012) and moving secrets to Azure Key Vault via
> managed identity.

## Why Container Apps, not an App Service "Web App"

The dashboard is a container workload. App Service Free **F1** cannot run it
(1 GB RAM, no Always On — Streamlit needs a persistent WebSocket process).
Container Apps gives a generous **free monthly grant** with **scale-to-zero**,
so a sporadically-visited thesis demo costs effectively nothing.

## What the app actually needs

- **No database.** `app.py` and `src/` never import `psycopg2`/SQLAlchemy; the
  dashboard is self-contained in mock-data mode. PostGIS is only used by the ETL
  scripts (`etl_*.py`, `db_production_seeder.py`) and is a **separate phase-2**
  concern (see bottom).
- **Python 3.12** (per `pyproject.toml` — not 3.11).
- Geospatial wheels (rasterio/shapely) install from PyPI without system GDAL;
  the Dockerfile uses `--only-binary=:all:` so a missing wheel fails the build
  loudly instead of breaking at runtime.

## One-time provisioning (Azure Cloud Shell)

1. Open the Azure Portal → **Cloud Shell** (Bash). It is already signed in to
   your subscription.
2. Clone the repo and run the bootstrap script:
   ```bash
   # --depth 1 avoids pulling the 4.3 GB git history (see hygiene note below)
   git clone --depth 1 https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory.git
   cd snto-smart-tourism-observatory
   bash deploy/azure-bootstrap.sh
   ```
3. The script prints a `https://…azurecontainerapps.io` URL. That is your live app.

This creates: resource group `rg-snto-observatory`, an ACR (Basic, ~US$5/mo),
a Container Apps environment, and the app with external ingress on port 8501,
scaled to zero, `USE_MOCK_DATA=true`.

## Continuous deployment (GitHub Actions) — CI-gated (ADR-009)

Deploys are **gated on CI**: `.github/workflows/deploy-azure-container-apps.yml`
triggers via `workflow_run` only when the `CI` workflow concludes **successfully
on `main`**. A red CI blocks the deploy; nothing ships unvalidated. The workflow
checks out and tags **the exact SHA that CI validated**
(`github.event.workflow_run.head_sha`), not whatever `main` points to when the
deploy starts.

Authentication is **OIDC + user-assigned managed identity (UAMI)** — the UCM
tenant blocks `az ad sp create-for-rbac`, so there is no service-principal
secret. The one-time UAMI/federated-credential bootstrap and the repo secrets
(`ACR_*`, `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID`) are
documented in the header of the workflow file itself.

A manual `workflow_dispatch` remains as the emergency path: it builds and
deploys the HEAD of the chosen ref without waiting for a CI chain (use only for
recovery; the normal path is merge → CI green → auto-deploy).

## Rollback runbook

Every deploy pushes an immutable image tag (`snto:<sha8>`) and creates a new
Container App revision (`--revision-suffix s<sha8>`), so rolling back means
pointing the app at a previous known-good image:

```bash
RG=rg-snto-observatory-app; APP=snto-observatory
# 1. Find the previous good revision / image tag:
az containerapp revision list -g $RG -n $APP \
  --query "[].{rev:name, img:properties.template.containers[0].image, active:properties.active}" -o table
# 2. Roll back to it (new revision from the old image; works in single-revision mode):
az containerapp update -g $RG -n $APP \
  --image acrsnto1781009309.azurecr.io/snto:<sha8-anterior> \
  --revision-suffix "rb$(date +%s)"
# 3. Verify:
FQDN=$(az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv)
curl -s -o /dev/null -w '%{http_code}\n' "https://$FQDN/_stcore/health"   # expect 200
```

Notes:

- Git history is untouched by a rollback — fix forward on `main`; the next
  CI-green merge redeploys automatically.
- **Secret changes don't propagate on their own** in Single-revision mode: after
  updating a Container App secret, run
  `az containerapp revision restart -g $RG -n $APP --revision <active>` (known
  gotcha from the 2026-07-18 Postgres cutover).
- DB rollback (unrelated to images): unset the five `SNTO_DB_*` env vars on the
  app → automatic fallback to local SQLite (ADR-011 §4bis).

## ⚠️ Repo hygiene — purge `data/` from git history

`data/` (3.4 GB of rasters/GeoJSON) is `.gitignore`d but **was committed
anyway** — the `.tif` files are real blobs in history. The image excludes them
(`.dockerignore`), but `git clone` / ACR remote build still pulls them, making
every build slow. Recommended cleanup:

```bash
git rm -r --cached data
git commit -m "Stop tracking data/ (already gitignored)"
# To also shrink history (optional, rewrites history):
#   pip install git-filter-repo && git filter-repo --path data --invert-paths
git push   # (--force if you rewrote history)
```

## Phase 2 — real PostGIS (decoupled, has a cost)

Azure Database for PostgreSQL Flexible Server has **no free tier**. When you
want the ETL pipeline live:

```bash
az postgres flexible-server create -g rg-snto-observatory -n pg-snto \
  --tier Burstable --sku-name Standard_B1ms --storage-size 32 \
  --version 16 --public-access 0.0.0.0
# then enable PostGIS:  CREATE EXTENSION postgis;
```

Stop it when idle (`az postgres flexible-server stop`) to limit credit burn,
then set the app's `USE_MOCK_DATA=false` plus DB connection env vars.
