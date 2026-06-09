# Deploying SNTO to Azure Container Apps

This deploys the **Streamlit dashboard** (`app.py`) to Azure Container Apps on an
**Azure for Students** subscription, in **mock-data mode** (no database required).

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

## Continuous deployment (GitHub Actions)

After the one-time bootstrap, wire CI/CD so every push to `main` redeploys:

1. Create a deployment service principal:
   ```bash
   az ad sp create-for-rbac --name snto-deployer --role contributor \
     --scopes /subscriptions/<SUB_ID>/resourceGroups/rg-snto-observatory --sdk-auth
   ```
2. In GitHub → **Settings ▸ Secrets and variables ▸ Actions**, add:
   - `AZURE_CREDENTIALS` = the JSON from step 1
   - `ACR_NAME` = your ACR name (printed by the bootstrap script)
3. Push to `main`. `.github/workflows/deploy-azure-container-apps.yml` builds and rolls the app.

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
