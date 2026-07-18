# Fase 5 — Fundamentos de v2.0: backend persistente, ciclo de vida del activo gestionado, API versionada

> Concreta [ADR-011](../decisions/ADR-011.md) (que a su vez concreta ADR-006) en
> un plan ejecutable, en el mismo formato y disciplina que
> [`plan_fases_post_v1.2.md`](plan_fases_post_v1.2.md): PRs pequeños,
> verificables, sin auto-merge, con smoke test donde aplique. Es el paso que
> `docs/ux/ui-evolution-v2-spec.md` llama **"Pre-v2 técnico"**: la
> modularización de `app.py` (#27) ya está hecha; esto cierra la mitad que
> falta (persistencia diseñada e implementada en local/CI, sin aprovisionar
> nube todavía).

## 0. Qué NO es esta fase

- **No es** el rediseño visual de v2.0 (Decidir/Diagnosticar/Evidenciar/Gobernar,
  home pages por rol). Eso sigue gateado hasta que esta fase entregue un
  backend real que consumir (`ui-evolution-v2-spec.md` §13).
- **No aprovisiona ningún recurso de nube** (base de datos gestionada, secretos,
  cambio del modelo de despliegue de Container Apps). El aprovisionamiento de
  producción sigue siendo un paso explícito y ejecutado por el propietario
  (comandos documentados en §4bis), no algo que estas PRs hagan por su cuenta.
- **No implementa SSO institucional.** Decidido (2026-07-13): el auth de la
  primera versión es **mínimo y propio** (API key / token de sesión, gatea
  solo escritura). Azure AD/Entra ID del tenant UCM queda como extensión
  posterior, no un bloqueante de Fase 5.

## 1. Estado real verificado

- `requirements.txt` ya fija `sqlalchemy>=2.0` y `psycopg2-binary`; `.env.example`
  ya declara `SNTO_DB_HOST/PORT/NAME/USER/PASS`. Nadie ha escrito código de
  conexión, modelos o migraciones — `src/config/settings.py` ni siquiera lee
  esas variables.
- `src/api/` es un FastAPI sin estado (3 routers: `evaluate`, `ranking`,
  `alerts`), sin sesión de base de datos, sin versión en el path.
- Los modelos de dominio existentes (`src/assets/models.TourismAsset`,
  `src/territorial/models.TerritorialAsset`, `src/intervention/models`) son
  **Pydantic puro**, calculados en memoria por ejecución — no hay registro
  persistente de qué pasó con un activo entre una ejecución y la siguiente.
- El objeto central que pide `ui-evolution-v2-spec.md` §3 —el **activo
  gestionado** con ciclo `detected → verified → assigned → funded → resolved →
  monitored`— no existe en ninguna forma hoy.

## 2. Decisiones (resueltas 2026-07-13, delegadas por el propietario)

1. **Aprovisionamiento de la base de datos de producción: diferido, ejecución
   manual del propietario cuando decida pasar a producción.** Ninguna PR de
   esta fase crea recursos de nube ni incurre coste recurrente. Los comandos
   exactos para cuando quieras hacer el cutover están en §4bis.
2. **Estrategia de autenticación: mínima propia** (API key o token de sesión),
   gatea solo endpoints de **escritura**; lectura queda abierta, misma postura
   que la API actual. SSO institucional (Azure AD/Entra ID del tenant UCM) se
   añade más adelante si hace falta acceso multi-usuario real — es un cambio
   aditivo de la dependencia de auth, no del esquema ni del contrato de API.
3. **Primer consumidor del backend: el módulo "Urgent actions"** (P1,
   `ui-evolution-v2-spec.md` §6), por ser el objeto central del producto
   (activo gestionado con ciclo de vida). Paso 5.9 del plan de abajo.

## 3. Esquema de recursos (SQLAlchemy, `src/persistence/models/`)

Deriva directamente de la lista de ADR-006 y del ciclo de vida de
`ui-evolution-v2-spec.md` §3. Tipos de columna portables SQLite↔PostgreSQL
(sin extensiones específicas de Postgres en el primer corte; PostGIS se añade
cuando se aprovisione la base de datos real, ver §4bis).

```
Territory        id, slug, name, budget_eur, created_at
ManagedAsset      id, territory_id, external_asset_id, name, asset_type,
                  geometry_geojson (JSON), region, status
                  (detected|verified|assigned|funded|resolved|monitored),
                  created_at, updated_at
Observation       id, asset_id, observed_at, source (real|calibrated|
                  synthetic|simulated — reusa src.platform.evidence.EvidenceClass),
                  ehs, ndvi, ndmi, raw_payload (JSON)
Alert             id, asset_id, level, risk_score, triggered_rules (JSON),
                  status (open|assigned|escalated|dismissed), reason, created_at
Recommendation    id, alert_id, action_label, cost_eur_low, cost_eur_high,
                  confidence (dcs), owner, deadline, status
FieldVerification id, asset_id, verified_at, method, verifier, result,
                  photo_ref, notes
Intervention      id, asset_id, recommendation_id, status, budget_eur,
                  started_at, resolved_at
Decision          id, subject_type, subject_id, decided_by, decision, reason,
                  decided_at
AuditLogEntry     id, actor, action, subject_type, subject_id, payload (JSON),
                  created_at
```

Cada tabla con un campo de evidencia reutiliza el vocabulario ya canónico de
`src.platform.evidence.EvidenceClass` (#10) — no se inventa una taxonomía nueva.
`ManagedAsset.status` es exactamente el ciclo de vida del §3 de la spec de UI.

## 4. Pasos de implementación (PRs pequeños, patrón de Fase 4)

**✅ COMPLETADA — los 10 pasos (5.0–5.9) están mergeados en `main`** (PRs #61
diseño y #62–#70 implementación). Lo único pendiente de Fase 5 es el cutover
manual a Postgres (§4bis), que es una acción explícita del propietario, no un
paso de código.

| Paso | Contenido | Riesgo | Estado |
|---|---|---|---|
| 5.0 | Este documento + ADR-011 (docs-only) | Ninguno | ✅ #61 |
| 5.1 | `src/persistence/models/` (SQLAlchemy 2.0, `Mapped`/`mapped_column`) + `src/persistence/session.py` (engine/session factory leyendo `SNTO_DB_*` de `settings`, con SQLite de fichero como default de desarrollo) + Alembic inicializado (`alembic/`, primera migración) | Bajo — solo código + SQLite local, sin infra nueva | ✅ #62 |
| 5.2 | Capa de repositorio/servicio (`src/persistence/repositories/`) — CRUD tipado por recurso, tests con SQLite en memoria | Bajo | ✅ #63 |
| 5.3 | `src/api/v2/` — nuevo namespace versionado; endpoints de solo-lectura para `ManagedAsset`/`Observation` respaldados por la capa de persistencia; `/evaluate_asset` etc. actuales quedan intactos | Bajo — aditivo | ✅ #64 |
| 5.4 | `Alert`/`Recommendation` como recursos persistentes; puente desde `src.alerts.engine` (ya calcula esto en memoria) a un registro persistente | Medio | ✅ #65 |
| 5.5 | Ciclo de vida (activo gestionado `detected→…→monitored` + intervención `planned→…→resolved`) + endpoints de transición con validación de transiciones permitidas | Medio | ✅ #66 |
| 5.6 | `FieldVerification` — registro persistente que sustituye/complementa el CSV de `docs/field_validation_protocol.md` (#26) | Bajo | ✅ #67 |
| 5.7 | `AuditLogEntry` — cada escritura en 5.3–5.6 deja rastro; endpoint de solo-lectura para auditoría | Bajo | ✅ #68 |
| 5.8 | Auth mínima propia (API key) — gatea escritura, no lectura | Bajo | ✅ #69 |
| 5.9 | Primer consumidor real en `src/ui/`: el módulo "Acciones urgentes" (P1) lee/escribe contra el backend persistente — primer punto de integración UI↔backend | Medio — toca `src/ui/tabs/` | ✅ #70 |

Cada paso siguió: rama desde `main`, tests (SQLite en CI, igual que el resto de
la suite), sin cambio de comportamiento fuera de lo que el paso añadió
explícitamente, PR individual, **sin auto-merge** (aprobación humana por PR).

## 4bis. Cutover a producción (ejecución manual del propietario, cuando decidas)

> **✅ EJECUTADO por el propietario el 2026-07-18.** Azure Postgres Flexible
> Server `snto-db` (v16, Burstable B1ms, PostGIS, Sweden Central, mismo RG que
> el Container App), firewall estrecho (Azure services + IP del propietario),
> las 9 tablas creadas vía Alembic, y los 5 secrets `SNTO_DB_*` cableados en el
> Container App `snto-observatory`. Verificado en vivo: la pestaña "Acciones
> Urgentes" muestra el estado conectado-pero-vacío. `SNTO_API_KEY` queda
> deliberadamente sin fijar (escrituras abiertas) por ahora. Rollback trivial:
> quitar los 5 `SNTO_DB_*` del Container App → vuelta automática a SQLite.
>
> Gotchas operativos aprendidos: (1) `az postgres flexible-server create`
> imprime la contraseña admin en su salida JSON — usar `-o none`; (2) `db
> create` usa `--name`, no `-d`; (3) habilitar acceso público a posteriori es
> `--public-access Enabled`, no `--public-network-access`; (4) un Container App
> en modo Single revision **no** recoge un secret actualizado sin un
> `az containerapp revision restart` explícito.
>
> **Hallazgo clave:** la API FastAPI `/api/v2` (`src/api/main.py`) **no está
> desplegada en ningún sitio** — solo la pestaña Streamlit in-process
> (`src/ui/services/urgent_actions.py`) consume la capa de persistencia.
> Exponer la API REST por HTTP es un follow-up separado, aún sin scope.

Ningún paso 5.1–5.9 crea esto. Cuando quieras pasar de SQLite a Postgres real
(comandos originales, ya ejecutados una vez):

```bash
# 1) Aprovisionar Postgres Flexible Server (Azure Cloud Shell, identidad owner)
RG=rg-snto-observatory-app
az postgres flexible-server create -g $RG -n snto-db \
    --admin-user snto_admin --admin-password <secreto> \
    --sku-name Standard_B1ms --tier Burstable --version 16 \
    --storage-size 32 --public-access 0.0.0.0

# 2) Habilitar PostGIS
az postgres flexible-server parameter set -g $RG -s snto-db \
    --name azure.extensions --value POSTGIS

# 3) Añadir SNTO_DB_HOST/PORT/NAME/USER/PASS reales como secrets del Container
#    App (no en .env versionado) y aplicar las migraciones Alembic ya
#    verificadas contra SQLite:
alembic upgrade head   # con DATABASE_URL apuntando al Postgres real
```

El coste recurrente y el cambio de modelo de despliegue (el Container App deja
de ser puramente stateless) son explícitamente tu decisión, no algo que estas
PRs asuman.

## 5. Verificación por paso

- `python -m pytest -q` en verde (SQLite in-memory para los tests nuevos, sin
  dependencia de una base de datos real).
- `alembic upgrade head` / `alembic downgrade base` limpios desde una base de
  datos vacía.
- `ruff check src/persistence src/api` limpio (nuevo módulo, se propone añadir
  a la zona bloqueante de `.github/workflows/ci.yml` desde el principio, no
  como deuda).
- A partir del paso 5.3: `pytest tests/integration/` con `TestClient` de
  FastAPI contra la API v2, sin necesidad de servidor real.
- El paso 5.9 requiere además smoke test manual (`streamlit run app.py`),
  mismo patrón que Fase 4.

## 6. Relación con el resto del roadmap

Esta fase es el prerequisito técnico que `ui-evolution-v2-spec.md` llama
"Pre-v2" (§11). Una vez completada (o al menos los pasos 5.1–5.5), el
rediseño de UI de v2.0 propiamente dicho (capas Decidir/Diagnosticar/
Evidenciar/Gobernar, home pages por rol) tiene un backend real sobre el que
construirse, en vez de simular persistencia en `st.session_state`.

## Documentos relacionados

- [ADR-011 — Arquitectura concreta del backend persistente](../decisions/ADR-011.md)
- [ADR-006 — Backend persistente antes de flujos operacionales](../decisions/ADR-006.md)
- [UI Evolution v2.0 Spec](../ux/ui-evolution-v2-spec.md)
- [Future Architecture](../architecture/future-architecture.md)
- [plan_fases_post_v1.2.md](plan_fases_post_v1.2.md) (Fases 0–4, ya completadas)
