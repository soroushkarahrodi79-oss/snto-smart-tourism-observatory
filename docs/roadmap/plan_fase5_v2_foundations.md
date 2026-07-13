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
  cambio del modelo de despliegue de Container Apps). Eso es una decisión
  explícita del propietario, tratada como **Decisión Abierta #1** más abajo.
- **No implementa SSO institucional.** El auth de la primera versión es mínimo
  y local (ver **Decisión Abierta #2**); la integración con Azure AD/Entra ID
  del tenant UCM (ya usado para OIDC de despliegue) es una extensión posterior,
  no un bloqueante de Fase 5.

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

## 2. Decisiones abiertas (requieren tu aprobación explícita antes de esos pasos)

Estas son bifurcaciones reales de coste/gobernanza que **no tomo por ti**:

1. **Aprovisionamiento de la base de datos de producción.** Cuándo y con qué
   servicio (p. ej. Azure Database for PostgreSQL Flexible Server) se crea el
   recurso real, quién paga el coste recurrente, y si el Container App actual
   (scale-to-zero, sin estado) cambia de modelo para sostener una conexión
   persistente. **Nada en esta fase lo hace por defecto.**
2. **Estrategia de autenticación.** Auth mínima propia (usuario/contraseña o
   API key, para desbloquear el modelo de roles) vs. SSO institucional (Azure
   AD/Entra ID del tenant UCM, ya usado para el despliegue). Recomiendo empezar
   mínimo y migrar a SSO cuando haya usuarios institucionales reales, pero es tu
   decisión.
3. **Quién es el primer consumidor del backend.** El plan de abajo prioriza el
   módulo P1 "Urgent actions" (`ui-evolution-v2-spec.md` §6) como primer punto
   de integración real UI↔backend, por ser el objeto central del producto. Si
   prefieres otro punto de entrada (p. ej. solo el catálogo de activos de
   solo-lectura), lo reordeno.

## 3. Esquema de recursos (SQLAlchemy, `src/persistence/models/`)

Deriva directamente de la lista de ADR-006 y del ciclo de vida de
`ui-evolution-v2-spec.md` §3. Tipos de columna portables SQLite↔PostgreSQL
(sin extensiones específicas de Postgres en el primer corte; PostGIS se añade
cuando se aprovisione la base de datos real — Decisión Abierta #1).

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

| Paso | Contenido | Riesgo |
|---|---|---|
| 5.0 | Este documento + ADR-011 (docs-only) | Ninguno |
| 5.1 | `src/persistence/models/` (SQLAlchemy 2.0, `Mapped`/`mapped_column`) + `src/persistence/session.py` (engine/session factory leyendo `SNTO_DB_*` de `settings`, con SQLite de fichero como default de desarrollo) + Alembic inicializado (`alembic/`, primera migración) | Bajo — solo código + SQLite local, sin infra nueva |
| 5.2 | Capa de repositorio/servicio (`src/persistence/repositories/`) — CRUD tipado por recurso, tests con SQLite en memoria | Bajo |
| 5.3 | `src/api/v2/` — nuevo namespace versionado; endpoints de solo-lectura para `ManagedAsset`/`Observation` respaldados por la capa de persistencia; `/evaluate_asset` etc. actuales quedan intactos (o se re-etiquetan como `/api/v1/` sin cambiar comportamiento) | Bajo — aditivo |
| 5.4 | `Alert`/`Recommendation` como recursos persistentes; puente desde `src.alerts.engine` (ya calcula esto en memoria) a un registro persistente | Medio |
| 5.5 | Ciclo de vida de `Intervention` (`detected→…→monitored`) + endpoints de transición de estado con validación de transiciones permitidas | Medio |
| 5.6 | `FieldVerification` — registro persistente que sustituye/complementa el CSV de `docs/field_validation_protocol.md` (#26) | Bajo |
| 5.7 | `AuditLogEntry` — cada escritura en 5.3–5.6 deja rastro; endpoint de solo-lectura para auditoría | Bajo |
| 5.8 | Auth mínima (según Decisión Abierta #2) — gatea escritura, no lectura | Depende de la decisión |
| 5.9 | Primer consumidor real en `src/ui/`: el módulo "Urgent actions" (P1) lee/escribe contra la API v2 en vez de solo memoria — primer punto de integración UI↔backend persistente | Medio — toca `src/ui/tabs/` |

Cada paso: rama desde `main`, tests (SQLite en CI, igual que el resto de la
suite), sin cambio de comportamiento fuera de lo que el paso añade
explícitamente, PR individual, **sin auto-merge** (igual que todo lo anterior).

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
