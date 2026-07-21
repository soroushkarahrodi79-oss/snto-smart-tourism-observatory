# Runbook: move secrets to Azure Key Vault (managed identity)

Today the Container App holds `SNTO_DB_PASS` (and, once
[`snto-api-deploy.md`](snto-api-deploy.md) runs, `SNTO_API_KEY`) as **inline
Container App secrets**, and it pulls from ACR with **admin username/password**.
This runbook moves both to a **managed-identity** model:

- secret *values* live in **Azure Key Vault**; the app references them and reads
  them at runtime via its own identity (no secret material in app config or the
  deploy workflow);
- ACR pull uses the app's **managed identity** with the `AcrPull` role instead
  of admin credentials.

Non-secret values (`SNTO_DB_HOST/PORT/NAME/USER`) stay as plain env vars — only
the password and API key are sensitive.

> Do this **per app**: `snto-observatory` today, and `snto-api` too once it
> exists. The steps are identical; the loop at the top handles both.

## Preflight

```bash
RG=rg-snto-observatory-app
LOCATION=swedencentral
KV=kv-snto-observatory            # must be globally unique; adjust if taken
APPS=(snto-observatory)           # add snto-api here once it is deployed
ACR_ID=$(az acr show -n acrsnto1781009309 --query id -o tsv)
```

## 1. Create the Key Vault (RBAC authorization)

```bash
az keyvault create -g $RG -n $KV -l $LOCATION \
  --enable-rbac-authorization true \
  --public-network-access Enabled     # tighten to a private endpoint later if required

KV_ID=$(az keyvault show -n $KV --query id -o tsv)

# Let YOURSELF write secrets (RBAC mode needs an explicit role):
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee "$ME" \
  --role "Key Vault Secrets Officer" --scope "$KV_ID"
```

## 2. Store the secret values

```bash
# DB password — paste the real value (or read it from the existing app secret).
az keyvault secret set --vault-name $KV -n snto-db-pass --value "<DB_PASSWORD>"

# API key — only if/when snto-api is in play (same value you stored at API create).
az keyvault secret set --vault-name $KV -n snto-api-key --value "<API_KEY>"
```

## 3. Give each app an identity + read access, then switch to KV references

```bash
for APP in "${APPS[@]}"; do
  # a) System-assigned managed identity on the app.
  az containerapp identity assign -g $RG -n $APP --system-assigned
  PID=$(az containerapp show -g $RG -n $APP --query identity.principalId -o tsv)

  # b) Let that identity READ secrets from the vault.
  az role assignment create --assignee "$PID" \
    --role "Key Vault Secrets User" --scope "$KV_ID"

  # c) Repoint the app's secrets at Key Vault (value now comes from KV at runtime,
  #    resolved via the system identity). The env-var secretrefs do NOT change.
  DB_URI=$(az keyvault secret show --vault-name $KV -n snto-db-pass --query id -o tsv)
  az containerapp secret set -g $RG -n $APP \
    --secrets "snto-db-pass=keyvaultref:${DB_URI},identityref:system"

  # If this app uses the API key (snto-api):
  if az containerapp show -g $RG -n $APP \
       --query "properties.template.containers[0].env[?name=='SNTO_API_KEY']" -o tsv | grep -q .; then
    API_URI=$(az keyvault secret show --vault-name $KV -n snto-api-key --query id -o tsv)
    az containerapp secret set -g $RG -n $APP \
      --secrets "snto-api-key=keyvaultref:${API_URI},identityref:system"
  fi

  # d) 🔴 Single-revision gotcha: secret-value changes need an explicit restart.
  REV=$(az containerapp show -g $RG -n $APP --query properties.latestRevisionName -o tsv)
  az containerapp revision restart -g $RG -n $APP --revision "$REV"
done
```

> Using the vault's **secret id without a version** (as above) means Container
> Apps tracks the *latest* version — rotating the password in Key Vault plus a
> revision restart is then the whole rotation procedure.

## 4. ACR pull via managed identity (drop the admin password)

```bash
for APP in "${APPS[@]}"; do
  PID=$(az containerapp show -g $RG -n $APP --query identity.principalId -o tsv)
  # Grant pull on the registry to the app identity.
  az role assignment create --assignee "$PID" --role "AcrPull" --scope "$ACR_ID"
  # Switch the app's registry auth from admin creds to the system identity.
  az containerapp registry set -g $RG -n $APP \
    --server acrsnto1781009309.azurecr.io --identity system
done
```

Then in [`.github/workflows/deploy-azure-container-apps.yml`](../../.github/workflows/deploy-azure-container-apps.yml)
the **image build+push** still needs registry auth, but the **roll** step no
longer relies on the app's admin creds. Once every app pulls via identity you
can disable the ACR admin user entirely:

```bash
az acr update -n acrsnto1781009309 --admin-enabled false
```

Only do that after confirming both the build job (which logs into ACR to push)
still has a working path — it currently uses `ACR_USERNAME`/`ACR_PASSWORD`
secrets, so **keep admin enabled until the build job is also moved to OIDC-based
ACR login** (a follow-up; the UAMI `id-snto-gha-deployer` would need `AcrPush`).
Disabling admin while the build job still uses it will break deploys.

## Verify

```bash
APP=snto-observatory
# The app resolves the KV reference and serves normally:
FQDN=$(az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv)
curl -s -o /dev/null -w "%{http_code}\n" "https://$FQDN/_stcore/health"   # expect 200
# Confirm the secret is now a KV reference (shows a keyVaultUrl, not a value):
az containerapp secret show -g $RG -n $APP --secret-name snto-db-pass -o json
```

## Rollback

```bash
# Put an inline secret value back (reverts to pre-KV behavior), then restart:
az containerapp secret set -g $RG -n snto-observatory --secrets "snto-db-pass=<DB_PASSWORD>"
REV=$(az containerapp show -g $RG -n snto-observatory --query properties.latestRevisionName -o tsv)
az containerapp revision restart -g $RG -n snto-observatory --revision "$REV"

# Revert ACR pull to admin creds if identity pull misbehaves:
az acr update -n acrsnto1781009309 --admin-enabled true
az containerapp registry set -g rg-snto-observatory-app -n snto-observatory \
  --server acrsnto1781009309.azurecr.io \
  --username "$(az acr credential show -n acrsnto1781009309 --query username -o tsv)" \
  --password "$(az acr credential show -n acrsnto1781009309 --query passwords[0].value -o tsv)"
```

The database itself is untouched by anything here — this runbook only changes
*where the app reads the password from*, never the password or the data.
