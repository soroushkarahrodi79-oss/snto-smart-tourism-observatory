# Despliegue en Streamlit Community Cloud (demo pública de solo lectura)

Coste cero. Sin Azure, PostgreSQL ni credenciales de Earth Engine. Despliega el dashboard completo (`app.py`) en modo **solo lectura** (`SNTO_PUBLIC_DEMO=true`).

## Qué garantiza `SNTO_PUBLIC_DEMO=true`
- La capa de persistencia (`src/persistence/session.py`) rechaza **toda** sentencia que no sea de lectura (INSERT/UPDATE/DELETE/DDL), sea cual sea el origen: UI, servicios, `/api/v2` o migraciones. Cubierto por `tests/persistence/test_public_demo_readonly.py`.
- La UI oculta además los formularios/botones de escritura (tenencia, parcelas de campo, triaje y ciclo de vida) y muestra un aviso.
- El resto no cambia: navegación, mapas, gráficos y etiquetas de evidencia (sintético/simulado/real). Sin él, el uso local es idéntico al anterior.

## Configuración exacta
1. https://share.streamlit.io → iniciar sesión con GitHub → **Create app** → *Deploy a public app from GitHub*.
2. Repository: `soroushkarahrodi79-oss/snto-smart-tourism-observatory` · Branch: `main` · Main file path: `app.py`.
3. **Advanced settings → Python version: 3.12.**
4. **Advanced settings → Secrets** (TOML):
   ```toml
   SNTO_PUBLIC_DEMO = "true"
   USE_MOCK_DATA = "true"
   ```
5. **No** añadir `SNTO_DB_*`, `SNTO_DATABASE_URL`, `SNTO_API_KEY` ni `GEE_*`. No ejecutar migraciones.
6. Deploy. La primera instalación de `requirements.txt` tarda varios minutos.

## Verificación tras desplegar (obligatoria antes de publicar la URL)
- La URL carga y aparece el dashboard (puede mostrar «waking up» si estuvo inactivo).
- *Diagnosticar → Diagnóstico espacial*: el mapa se ve (estilo oscuro CARTO, sin token).
- En *Metodología y auditoría* y *Configuración territorial* aparece «Demo pública de solo lectura» y no hay formularios de escritura.
- No hay trazas de excepción en la app ni en *Manage app → logs*.

## Límites
- El plan gratuito duerme la app por inactividad y tiene límites de recursos no verificados aquí (pico local ≈ 290 MB por sesión).
- El contenido sigue siendo sintético/simulado con sus etiquetas; no hay validación de campo (#26).
