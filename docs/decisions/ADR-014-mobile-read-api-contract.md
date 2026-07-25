# ADR-014 — Contrato de lectura `/api/v2` para el cliente móvil (Fase 2)

- **Estado:** Aceptada
- **Fecha:** 2026-07-25
- **Alcance:** `src/api/v2/`, `mobile/` (consumo en un PR posterior)
- **Precede a:** [ADR-013](ADR-013-mobile-client.md) (fundación del cliente,
  Fase 1), que dejó explícitamente esta decisión como condición de Fase 2:
  *"Antes de leer datos reales desde el móvil se debe acordar un contrato API
  versionado."*

## Contexto

ADR-013 (Fase 1) construyó el cimiento del cliente móvil sobre fixtures
sintéticos y un adaptador HTTP `GET`-only ya preparado
(`createReadOnlyApiClient`) pero sin backend real que consumir. `/api/v2`
(Fase 5, ADR-011) ya exponía activos, alertas, intervenciones y verificaciones
de campo — pero **le faltaban dos cosas** que la pantalla de inicio y el mapa
del móvil necesitan:

1. **Ningún endpoint de territorios.** `TerritoryOut` existía como esquema
   desde Fase 5 pero nunca se montó un router — la tabla `territories`
   persistida no tenía superficie de lectura.
2. **Ninguna coordenada ni frescura por activo.** `ManagedAsset.geometry_geojson`
   guarda geometría real (texto opaco hoy — PostGIS es trabajo futuro del
   roadmap v3), pero `ManagedAssetOut` nunca la serializaba; tampoco existía
   forma de saber, sin una llamada por activo, cuál es su evidencia y fecha
   más reciente.

## Decisión

Extender `/api/v2` con el contrato de lectura mínimo que el `MobileRepository`
de la Fase 1 ya anticipaba (`HomeSummary`, `TourismAsset`, `ObservatoryAlert`):

- **`GET /api/v2/territories/`** y **`GET /api/v2/territories/{id}`** — lectura
  simple sobre `TerritoryOut` (ya existía el esquema, faltaba el router).
- **`GET /api/v2/territories/{id}/summary`** — roll-up expresamente pensado
  para una pantalla de inicio: `asset_count`, `open_alert_count`,
  `updated_at` y `evidence_class` de la observación más reciente del
  territorio. Una llamada, no N.
- **`ManagedAssetOut` ampliado** con `latitude`/`longitude` (centroide) y
  `latest_observed_at`/`latest_evidence_class` (de la observación más
  reciente del activo) — para que una vista de lista no necesite una llamada
  por activo.
- **`src/api/v2/geometry.py`** — un centroide **deliberadamente sin
  `shapely`**: `src/geospatial/geometry.py` ya hace análisis geométrico real
  para el núcleo analítico (Pipeline A/B); esta es una capa distinta y más
  ligera, «dónde poner aproximadamente un pin de mapa», con aritmética plana
  sobre el array de coordenadas GeoJSON.

Todo degrada de forma honesta: geometría no parseable → `latitude`/`longitude`
`None`; activo o territorio sin observaciones → `updated_at`/`evidence_class`
`None`. Nunca se fabrica una coordenada o una clase de evidencia (ADR-004).

## Alcance explícitamente excluido de esta ADR

- **No se decide proveedor de mapa** (Mapbox, Google Maps, `react-native-maps`,
  …). Esa es una decisión de licencia/coste/telemetría separada, tal como ya
  fijó ADR-013. Esta ADR solo garantiza que el **dato** (coordenadas) esté
  disponible para cuando esa decisión se tome; la pantalla de mapa del móvil
  sigue mostrando su placeholder honesto.
- **No se despliega `/api/v2` como servicio.** Sigue en el estado de ADR-012
  (código + tests, no desplegado). El adaptador HTTP del móvil (Fase 2,
  siguiente PR) se construye y testea contra este contrato con `fetch`
  mockeado — queda listo para apuntar a un backend real el día que se
  despliegue, sin bloquear el trabajo de cliente mientras tanto.
- **No se toca la escritura.** Los endpoints de escritura existentes
  (`transition`, `triage`, intervenciones, verificaciones de campo) no
  cambian; esta ADR es puramente de lectura.

## Consecuencias

Positivas: el móvil (Fase 2) puede implementar un repositorio HTTP real
conforme al contrato exacto que su interfaz `MobileRepository` ya declaraba,
sin re-round-trips por activo para lo que una lista necesita. `/api/v2` gana
su primer endpoint de territorios, cerrando una laguna que también afecta a
cualquier otro consumidor futuro (no solo móvil).

Negativas: `ManagedAssetOut` deja de ser un passthrough ORM puro (gana dos
campos computados) — documentado explícitamente en el propio esquema para que
la próxima persona no lo confunda con una columna real.

## Condiciones para fases posteriores

Antes de leer datos **reales** de producción desde el móvil, `/api/v2` debe
estar desplegado (ADR-012, decisión pendiente del propietario) y debe existir
identidad de usuario para las lectures con alcance por tenant (ver ADR-005 /
`src.persistence.services.authz`, hoy aplicado solo a escrituras). Hasta
entonces, el repositorio HTTP del móvil es código completo y probado, pero
inalcanzable en producción — el modo por defecto sigue siendo el fixture
sintético.
