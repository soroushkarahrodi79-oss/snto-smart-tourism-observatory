# Contrato de integración SNTO (OpenAPI)

[`openapi.json`](openapi.json) es el contrato **OpenAPI 3.1** de la API del SNTO,
generado desde el propio código (`python scripts/export_openapi.py`) y verificado
en CI: si el contrato publicado deja de coincidir con la aplicación, el build
falla. Lo que aquí se documenta es lo que el código implementa.

## ⚠️ Publicar el contrato no significa que la API esté desplegada

La API **no está desplegada** como servicio HTTP. El panel Streamlit consume la
capa de persistencia **en proceso**, no por HTTP. El despliegue de `/api/v2` está
gobernado por [`ADR-012`](../decisions/ADR-012.md), que lo mantiene en espera
hasta que se dispare uno de sus tres supuestos (un consumidor externo concreto,
la captura de campo escribiendo desde fuera del panel, o una separación del
frontend). El runbook de despliegue ya está escrito
([`../runbooks/snto-api-deploy.md`](../runbooks/snto-api-deploy.md)).

Este documento existe justamente para lo anterior: permite **evaluar la
integración antes de decidir desplegar**, sin coste ni superficie de ataque.

## Para qué sirve

Encaja con [`ADR-008`](../decisions/ADR-008.md): SNTO no compite con ArcGIS,
Google Earth Engine, Sentinel Hub, Tableau ni Power BI — se sitúa por encima y se
integra con ellos. Con este contrato, un equipo técnico puede:

- generar un cliente (`openapi-generator`, `datamodel-code-generator`, etc.);
- valorar el encaje con su GIS/BI **sin** acceso al sistema;
- revisar el modelo de datos antes de una prueba de concepto.

## Qué contiene

| Bloque | Qué expone |
|---|---|
| `/api/v2/territories` | Territorios, su resumen y recuentos agregados |
| `/api/v2/managed-assets` | Activos gestionados, observaciones, ciclo de vida, centroide para mapa |
| `/api/v2/alerts` | Alertas por territorio o activo, triaje y recomendaciones |
| `/api/v2/interventions` | Ciclo de vida de intervención con transiciones validadas |
| `/api/v2/…/field-verifications` | Verificaciones de campo (campaña #26) |
| `/api/v2/audit-log` | Rastro de auditoría de toda escritura |
| `/evaluate_asset`, `/ranking`, `/alerts` | Routers sin estado previos a Fase 5 |
| `/health` | Sonda de estado |

## Autenticación

Las **lecturas son abiertas** por diseño (ADR-011). Las **escrituras** están
protegidas por clave de API (`SNTO_API_KEY`) y, además, por el gate de
autorización por territorio (`authz_gate.py`), latente hasta que existan usuarios
reales. Si la API llegara a exponerse, la clave debe fijarse **antes** de la
primera petición: es el punto no negociable del runbook.

## Nota sobre evidencia

Los valores que devuelve la API llevan su **clase de evidencia** cuando existe
(`real` / `calibrated` / `simulated` / `synthetic` / `missing`). Un campo ausente
se serializa como `null`: el sistema declara la ausencia en lugar de rellenarla.
Ninguna respuesta afirma validación de campo — la campaña #26 sigue pendiente.

## Regenerar

```bash
python scripts/export_openapi.py          # actualiza openapi.json
python scripts/export_openapi.py --check  # comprueba que está al día (lo corre CI)
```

Forma parte del flujo de release, junto a `python scripts/sync_readme.py`.
