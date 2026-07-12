# Validation

## Purpose
Define the validation gap that must be closed before SNTO can be treated as operationally authoritative.

## Background
The review board identified validation as the largest scientific weakness.

## Current State
SNTO has validation scaffolding and code tests, but scientific validation requires independent empirical evidence.

### Campaña de validación de campo — estado (issue #26)

La **infraestructura** para la primera campaña está completa y ejecutable; la
**verdad-terreno todavía no se ha recogido**, así que **no se afirma ninguna
validación** (no-negotiable: no sobre-afirmar validez).

Listo:

- Protocolo de muestreo control–impacto (BACI): `docs/field_validation_protocol.md`.
- Esquema de observación y índice de degradación de campo: `src/validation/field.py`.
- Métricas de concordancia continua (Spearman) y contraste BACI (Cliff's δ):
  `src/validation/agreement.py`.
- **Matriz de confusión** satélite↔campo (clase positiva = alerta/degradado) con
  exactitud, precisión, sensibilidad, F1 y **Cohen's κ**: `src/validation/confusion.py`.
- Registro de campo en CSV (plantilla + carga):
  `clean_assets/field_validation/pnsg_field_observations_template.csv`,
  `src/validation/io.py`.
- Ejecutor de campaña: `scripts/run_field_validation.py`
  (`--init` genera la plantilla; sin `--init` produce el informe de contraste).

**Activos prioritarios** (los dos del PNSG con tendencia NDVI significativa,
sembrados en la plantilla):

| Activo | Categoría | Tendencia satelital | Expectativa de campo |
|---|---|---|---|
| Escalada Maliciosa-Porrones | escalada | ↓ decreciente (τ=−0.37, p≈0) → **alerta** | degradación esperada en el corredor |
| Vuelo libre El Nevero | vuelo libre | ↑ creciente (τ=+0.23, p≈0.01) → recuperación | sin degradación esperada |

Pendiente (requiere trabajo de campo, no automatizable): recoger las parcelas
impacto/control con penetrómetro, cobertura y erosión; ejecutar el informe;
consignar la matriz de confusión resultante y sus límites aquí.

## Evidence
The scientific review asked for field observations, control sites, visitor-use data, soil/erosion/vegetation measures, cross-sensor validation, temporal replication, and external protected-area replication.

## Recommendations
Validation should include:
- field plots;
- control-impact design;
- ranger/ecologist verification;
- visitor-count correlation;
- false-positive and false-negative analysis;
- habitat-stratified calibration;
- external protected-area pilots.

## Next Steps
Execute validation before making strong operational or scientific claims.

## Related Documents
- [Future Validation](future-validation.md)
- [Scientific Review Board](../reviews/2026/03-scientific-review-board.md)

