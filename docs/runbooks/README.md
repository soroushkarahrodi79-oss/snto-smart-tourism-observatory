# SNTO operational runbooks

Owner-executed operational procedures. Each runbook is a copy-pasteable
sequence with a **safety gate** at the top and a **rollback** at the bottom.
They are grounded in the real deployed resources (see the fact table below),
not generic Azure boilerplate.

These procedures are executed by the **owner** from Azure Cloud Shell (already
signed in) or a local `az` session — the agent environment cannot run `az`
(the UCM tenant blocks service principals; auth is OIDC/UAMI, see
[`../../DEPLOY.md`](../../DEPLOY.md)).

## Runbooks

| Runbook | What it does | v2.1 roadmap item |
|---|---|---|
| [`snto-api-deploy.md`](snto-api-deploy.md) | Stand up the `/api/v2` HTTP surface as a second Container App (`snto-api`), ADR-012 Option C. **Sets `SNTO_API_KEY` before first exposure.** | "Deploy `/api/v2`" |
| [`keyvault-secrets.md`](keyvault-secrets.md) | Move `SNTO_DB_*` / `SNTO_API_KEY` into Azure Key Vault via managed identity; ACR pull via managed identity. | "Secrets hardening" |

## Live infrastructure fact table (as of 2026-07-18 cutover)

| Thing | Value |
|---|---|
| Resource group | `rg-snto-observatory-app` |
| Region | Sweden Central |
| Container Apps environment | shared by `snto-observatory` (query it, don't hardcode — see runbooks) |
| Existing app (Streamlit) | `snto-observatory`, ingress target port **8501** |
| Container registry (ACR) | `acrsnto1781009309.azurecr.io`, image repo `snto`, tags `<sha8>` + `latest` |
| Database | Azure Postgres Flexible Server `snto-db` (v16, Burstable B1ms, PostGIS), same RG, firewall = Azure services + owner IP |
| DB secrets on `snto-observatory` | five `SNTO_DB_*` env vars (host/port/name/user/pass) |
| `SNTO_API_KEY` | **intentionally unset** today (writes open; safe only because the sole caller is the in-process Streamlit UI) |
| CD identity | UAMI `id-snto-gha-deployer`, **Contributor on the whole RG** → already covers any new app/vault in this RG |
| CD workflow | [`.github/workflows/deploy-azure-container-apps.yml`](../../.github/workflows/deploy-azure-container-apps.yml) (CI-gated since #95) |

## Two gotchas that apply to every runbook here

1. **Single-revision secret refresh.** Container Apps in *Single* revision mode
   do **not** pick up changed secret *values* automatically. After any
   `az containerapp secret set`, force it:
   `az containerapp revision restart -g <rg> -n <app> --revision <active-revision>`.
2. **The agent cannot run these.** Every command below is for you to run. The
   agent can prepare, review, and adjust the scripts, and can edit the CD
   workflow — it cannot touch Azure.
