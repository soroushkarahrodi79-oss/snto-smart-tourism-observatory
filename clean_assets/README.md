# `clean_assets/` — Artefactos de evidencia versionados

**Decisión de convención (v1.1.0):** este directorio contiene datos **derivados**
que se versionan **a propósito** en el repositorio. No son datos crudos ni
secretos; son la evidencia reproducible que sostiene la capa temporal de v1.1.0.

## Por qué se versionan (y no se `.gitignore`)

- **El despliegue no puede regenerarlos.** La cadena de generación depende de
  **Google Earth Engine** (requiere autenticación `earthengine`/`ee`), que no
  está disponible ni en CI ni en el contenedor de Azure Container Apps.
- **Degradación silenciosa.** `src/platform/satellite_trends.py` cae a
  `TrendSummary(available=False)` si falta el JSON, y el panel del dashboard está
  condicionado a `if _real_trends.available`. Sin estos ficheros, **la capa
  satelital real de v1.1.0 desaparece del dashboard desplegado**.
- **Transparencia científica.** Versionar la evidencia derivada hace el repo
  autocontenido y auditable (no-negociable del proyecto). El CSV incluye columna
  `data_source` (`GEE:S2_SR_HARMONIZED`) que marca la procedencia.
- **Tamaño despreciable.** ~306 KB en total (geojson 34 KB · csv 258 KB · json 14 KB).

## Contenido

| Fichero | Qué es | Generado por |
|---|---|---|
| `pnsg_assets.geojson` | 21 activos reales del PNSG (geometrías, EPSG:4326) | `scripts/build_pnsg_assets.py` |
| `pnsg_assets.py` | Mismo set como lista Python importable | `scripts/build_pnsg_assets.py` |
| `timeseries/pnsg_gee_timeseries.csv` | Serie NDVI/NDMI/EVI mensual Sentinel-2 (2021–jun 2026) | GEE Code Editor (export) |
| `timeseries/analysis/mk_trends_pnsg.json` | Tendencias Mann-Kendall por activo | `scripts/run_timeseries_analysis.py` |
| `timeseries/pn_tablas_daimiel_gee_timeseries.csv` | Piloto OAPN v1.2.0 — humedal, serie mensual (5 activos) | GEE Code Editor (export, `gee_templates_oapn/pn_tablas_daimiel.js`) |
| `timeseries/analysis/mk_trends_pn_tablas_daimiel.json` | Tendencias Mann-Kendall del piloto Tablas de Daimiel | `scripts/run_timeseries_analysis.py --park pn_tablas_daimiel` |
| `timeseries/pn_monfrague_gee_timeseries.csv` | Piloto OAPN v1.2.0 — dehesa, serie mensual (21 activos) | GEE Code Editor (export, `gee_templates_oapn/pn_monfrague.js`) |
| `timeseries/analysis/mk_trends_pn_monfrague.json` | Tendencias Mann-Kendall del piloto Monfragüe | `scripts/run_timeseries_analysis.py --park pn_monfrague` |

## ✅ Alcance estadístico del Mann-Kendall (corregido en v1.1.1)

El Mann-Kendall de `mk_trends_pnsg.json` se calcula sobre la serie NDVI mensual
**desestacionalizada** (descomposición armónica de 2 componentes, Julien &
Sobrino 2009), con **corrección de empates** en la varianza (Hipel & McLeod
1994) y **pendiente de Sen con intervalo de confianza no paramétrico** (Gilbert
1987). Los 7 veredictos significativos superan además una prueba de robustez de
*pre-whitening* libre de tendencia (Yue-Pilon 2002) sin ningún cambio de
dirección: la autocorrelación serial no explica las tendencias detectadas.
Implementación: `src/time_series/{decomposition,mann_kendall,prewhitening,confidence}.py`,
orquestada por `scripts/run_timeseries_analysis.py` (flag `--prewhiten` para la
comprobación de robustez). Detalle completo en
`docs/nota_metodologica_temporalidad.md`.

**v1.1.1 también corrigió un bug de orden cronológico** en
`scripts/run_timeseries_analysis.py`: `year`/`month` llegaban del CSV como
texto y se ordenaban lexicográficamente ("10","11" antes que "2"), corrompiendo
la serie mensual de los 21 activos en el análisis de v1.1.0. El bug estaba
presente en el release público de v1.1.0; el resultado corregido —recalculado
tras arreglar el orden y desestacionalizar— es el que contiene este JSON.

*(Nota histórica: en v1.1.0 el test corría sobre la serie cruda sin
desestacionalizar ni corregir autocorrelación, y se etiquetaba como
preliminar/indicativo. Ese estado ya no aplica.)*

## Cómo regenerar

```bash
# 1. Extraer los 21 activos reales desde los shapefiles PRUG → geojson (fuente única)
python scripts/build_pnsg_assets.py

# 2. Embeber el geojson en un script JS para el GEE Code Editor
python scripts/build_gee_js.py            # → scripts/gee_code_editor_pnsg.js

# 3. Ejecutar ese JS en code.earthengine.google.com (requiere auth GEE)
#    → exporta el CSV a Drive → colocar en clean_assets/timeseries/pnsg_gee_timeseries.csv

# 4. Calcular las tendencias Mann-Kendall a partir del CSV
python scripts/run_timeseries_analysis.py # → timeseries/analysis/mk_trends_pnsg.json
```

El paso 3 es el único que exige credenciales de Earth Engine; los demás son
deterministas y offline.

## Precedente para v1.2.0

Los pipelines OAPN de v1.2.0 (expansión de red multi-parque) deben seguir esta
misma convención: **salidas derivadas versionadas bajo `clean_assets/`**, con
procedencia etiquetada y su cadena de regeneración documentada aquí.
