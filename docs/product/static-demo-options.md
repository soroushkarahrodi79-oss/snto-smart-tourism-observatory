# Alternativas de demostración sin coste recurrente (post-suspensión de Azure)

> Estado: 2026-11. El despliegue Azure está **suspendido por el propietario**; no hay dashboard público. Esto es un hecho operativo, **no** un fallo científico: código, pruebas, datos derivados versionados, metodología y DOI siguen intactos.

## 1. Qué depende de qué

| Componente | ¿Necesita Azure / PostgreSQL / red? |
|---|---|
| `app.py` (Streamlit, 4 capas) | **No.** `USE_MOCK_DATA=true`; la persistencia cae a SQLite (`src/config/settings.py`). Verificado: `AppTest` sin excepciones y `/_stcore/health` OK en local. |
| Tendencias Sentinel-2 (`clean_assets/timeseries/*`) | **No.** Datos derivados versionados en el repo. |
| Pruebas / CI (`ci.yml`) | **No** (independiente de Azure). |
| Validación de campo (#26): plantilla, runner de concordancia | **No** (offline). La campaña física sigue pendiente. |
| Regenerar series desde Sentinel-2 | **Sí**: Google Earth Engine (cuenta + red). No es Azure, pero tampoco es offline. |
| `deploy-azure-container-apps.yml`, `deploy/azure-bootstrap.sh`, ACR | **Sí** — única parte Azure. Ahora solo `workflow_dispatch`. |
| PostgreSQL `snto-db` en Azure | Solo producción histórica; ningún flujo local lo requiere. |
| Visual Change Explorer (imágenes S2 en vivo) | Sí, GEE; degrada sin ello. |

## 2. Comparación

| Criterio | A. Local | B. GitHub Pages (visor) | C. Informe HTML autónomo | D. HF Spaces / Streamlit Cloud |
|---|---|---|---|---|
| Compatibilidad con la arquitectura | Total | Parcial (reescribir front) | Alta (reutiliza `satellite_trends`) | Total, pero hosting nuevo |
| Backend/PostgreSQL | No | No | No | No (mock) |
| Coste recurrente | 0 | 0 | 0 | 0 nominal; tier gratuito con *sleep* y límites |
| Mantenimiento | Mínimo | Medio (front propio) | **Mínimo** (1 script, `--check`) | Medio (otra plataforma que vigilar) |
| Acceso público | No | Sí | Sí (si se publica en Pages, o descargable) | Sí |
| Reproducibilidad científica | Alta | Media | **Alta** (determinista, sin red) | Media |
| Limitación | Requiere instalar | Reconstrucción de front: **no** ahora | Solo evidencia L2; no interactivo | Dependencia de terceros; ya hubo un coste «≈0» que no lo fue |

**Recomendación: C (informe estático autónomo), publicable luego vía B sin cambios** (es un único `site/index.html` sin dependencias; ver procedimiento en §6), más A como vía de reproducción. D se descarta de momento: añade una dependencia de plataforma para mostrar lo mismo.

## 3. Prototipo incluido

`python scripts/build_static_report.py` → `site/index.html` (~20 KB, 0 peticiones externas, desktop y móvil comprobados). Muestra las tendencias NDVI de 21 activos del PNSG con fechas, fuente, límites y atribución Copernicus. **No** incluye alertas, presupuestos, simulaciones, proyecciones ni datos sintéticos. **No se publica automáticamente**; `--check` detecta desfase.

## 4. Límites explícitos

- Evidencia derivada (L2), sin presión de visitantes, sin causalidad, sin validación de campo.
- El croquis usa un punto representativo (media de vértices) por activo; no es cartografía.
- Los p-valores no están corregidos por comparaciones múltiples.

## 5. Facturación residual — NO verificada (sin acceso a Azure desde esta sesión)

Detener la app **no** garantiza coste cero. Comprobar en Azure Portal (solo lectura):
1. **Cost Management → Cost analysis**, agrupar por *Resource* los últimos 30 días.
2. **Azure Database for PostgreSQL `snto-db`**: un Flexible Server *parado* se reinicia solo a los 7 días, y el almacenamiento se factura aunque esté parado.
3. **Container Registry `acrsnto1781009309`**: SKU Basic factura a diario.
4. Container App `snto-observatory` (revisiones/réplicas mínimas), Log Analytics workspace, Key Vault, IP pública / VNet si existieran.
5. **Suscripción**: crédito de Azure for Students y fecha de caducidad; configurar un *Budget* con alerta.
6. Decidir con criterio propio si exportar y eliminar recursos; esta misión no borra nada.

## 6. Próximos pasos (sin coste)

1. Revisar y fusionar esta PR (manual).
2. Ejecutar la comprobación de facturación de §5.
3. **URL pública vía GitHub Pages (workflow `.github/workflows/pages.yml`, sin coste).** El propietario activa Pages **una sola vez**: *Settings → Pages → Build and deployment → Source: **GitHub Actions***. Después, cada merge a `main` que toque el informe (`site/`, su generador o sus datos de entrada) ejecuta `validate` (`build_static_report.py --check` + `tests/unit/test_static_report.py`) y, solo si pasa, `deploy` publica **únicamente** `site/`. Las PR ejecutan `validate` pero nunca publican; `deploy` solo corre en `main`. URL esperada: `https://soroushkarahrodi79-oss.github.io/snto-smart-tourism-observatory/` (a verificar tras el primer despliegue; no se asume). Primer despliegue sin cambios en `site/`: *Actions → Pages → Run workflow* (rama `main`). Para retirarlo: *Settings → Pages → Unpublish*. Los repositorios privados requieren un plan de pago; este es público.
   - La publicación solo muestra evidencia derivada L2 (ver §4): no hay alertas, presupuestos ni simulaciones.
   - Alternativa manual previa (rama `gh-pages`) ya **no** es necesaria.
4. Campaña de campo #26 (independiente de todo lo anterior).
