# Blueprints de páginas — Experience Builder MVP

> Fase 2A · documentación únicamente. Todos los widgets son **estándar de ArcGIS
> Online**; cualquier carencia se marca **[Diferido — brecha widget]**, nunca se
> asume widget personalizado. Marcadores: **[Verificado]/[Propuesto]/[Desconocido]/[Diferido]**.

La app EB reutiliza la gramática de 4 capas de `src/ui/navigation.py`
(**[Verificado]**) como esqueleto, re-expresada en clave map-centric. Fuente de
datos por defecto: la Hosted Feature Layer de activos (snapshot) y, cuando se
publique, el feature service de observaciones Survey123.

Widgets estándar usados: **Map, List, Table, Feature Info, Filter, Search, Chart,
Text, Button, Menu, Section/Views, Embed, Survey** + *message/data actions* y
parámetros de URL.

---

## Página 1 · Decidir

| Atributo | Definición |
|---|---|
| **Persona** | Gestor/directivo del parque (perfil «Decidir» de `ViewProfile`). |
| **Pregunta** | ¿Qué debe decidirse esta semana? |
| **Fuente de datos** | Hosted Feature Layer de activos (snapshot). |
| **Widgets** | `Text` (3–4 KPIs), `List` (activos prioritarios ordenados por `is_degrading`+`confidence`), `Map` pequeño de contexto, `Button` («Ver en Diagnosticar»). |
| **Layout** | Fila de KPIs arriba; lista prioritaria a la izquierda; mapa de contexto a la derecha. |
| **Message/Data actions** | Seleccionar en `List` → *pan/zoom* del `Map` + filtra Asset Detail. `Button` → navega a Diagnosticar con el activo seleccionado (parámetro de URL). |
| **Filtros** | Solo `is_degrading = 1` por defecto (conmutable). |
| **Estado vacío** | «Sin activos prioritarios en este snapshot» (nunca 0 activos falsos). |
| **Carga/error** | Skeleton de KPIs; si la capa no carga: «No se pudo cargar el snapshot; última fecha conocida: —». |
| **Etiquetas de evidencia** | Cada KPI y fila muestra `confidence` + badge de `evidence_level`. **Ningún** valor `simulated`/`estimated` como titular. |
| **Responsive** | Móvil: KPIs en columna, mapa colapsable bajo la lista. |
| **Criterios de aceptación** | (a) máx. 4 cifras de decisión; (b) el usuario encuentra el activo prioritario (Maliciosa–Porrones) sin narrador; (c) ninguna cifra sin `confidence`/evidencia. |

---

## Página 2 · Diagnosticar (página central, map-centric)

| Atributo | Definición |
|---|---|
| **Persona** | Técnico de conservación / analista. |
| **Pregunta** | ¿Es real la señal y dónde ocurre? |
| **Fuente de datos** | Capa de activos (snapshot) + capa PRUG/límite **[Propuesto, condicionado a licencia]**. |
| **Widgets** | `Map` (a pantalla completa, principal), `List` y `Table` acopladas, `Filter`, `Search`. |
| **Layout** | Mapa dominante; panel lateral con List/Table conmutables; barra de filtros superior. |
| **Message/Data actions** | Sincronización **Map ↔ List ↔ Table**: seleccionar en cualquiera resalta en los demás. Clic en entidad → abre **Asset Detail** (Feature Info). |
| **Filtros** | Por `trend`, `confidence`, `has_trend`, `category`, `is_degrading`. |
| **Estado vacío** | Filtro sin resultados → «Ningún activo cumple el filtro» + botón «Restablecer». |
| **Carga/error** | Spinner del mapa; capa PRUG opcional falla en silencio con aviso «Capa de contexto no disponible». |
| **Etiquetas de evidencia** | Simbología por `trend` + patrón/etiqueta para `has_trend=false` (no solo color). Popup muestra `evidence_level`, `p_value`, IC de Sen. |
| **Responsive** | Tablet/móvil: panel List/Table como hoja inferior deslizable; mapa siempre visible. |
| **Criterios de aceptación** | (a) selección sincronizada en las 3 vistas; (b) `has_trend=false` distinguible sin color; (c) el usuario localiza un activo por `Search` y ve su tendencia. |

---

## Página 3 · Evidenciar

| Atributo | Definición |
|---|---|
| **Persona** | Investigador / responsable de validación de campo. |
| **Pregunta** | ¿Qué datos sostienen la señal? |
| **Fuente de datos** | Feature service de observaciones Survey123 **[por publicar]** + capa de activos. |
| **Widgets** | `Map`, `List` de parcelas, `Feature Info` (adjuntos/fotos), `Chart` (impacto vs control), `Survey` o enlace Survey123. |
| **Layout** | Mapa de parcelas a la izquierda; ficha de parcela (Feature Info) a la derecha con fotos y mediciones. |
| **Message/Data actions** | Seleccionar parcela → muestra fotos/mediciones + `is_control`. Botón «Registrar parcela» → Survey123 (prefill de `asset_id`, ver `survey123-integration.md`). |
| **Filtros** | Por `qa_status`, `is_control`, `evidence_class`, activo. |
| **Estado vacío** | **Estado por defecto real hoy:** «Aún no hay observaciones de campo. Las parcelas mostradas están `planned`/`missing`.» (roadmap: 4 parcelas semilla). |
| **Carga/error** | Si el servicio no existe aún: banner «El servicio de observaciones se publica en la Fase 3 del roadmap». |
| **Etiquetas de evidencia** | `missing`/`synthetic` mostrados explícitamente. **Prohibido** cualquier texto de «acuerdo satélite↔campo». |
| **Responsive** | Móvil-primero (uso de campo): ficha de parcela a pantalla completa; mapa colapsable. |
| **Criterios de aceptación** | (a) ninguna parcela `planned` etiquetada como «observada»; (b) `missing` nunca como 0; (c) sin afirmación de validación; (d) ningún resultado de concordancia sin comparación legítima y muestra suficiente. |

---

## Página 4 · Gobernar

| Atributo | Definición |
|---|---|
| **Persona** | Auditor / interlocutor institucional. |
| **Pregunta** | ¿Puede reconstruirse y auditarse la decisión? |
| **Fuente de datos** | Items enlazados (informes, GeoJSON de export), documentación SNTO. |
| **Widgets** | `Text` (metodología, limitaciones, clases de evidencia), `Button` (descargar GeoJSON/GeoPackage/informe), `Embed` (documentación). |
| **Layout** | Documento estructurado: metodología → limitaciones → descargas → proveniencia. |
| **Message/Data actions** | Botones de descarga → items de exportación (una sola vez). |
| **Filtros** | N/A. |
| **Estado vacío** | N/A (contenido estático curado). |
| **Carga/error** | Enlaces rotos → aviso «Recurso no disponible». |
| **Etiquetas de evidencia** | Cautelas metodológicas destacadas; explicación BACI y de las 3 dimensiones de evidencia (ver `data-contract.md` §5). |
| **Responsive** | Desktop-primero; lectura fluida en móvil. |
| **Criterios de aceptación** | (a) las descargas llevan sello `source_version`/fecha; (b) se explica qué es snapshot y qué sería «en vivo»; (c) limitaciones visibles antes que cualquier cifra. |

---

## Objeto transversal · Asset Detail

**[Propuesto]** Se abre desde `Map`/`List` en Diagnosticar/Decidir. Implementable
**íntegramente con widgets estándar** (`Feature Info` + `List` de observaciones
relacionadas + `Text` + parámetros de URL). **[Diferido — brecha widget]:**
ninguna detectada; si en el build se hallara una, se registraría aquí.

Contenido mostrado:

1. Identidad (`asset_id`, `asset_name`, `category`, `stratum`).
2. Geometría / ubicación (mapa embebido centrado).
3. Estado ecológico (`ehs`, o «Sin dato» si null).
4. Tendencia (`trend`, `tau`, `p_value`, IC de Sen) o «Sin serie» si `has_trend=false`.
5. Confianza (`confidence`).
6. Clase de evidencia (`evidence_level`) — badge.
7. Contexto PRUG **[condicionado]**.
8. Estado de validación de campo (`validation_status` derivado) — hoy
   `unvalidated` para casi todo.
9. Observaciones relacionadas (unión por `asset_id` string).
10. Acción de gestión recomendada (`decision_caveat`).
11. Proveniencia y limitaciones (`provenance`, `source_version`, sello de fecha).

**Flujo (ver `data-contract.md` §6/§7 para claves):**
`Map/List (selección)` → `Asset Detail` → `Evidencia (obs. del mismo asset_id)`
→ `observación de campo (fotos/mediciones/is_control)` → `acción / proveniencia /
informe`.

**Criterios de aceptación:** (a) las observaciones se unen por `asset_id` string,
no por `OBJECTID`; (b) los campos null se muestran como «Sin dato»; (c) el estado
de validación no dice «field_verified» sin medición real.
