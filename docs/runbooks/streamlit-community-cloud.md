# Streamlit Community Cloud: demo pública de solo lectura

Coste cero. Sin Azure, PostgreSQL ni credenciales de Earth Engine.

- App publicada: https://snto-observatory.streamlit.app/
- Informe estático (GitHub Pages): https://soroushkarahrodi79-oss.github.io/snto-smart-tourism-observatory/

## Activar el modo de solo lectura (acción del propietario)

Fusionar el código **no** activa nada: el modo está apagado por defecto.

1. Fusionar el PR en la rama que despliega la app (`main`) y esperar a que la app se reconstruya.
2. https://share.streamlit.io → app `snto-observatory` → **⋮ → Settings → Secrets**.
3. Pegar **en la raíz del TOML** (antes de cualquier `[sección]`; dentro de una sección no se lee), conservando las claves que ya existan:
   ```toml
   SNTO_PUBLIC_DEMO = "true"
   USE_MOCK_DATA = "true"
   ```
4. **Save** y después **⋮ → Reboot app** (la conexión a la base se crea una vez por proceso).
5. No añadir `SNTO_DB_*`, `SNTO_DATABASE_URL`, `SNTO_API_KEY`, `GEE_*` ni `SNTO_TELEMETRY`. No ejecutar migraciones.

Si la app se crea de nuevo: Repository `soroushkarahrodi79-oss/snto-smart-tourism-observatory`, Branch `main`, Main file `app.py`, Python **3.12**.

## Verificación tras activar (obligatoria)

Desde una ventana privada, sin sesión iniciada:

- Arriba aparece **«Public research demo · Read-only»**. Si no aparece, el modo **no** está activo: revisar el nombre de la clave y que esté en la raíz del TOML.
- *Diagnosticar → Diagnóstico espacial*: el mapa se ve.
- *Gobernar → Configuración territorial* y *Metodología y auditoría*: aviso de solo lectura y ningún formulario de escritura.
- *Gobernar → Informes*: las descargas funcionan.
- *Manage app → logs*: sin trazas de excepción.

## Qué garantiza

Dos capas en `src/persistence/session.py`:

1. La conexión se abre en solo lectura (SQLite `PRAGMA query_only`; Postgres `SESSION ... READ ONLY`), de modo que la base rechaza la escritura aunque llegue por una CTE o por un cursor DBAPI directo.
2. Un filtro de sentencias rechaza antes cualquier cosa que no empiece por `SELECT`/`WITH`/`EXPLAIN`/`SHOW`, incluidos `PRAGMA` y `SET`.

Además, las migraciones Alembic se rechazan y la UI oculta tenencia, registro de parcelas, triaje y ciclo de vida.

| Configuración | Resultado |
|---|---|
| Ausente | Apagado (uso local sin cambios) |
| `true`/`1`/`yes`/`on` en entorno o *Secrets* | Solo lectura |
| `true` sin comillas en *Secrets* | Solo lectura |
| Entorno y *Secrets* en desacuerdo | Gana solo lectura |
| Valor no booleano en el entorno | La app no arranca |
| Valor no reconocido o TOML ilegible en *Secrets* | Solo lectura o la app no arranca |
| Clave mal escrita | **Apagado**: por eso la verificación del indicador es obligatoria |

## Límites

- No es un sistema de autenticación. Protege frente a visitantes de la app, no frente a quien puede ejecutar código en el servidor.
- Los scripts ETL de la raíz del repositorio usan `psycopg2` directamente y quedan fuera; la app pública no los ejecuta.
- La telemetría local (`SNTO_TELEMETRY`, apagada por defecto) escribe un fichero, no registros de dominio.
- Si algún día se conecta una base real, usar además un rol de base de datos sin permisos de escritura.
- Accesibilidad pública no es validación científica: contenido sintético/simulado con sus etiquetas; campaña de campo (#26) pendiente.

## Reversión

- Desactivar el modo: quitar `SNTO_PUBLIC_DEMO` de *Secrets* y reiniciar. **No** hacerlo con una base conectada: las escrituras quedarían abiertas a cualquiera.
- Revertir el código: revertir el commit del PR en `main`; la app se reconstruye sola. No hay migraciones ni datos que deshacer.
