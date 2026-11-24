# Streamlit Community Cloud — viabilidad (informe, no despliegue)

> Estado: investigación independiente; **no se ha desplegado nada** ni existe URL. No bloquea la publicación estática (GitHub Pages, ver `static-demo-options.md`).

## Verificado (local, Windows, Python 3.12, entorno limpio desde `requirements.txt`)

| Aspecto | Resultado |
|---|---|
| Resolución de dependencias | OK. El resolutor instala `streamlit 1.56.0` (no la última de PyPI, 1.67.0, por las restricciones del repo, p. ej. `starlette<0.38`). |
| Arranque | `streamlit run app.py` sirve `/_stcore/health` = `ok`; `AppTest` sin excepciones (≈7–15 s en frío). |
| Memoria | Pico ≈ 290 MB de working set por sesión de `AppTest` (3 ejecuciones). No se midió bajo carga concurrente. |
| Datos | Repo ≈ 14 MB rastreados; los datasets que usa la app están versionados. Sin Azure, PostgreSQL ni credenciales de Earth Engine (`USE_MOCK_DATA=true` por defecto). |
| `use_container_width` (45 usos) | Solo emite *deprecation warnings* en 1.56.0; **no hay incompatibilidad demostrada**, por lo que no se tocan. |

## No verificado
- Instalación en Linux de Streamlit Cloud (solo CI de GitHub en Ubuntu 3.12 respalda que `requirements.txt` instala allí).
- Límites de recursos vigentes del plan gratuito, tiempo de *sleep*, concurrencia.
- Comportamiento con versiones de Streamlit posteriores a 1.56 si se relajaran las restricciones.

## Superficies de escritura (verificado empíricamente)
La app incluye formularios/botones que escriben en persistencia: alta de organizaciones/usuarios/territorios (`tab_config.py`), registro de parcela de campo (`tab_method.py`) y triaje/avance de activos (`tab_urgent_actions.py`).

En un clon limpio la base SQLite no tiene tablas (nadie ejecuta `alembic`), por lo que **todas las escrituras fallan con `OperationalError` y la UI lo informa**; no se crea ninguna tabla. Esta propiedad es **accidental, no una puerta de acceso**:
- **No** configurar secretos `SNTO_DB_*` / `SNTO_DATABASE_URL` en Streamlit Cloud: con una base real las escrituras quedarían abiertas a cualquier visitante (no hay login; `SNTO_API_KEY` solo protege `/api/v2`).
- No ejecutar migraciones en ese despliegue.
- Un modo «solo lectura» explícito sería la defensa correcta si algún día se conecta una base; no se implementa aquí por no ser necesario hoy.

## Veredicto: MODIFY (viable, con condiciones)
Técnicamente arranca y es ligera. Condiciones antes de publicarla: Python 3.12 en *Advanced settings*, sin secretos de base de datos, archivo principal `app.py`, y comprobar la URL real tras el despliegue. La app sigue mostrando contenido sintético/simulado con sus etiquetas de evidencia; publicarla no cambia ningún límite científico (sin validación de campo, #26).
