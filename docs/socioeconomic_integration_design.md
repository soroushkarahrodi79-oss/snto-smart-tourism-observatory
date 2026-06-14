# Integración socioeconómica ALMUDENA / INE — diseño (F9)

> **Propósito.** Dotar al observatorio de una **capa socioeconómica real** a nivel
> municipal y cruzarla con el riesgo ambiental de los activos (EHS / SCM / Tier)
> para responder a una pregunta que hoy no se puede contestar: *¿qué comunidades
> locales están más expuestas económicamente a la degradación de sus activos
> naturales?* Esta fase sustituye los proxies expertos actuales
> (`economic_importance` 0–1 y el KPI "Empleos locales en riesgo" con números
> mágicos en `app.py`) por indicadores anclados en **INE** y **ALMUDENA**.

---

## 0. Decisiones aprobadas (gate Fase 2)

| Decisión | Elección |
|---|---|
| Territorio inicial | **PNSG** (principal y más rico en datos) |
| Adquisición de datos | **Snapshot curado versionado** en repo (offline, reproducible); API en vivo como mejora futura |
| Profundidad de indicador | **SVI compuesto completo** + métrica de impacto en comunidad, con tests |

---

## 1. Grano de análisis y clave de cruce

- El riesgo vive a nivel de **activo** (`TerritorialAsset`); el dato socioeconómico
  vive a nivel de **municipio**.
- Clave de cruce canónica: **código INE de municipio (5 dígitos)**, NO el string
  del nombre (frágil ante acentos/variantes "Manzanares el Real" vs "Manzanares El Real").
- Cada `TerritorialAsset.region` (nombre) se mapea a su código INE mediante una
  tabla explícita.

### Municipios PNSG — IMPLEMENTADO (34 municipios, crosswalk-driven)

La ingesta usa la tabla de correspondencia oficial
(`processed/tabla_correspondencia_municipios_pnsg.csv`) como fuente de verdad de
los **34 municipios** del PNSG (15 Madrid + 19 Segovia; se omite "Los Baldíos",
entidad sin código INE municipal). Los códigos INE de la tabla son consistentes
con el padrón y los límites geojson (p. ej. Cercedilla = 28038, Rascafría = 28120,
Manzanares el Real = 28082). Los 4 municipios con activos hoy
(Rascafría, Cercedilla, Navacerrada, Manzanares el Real) resuelven vía
`region_to_ine`.

> ALMUDENA cubre solo Madrid (15 municipios → `completeness=FULL`). El **lado de
> Segovia** (19 municipios) queda `DEMOGRAPHIC_ONLY`: solo padrón INE.

---

## 2. Fuentes y cobertura

| Fuente | Cobertura | Indicadores que se extraen |
|---|---|---|
| **INE** (backbone universal) | Toda España | Padrón (población, densidad, **% ≥65 envejecimiento**, variación interanual = despoblación); EOATR (plazas y pernoctaciones en alojamientos de turismo rural); DIRCE (nº de empresas); Atlas de Renta (renta media por persona/hogar); paro registrado |
| **ALMUDENA** (enriquecimiento Madrid) | Solo municipios de Madrid (28) | Banco municipal más granular/actualizado (paro registrado, actividad económica, establecimientos turísticos, renta) + capas espaciales (límites municipales) |
| **OAPN — Área de Influencia Socioeconómica** (opcional) | Red de PN | Lista legal de municipios del AIS del parque (autoridad para definir "comunidad local") |

Prioridad: **INE primero** (homogéneo y universal); **ALMUDENA** sobreescribe/enriquece
los municipios de Madrid donde aporte más detalle o frescura.

---

## 3. SVI — Socioeconomic Vulnerability Index (0–100 por municipio)

Sigue la convención de acrónimos del observatorio (EHS, SCM, DCS, TPI, TIS). Tres
componentes normalizados a [0, 1] y combinados con pesos expertos declarados:

```
SVI = 100 · ( w_dep · DEP  +  w_dem · DEM  +  w_exp · EXP )
```

| Componente | Símbolo | Significado | Insumos |
|---|---|---|---|
| Dependencia turística | DEP | Cuánto pesa el turismo natural en la economía local | EOATR (plazas rurales / población), DIRCE (densidad empresarial) |
| Fragilidad demográfica | DEM | Vulnerabilidad estructural de la población | Despoblación (variación padrón 5y) + envejecimiento (% ≥65) |
| Exposición al riesgo ambiental | EXP | Estado de los activos del municipio | Agregación de los activos del municipio: media de (100−EHS), share de SCM `LOCALIZED_IMPACT`, share de activos Tier 1–2 |

Pesos iniciales propuestos (revisables, banda de sensibilidad como en `src/analysis/sensitivity.py`):
`w_dep = 0.40`, `w_dem = 0.30`, `w_exp = 0.30`.

> EXP reutiliza salidas ya existentes del observatorio (EHS, `scm_classification`,
> `tier`), de modo que el SVI **conecta** las dos mitades del sistema en vez de
> introducir una métrica paralela.

### Métrica de cruce para el dashboard — Impacto en la comunidad

```
CommunityImpact(municipio) = riesgo_ambiental_activos × dependencia_económica
```

Convierte el KPI "Empleos locales en riesgo" (hoy `_jobs_per=2500`, `_spend=22.50`
hardcodeados en `app.py:1025`) en una estimación **respaldada por datos**: empleo
turístico real (EOATR/DIRCE) × capacidad de visitantes en riesgo (Tier 1–2).

---

## 4. Modelo de datos e integración

No se ensucia `TerritorialAsset`. Capa nueva, desacoplada:

```
src/socioeconomic/
├── __init__.py
├── models.py        # dataclass Municipality (keyed por código INE)
├── loader.py        # lee el snapshot curado → dict[ine_code, Municipality]
├── mapping.py       # region (nombre) → código INE
├── indicators.py    # SVI + CommunityImpact (funciones puras, testadas)
└── snapshot/        # SNAPSHOT VERSIONADO (config, no bulk data — se envía en la imagen)
    ├── municipalities.json
    └── pnsg_tourism_zone.json

etl_socioeconomic.py # ETL raíz (patrón de etl_oapn_wfs.py / etl_tourist_traffic.py):
                     #   crosswalk + ALMUDENA + padrón + EOATR → normaliza →
                     #   src/socioeconomic/snapshot/municipalities.json

tests/unit/test_socioeconomic.py                        # SVI, mapping, loader
```

### Esquema de `municipalities.json` (snapshot curado)

```json
{
  "schema_version": "1.0",
  "source_snapshot_date": "2026-06",
  "municipalities": {
    "28120": {
      "name": "Rascafría", "province": "Madrid", "ine_code": "28120",
      "population": 0, "pop_change_5y_pct": 0.0, "pct_over_65": 0.0,
      "rural_tourism_beds": 0, "businesses_total": 0, "income_per_capita_eur": 0,
      "unemployment_rate_pct": 0.0,
      "provenance": {"population": "INE Padrón 2024", "income_per_capita_eur": "INE ADRH 2022", "...": "..."}
    }
  }
}
```

Cada campo lleva su **procedencia** (fuente + año), que el dashboard mostrará vía
`src/platform/provenance.py`.

---

## 5. Superficie en el dashboard

- **Sustituir** el KPI heurístico "Empleos locales en riesgo" por la estimación
  basada en INE (empleo turístico × capacidad en riesgo).
- **Nuevo panel "Comunidades locales en riesgo"**: municipios ordenados por
  `CommunityImpact`, mostrando SVI y sus componentes.
- Etiquetas de **procedencia** (INE/ALMUDENA + año) por indicador, con énfasis en
  la vista **Auditoría científica** (`ConfidenceDetail.FULL`).

---

## 6. Honestidad / límites (declarados desde el día 1)

- **Mapeo nombre→código INE explícito** y validado en la ETL (evita falsos cruces).
- **Secreto estadístico** en municipios diminutos (La Hiruela, Madarcos ~50 hab):
  INE suprime variables; se marca `null` + caveat, no se inventa.
- **Lado de Segovia** del PNSG: solo INE (ALMUDENA no cubre Castilla y León).
- **Desfase temporal**: Censo/Atlas de Renta (2021/22) vs satélite (2025/26). El SVI
  es **contexto de enriquecimiento**, no una afirmación causal sobre la economía.
- Snapshot **versionado y fechado**; la actualización es un re-run consciente de la ETL.

---

## 7. Fases de implementación — ESTADO: COMPLETADO

1. ✅ **Registro municipal + mapping INE** — `src/socioeconomic/models.py`,
   `mapping.py` (crosswalk + normalización de nombres INE "Molinos (Los)" etc.).
2. ✅ **Curado del snapshot** — `etl_socioeconomic.py` parsea crosswalk + 15 fichas
   ALMUDENA + padrón 2881/2894 + EOATR zona PNSG → `src/socioeconomic/snapshot/
   municipalities.json` (34 municipios, 15 FULL + 19 DEMOGRAPHIC_ONLY) y
   `pnsg_tourism_zone.json`. Procedencia por campo + caveats. **Va dentro de `src/`**
   (no en `data/`) porque `data/` está git-ignored y docker-ignored; así el snapshot
   llega a CI y a la imagen de Azure.
3. ✅ **Indicadores** — `src/socioeconomic/indicators.py`: SVI (DEP/DEM/EXP con
   pesos renormalizados), CommunityImpact y JobsAtRisk. `loader.py` con caché.
   Tests: `tests/unit/test_socioeconomic.py` (20 casos; suite total 474 verde).
4. ✅ **Cableado en dashboard** — KPI superior "Empleos locales en riesgo" respaldado
   por datos reales; pestaña *Impacto socioecon.* con sección "Datos reales",
   KPIs de comunidad, tabla "Comunidades locales en riesgo" y procedencia/límites
   en la vista Auditoría. El modelo proxy heredado se conserva, re-etiquetado.

### Notas de realidad del dato (vs diseño inicial)
- **EOATR es de zona turística**, no municipal → se guarda como contexto de
  territorio (`pnsg_tourism_zone.json`), no entra en el SVI municipal.
- **Envejecimiento** solo disponible vía ALMUDENA (Madrid); en Segovia el DEM se
  calcula solo con despoblación del padrón.
- **Encodings INE mixtos** (padrón 2881 = cp1252, 2894 = utf-8-sig): lectura robusta.

### Pendiente / mejoras futuras
- Datos de turismo municipal para Segovia (SIE Castilla y León) para SVI completo allí.
- Capa espacial: coropleta municipal usando `municipios_pnsg_34.geojson`.
- API en vivo INE (Tempus3 JSON) como alternativa al snapshot curado.
