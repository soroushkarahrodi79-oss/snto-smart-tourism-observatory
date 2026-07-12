# Clases de evidencia y gating de decisión (ADR-004)

## Propósito

Definir el vocabulario canónico de **clases de evidencia** de SNTO y la regla de
**gating**: qué tipo de decisión puede sostener cada clase. Cumple la decisión
[ADR-004](../decisions/ADR-004.md) ("separar evidencia real / calibrada /
sintética / simulada como concepto de primer nivel en datos, UI, informes y
documentación") y su *Next Step* pendiente: *"Definir reglas de producto sobre
qué clases de evidencia pueden respaldar monitorización, priorización,
intervención y reporte público."* Referencia de código:
[`src/platform/evidence.py`](../../src/platform/evidence.py).

**No-negociable:** no se difuminan los niveles de evidencia. Un dato calibrado
no se presenta como observación directa; un escenario simulado no se presenta
como estado real; un dato ausente se declara `null`, nunca se rellena.

## Las cuatro clases (+ ausencia)

| Clase | Etiqueta | Definición |
|---|---|---|
| `real` | 🛰️ Dato satelital real | Observación directa Sentinel-2 L2A / cartografía oficial. |
| `calibrated` | 📐 Dato calibrado por experto | Reconstrucción calibrada con literatura / anomalías AEMET-Copernicus. No es observación directa. |
| `simulated` | 🎛️ Escenario simulado | Escenario / contrafactual del simulador (Pipeline B): un "¿y si?", no el estado actual. |
| `synthetic` | 🧪 Demo sintética | Datos generados para demostrar el sistema. |
| `missing` | — Sin dato | Periodo o activo sin observación válida. Ausencia de evidencia, no una clase. |

## Reconciliación con los ejes existentes

SNTO ya etiquetaba procedencia en dos ejes distintos y legítimos. La clase de
evidencia es el **eje de procedencia canónico**; el módulo reconcilia ambos sin
mezclarlos:

| Clase canónica | `DataStatus` (capa temporal) | `DataType` (metodología) |
|---|---|---|
| `real` | `REAL` | `Observada` |
| `calibrated` | `CALIBRATED` | `Estimada` |
| `simulated` | *(no existe)* | `Simulada` |
| `synthetic` | `SYNTHETIC` | — |
| `missing` | `MISSING` | — |

`DataType.Calculada` (variable determinista derivada de otras) **no** se colapsa
a una sola clase: hereda la clase de sus entradas. Forzar un mapeo difuminaría
la evidencia, así que `from_data_type()` devuelve `None` para ese caso y el
consumidor debe resolverlo desde las entradas reales.

## Matriz de gating (política propuesta)

Regla conservadora por diseño: el modo de fallo que ADR-004 evita es
*sobre-afirmar certeza*. ✅ = la clase puede respaldar ese uso; 🚫 = no.

| Clase | monitoring | prioritization | intervention | public_reporting |
|---|---|---|---|---|
| Dato satelital real (`real`) | ✅ | ✅ | ✅ | ✅ |
| Dato calibrado por experto (`calibrated`) | ✅ | ✅ | 🚫 | 🚫 |
| Escenario simulado (`simulated`) | 🚫 | 🚫 | 🚫 | 🚫 |
| Demo sintética (`synthetic`) | 🚫 | 🚫 | 🚫 | 🚫 |
| Sin dato (`missing`) | 🚫 | 🚫 | 🚫 | 🚫 |

Lectura:

- **`real`** respalda todo, siempre con su nivel de confianza (DCS) explícito.
- **`calibrated`** orienta *dónde mirar* (monitorización, priorización) pero no
  ordena gasto ni se comunica como hecho sin validación de campo previa.
- **`simulated`** solo sirve para explorar escenarios en el simulador; no es
  evidencia del estado del territorio.
- **`synthetic`** solo demuestra el sistema.
- **`missing`** es ausencia de evidencia y no respalda ninguna decisión.

> Esta matriz es una **política institucional propuesta**, abierta a revisión
> del responsable. Vive en código (`gating_matrix()`) para que dashboard,
> informes y exportadores GIS/riesgo apliquen exactamente la misma regla.

## Convención de score EHS (salud vs estrés)

Cuestión relacionada de #10: la inversión de convención entre pipeline y
dashboard **ya está resuelta** y se documenta aquí como referencia canónica.

SNTO usa dos direcciones de score 0–100 que **no deben mezclarse**:

- **Salud (dashboard, TPI, tiers, comunicación):** `0 = crítico`, `100 = sano`.
- **Estrés/degradación (columnas legacy Pipeline A `ehs_spring`, `ehs_summer`,
  `delta_ehs`):** `0 = sin estrés (sano)`, `100 = máxima degradación`.

La conversión oficial es única y vive en
[`src/metrics/semantics.py`](../../src/metrics/semantics.py)
(`health = 100 − stress`), aplicada en el único límite de entrada
[`src/platform/real_trails.py`](../../src/platform/real_trails.py) (con
intercambio `min ↔ max` y cambio de signo del delta). Verificada en
`tests/unit/test_score_semantics.py`. Así una métrica alta significa siempre lo
mismo en todo el sistema.

## Documentos relacionados

- [ADR-004 — Separación de evidencia](../decisions/ADR-004.md)
- [Incertidumbre](uncertainty.md)
- [Posicionamiento científico](scientific-positioning.md)
