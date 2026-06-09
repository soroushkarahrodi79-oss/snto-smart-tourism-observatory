#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# SNTO — one-shot Azure Container Apps provisioner (Azure for Students)
#
# Runs end-to-end in Azure Cloud Shell (already authenticated, az + Docker-less
# build via `az acr build`). Idempotent: safe to re-run.
#
#   bash deploy/azure-bootstrap.sh
#
# Cost note: Container Apps stays within the free monthly grant when scaled to
# zero. ACR Basic is ~US$5/mo. No database is created here — the dashboard runs
# in mock-data mode. PostGIS is a separate phase-2 step (see DEPLOY.md).
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config (override via env before running) ─────────────────────────────────
RG="${RG:-rg-snto-observatory}"
LOCATION="${LOCATION:-westeurope}"
ACR="${ACR:-acrsnto$RANDOM}"            # ACR names must be globally unique, alphanumeric
ENV_NAME="${ENV_NAME:-cae-snto}"
APP_NAME="${APP_NAME:-snto-observatory}"
IMAGE_REPO="snto"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GIT_REPO="${GIT_REPO:-https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory.git}"
TARGET_PORT=8501

echo "▶ Subscription in use:"
az account show --query "{name:name, id:id}" -o table

# ── 1. Providers ──────────────────────────────────────────────────────────────
echo "▶ Registering resource providers (idempotent)…"
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.OperationalInsights --wait
az provider register -n Microsoft.ContainerRegistry --wait

# ── 2. Resource group ─────────────────────────────────────────────────────────
echo "▶ Resource group: $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" -o none

# ── 3. Container registry (Basic) + remote build from GitHub ──────────────────
echo "▶ Container registry: $ACR"
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true -o none

# Build from the LOCAL working dir (run this script from the repo root). The
# build context honours .dockerignore, so data/ (3.4 GB) and the 4.3 GB git
# history are NOT uploaded — only the code. Do NOT pass the git URL here: ACR
# would clone the entire bloated history.
echo "▶ Building image in the cloud from local context (no local Docker needed)…"
az acr build --registry "$ACR" --image "$IMAGE_REPO:$IMAGE_TAG" .

ACR_SERVER="$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show -n "$ACR" -g "$RG" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR" -g "$RG" --query "passwords[0].value" -o tsv)"

# ── 4. Container Apps environment ─────────────────────────────────────────────
echo "▶ Container Apps environment: $ENV_NAME"
az containerapp env create -g "$RG" -n "$ENV_NAME" -l "$LOCATION" -o none

# ── 5. The app — external ingress, scale-to-zero (free-grant friendly) ────────
echo "▶ Deploying container app: $APP_NAME"
az containerapp create \
  -g "$RG" -n "$APP_NAME" \
  --environment "$ENV_NAME" \
  --image "$ACR_SERVER/$IMAGE_REPO:$IMAGE_TAG" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port "$TARGET_PORT" \
  --ingress external \
  --transport auto \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 1.0 --memory 2.0Gi \
  --env-vars USE_MOCK_DATA=true PORT=$TARGET_PORT \
  -o none

FQDN="$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
echo
echo "✅ Deployed. Live URL:  https://$FQDN"
echo "   (first request after idle cold-starts in ~10–30s — that is the price of \$0 scale-to-zero)"
echo
echo "Re-deploy after a code change (from repo root):"
echo "   az acr build --registry $ACR --image $IMAGE_REPO:$IMAGE_TAG ."
echo "   az containerapp update -g $RG -n $APP_NAME --image $ACR_SERVER/$IMAGE_REPO:$IMAGE_TAG"
