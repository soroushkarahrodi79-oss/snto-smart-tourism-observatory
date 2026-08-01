# Hoja de ruta — demostración ArcGIS de validación de campo SNTO

**Estado verificado (2026-08-01):** el **servicio Survey123** (capa 0 + vista de
formulario + vista de resultados) y la capa de activos `pilot_assets` **están
publicados y verificados por el propietario** (verificación de esquema
autenticada); los ítems y el Web Map **permanecen privados** (acceso anónimo
correctamente bloqueado, `403`/`499`). **Batch A** (endurecimiento) y **Batch B**
(configuración del Web Map) fueron **ejecutados y verificados por el propietario**
en su sesión autenticada; Claude no realizó ninguna mutación en ArcGIS.
La arquitectura de Experience Builder está documentada, pero **la app de
Experience Builder todavía NO se ha creado** (**Batch C preparado pero NO
autorizado ni ejecutado**, puerta `APPROVE EXPERIENCE BUILDER CREATION BATCH C`).

Separación estricta de estados (no confundir):

- **Preparación ArcGIS** — hecha (capa de captura y operación).
- **Captura real de campo** — **NO ejecutada**; no existen observaciones de campo
  reales.
- **Validación científica v2.5 (#26)** — **NO ejecutada**; no hay resultado
  satélite↔campo publicado. Las parcelas de demostración no constituyen
  validación científica.

Pendiente adicional: **QA multiusuario** (el grupo privado tiene por ahora un
único miembro, el propietario) y **continuidad/transferencia de la cuenta
educativa**.

**Ámbito:** demostración controlada sobre PNSG. ArcGIS es la capa de captura y
operación, **no** el motor científico de SNTO, y esto **no** es un despliegue
institucional.

**Objetivo:** cerrar el ciclo `alerta satelital → observación de campo → validación → demostración` sin alterar el núcleo científico de SNTO.

## Documentos canónicos y separación de responsabilidades

- [`../../arcgis/demo/pnsg/README.md`](../../arcgis/demo/pnsg/README.md) —
  paquete fuente reproducible (CSV, GeoJSON y XLSForm).
- [`../integrations/arcgis/experience-builder/README.md`](../integrations/arcgis/experience-builder/README.md)
  — arquitectura y playbook Experience Builder de Fase 2A.
- Este documento — flujo operativo de captura, QA e integración de campo.

Los artefactos locales de `outputs/` no son fuente canónica.

## 1. Resultado que queremos demostrar

Al terminar el piloto debe ser posible:

1. ver en un mapa dos activos prioritarios del PNSG;
2. abrir una ficha de inspección desde el mapa;
3. registrar una parcela de impacto y otra de control, incluso sin cobertura;
4. capturar compactación, cobertura vegetal, erosión, anchura, visitantes y fotografías;
5. exportar las observaciones desde ArcGIS Online;
6. convertirlas al CSV canónico de SNTO;
7. ejecutar `scripts/run_field_validation.py`;
8. generar un informe honesto con matriz de confusión, correlación de Spearman y contraste control–impacto BACI cuando exista muestra suficiente;
9. mostrar el estado del piloto en un dashboard de demostración.

El piloto **no demostrará todavía** validez científica general, causalidad confirmada, capacidad operativa nacional ni autorización de gasto.

## 2. Reglas de seguridad del trabajo

### Núcleo protegido

No se modifican durante el piloto:

- fórmulas EHS, DCS, SCM, TPI o TIS;
- motores de riesgo, tendencias o causalidad;
- datos Sentinel-2 originales;
- `app.py` salvo decisión posterior y revisión específica;
- configuración de producción, Azure, CI/CD o base PostGIS;
- `.env`, credenciales o claves de ArcGIS.

### Superficie permitida

El trabajo se limita inicialmente a:

- `docs/arcgis/` — diseño, instrucciones y registro de decisiones;
- `arcgis/` — plantillas de intercambio, esquemas y archivos de demostración;
- un futuro script nuevo de importación, sin modificar el cargador canónico;
- tests nuevos del adaptador ArcGIS;
- elementos creados dentro de un grupo ArcGIS marcado claramente como `DEMO`.

### Evidencia y lenguaje

- `real`: observación satelital u observación de campo realmente recogida;
- `calibrated`: reconstrucción o parámetro calibrado;
- `simulated`: escenario, nunca estado observado;
- `synthetic`: dato de demostración, nunca decisión real;
- `missing`: ausencia explícita de dato.

Una prueba rellenada desde el escritorio se etiquetará como `synthetic`. Solo una medición tomada en campo puede etiquetarse como `real`.

## 3. Punto de partida verificado

SNTO ya incluye:

- `clean_assets/field_validation/pnsg_field_observations_template.csv`;
- cuatro parcelas semilla: impacto/control en Porrones y El Nevero;
- el esquema `src.validation.field.FieldObservation`;
- validación de rangos y cálculo del índice de degradación;
- importador CSV que conserva valores vacíos como `None`;
- runner `scripts/run_field_validation.py`;
- matriz de confusión satélite↔campo;
- correlación Spearman cuando hay al menos tres pares válidos;
- contraste BACI mediante diferencia de medias y Cliff's delta;
- series Sentinel-2 y tendencias reales para los dos activos piloto.

Por tanto, ArcGIS será una **capa de captura y operación**. No recalculará la ciencia de SNTO.

## 4. ¿Qué hay que instalar?

| Componente | ¿Ahora? | Momento | Motivo |
|---|---:|---|---|
| Navegador actualizado | Sí | Fase 1 | ArcGIS Online, Survey123 web, Dashboards y Experience Builder |
| Survey123 Connect para Windows | Sí, instalado | Fase 3 | Crear y probar el formulario XLSForm con reglas, cálculos y control de versiones |
| Survey123 Field App | Todavía no | Fase 3 | Probar captura online/offline en el móvil |
| ArcGIS Field Maps | Todavía no | Fase 4 | Navegación, mapa offline y tareas de inspección |
| ArcGIS Pro | No | Fuera del MVP | No es necesario para publicar el GeoJSON ni para el formulario |
| Paquete Python `arcgis` | No | Fase 6, opcional | Automatización posterior; la primera integración será por CSV |
| QGIS | No | Opcional | Solo serviría como comprobación independiente de capas |

No se instalará nada hasta comprobar el tipo de usuario, rol y aplicaciones disponibles en la organización ArcGIS.

## 5. Hoja de ruta por fases

## Fase 0 — Aislamiento y control del cambio

**Estado:** completada.

- [x] verificar rama, versión y cambios locales;
- [x] confirmar que existen plantilla y runner de validación;
- [x] comprobar que `arcgis` no está instalado ni es necesario ahora;
- [x] aislar el trabajo ArcGIS del árbol funcional;
- [x] declarar el núcleo científico como superficie protegida;
- [x] documentar fases y puertas de decisión.

**Puerta de salida:** ninguna modificación del núcleo y rama independiente.

## Fase 1 — Cuenta, arquitectura y activos del piloto

### 1.1 Verificación de la cuenta

Comprobar en ArcGIS Online:

- nombre de la organización;
- tipo de usuario: `Creator`, `Professional` o `Professional Plus` recomendado para crear contenido;
- rol: debe permitir crear contenido y publicar capas alojadas;
- acceso visible a Survey123, Field Maps, Dashboards y Experience Builder;
- permiso o prohibición de compartir públicamente;
- créditos disponibles. No hace falta comunicar contraseñas ni tokens.

**Verificación visual — 2026-07-13:**

- organización académica de la Universidad Complutense de Madrid confirmada;
- acceso confirmado a Survey123, Field Maps, Field Maps Designer, Dashboards,
  Experience Builder, Data Pipelines, Hub, QuickCapture, Instant Apps,
  StoryMaps y Map Viewer;
- cuenta con contenido y pertenencia previa a grupos;
- tipo de usuario y rol no visibles en las capturas;
- privilegio para crear grupos privados confirmado por prueba funcional;
- privilegio para publicar capas pendiente de prueba funcional en la Fase 2.

### 1.2 Contenedor de seguridad

Crear un grupo privado:

`SNTO — Validación de campo DEMO`

Convención de nombres:

- prefijo de todos los elementos: `SNTO_DEMO_`;
- descripción obligatoria: `Demostración académica; no usar para decisiones operativas`;
- propietario identificado;
- compartición únicamente con el grupo durante el desarrollo;
- prohibido compartir públicamente hasta superar la Fase 7.

### 1.3 Activos iniciales

Solo dos activos:

| Activo | `asset_id` | Estrato |
|---|---|---|
| Maliciosa–Porrones | `pnsg_escalada_maliciosa_porrones` | escalada–roquedo |
| El Nevero | `pnsg_vuelo_libre_el_nevero` | vuelo libre–pastizal |

Cada activo tendrá una parcela de impacto y una de control. Cuatro registros son suficientes para probar el flujo técnico, pero **no** para validar científicamente el método.

**Puerta de salida:** cuenta apta, grupo privado creado y alcance limitado a dos activos.

**Estado:** superada el 2026-07-13. Grupo privado creado por el propietario del
piloto; la publicación de capas se valida en la siguiente fase.

## Fase 2 — Capas alojadas y mapa web

**Progreso 2026-07-13:** `pilot_assets.geojson` publicado correctamente como
capa de entidades alojada. ArcGIS reconoce la geometría puntual, los atributos
y el campo de fecha. El privilegio de publicación queda confirmado. Pendientes:
desactivar edición, comprobar la compartición privada, configurar la presentación
y guardar el mapa web.

**Cierre de la fase — 2026-07-13:** edición desactivada, protección aplicada,
dos entidades verificadas, simbología por tendencia configurada, mapa guardado
como `SNTO_DEMO_PNSG_FieldValidation_Map` y contenido compartido exclusivamente
con el grupo privado del piloto. La gestión del grupo queda bajo responsabilidad
de su propietario académico.

### 2.1 Capa de activos

Nombre: `SNTO_DEMO_PNSG_Assets`

Campos mínimos:

- `asset_id` — texto, clave estable;
- `asset_name` — texto;
- `stratum` — dominio;
- `trend` — texto;
- `trend_significant` — sí/no;
- `sens_slope` — decimal;
- `confidence` — dominio;
- `evidence_class` — dominio;
- `demo_status` — siempre `DEMO`;
- `source_version` — versión SNTO;
- `calculated_at` — fecha;
- `provenance` — texto.

La capa será de referencia y no editable por el personal de campo.

### 2.2 Capa de observaciones

Nombre: `SNTO_DEMO_PNSG_FieldObservations`

Los nombres canónicos deben mantenerse para que SNTO pueda importarlos:

- `plot_id`;
- `asset_id`;
- `lat`, `lon`;
- `distance_to_trail_m`;
- `is_control`;
- `soil_compaction_mpa`;
- `veg_cover_pct`;
- `erosion_class`;
- `trail_width_m`;
- `visitor_count`;
- `photo_ref`;
- `stratum`;
- `observed_at`.

Campos de gobierno adicionales —ignorados por el cargador actual—:

- `observer`;
- `gps_accuracy_m`;
- `qa_status` — `draft`, `submitted`, `reviewed`, `rejected`;
- `evidence_class` — `synthetic` por defecto en pruebas;
- `notes`;
- editor y fecha de edición de ArcGIS.

### 2.3 Dominios y validaciones

- `is_control`: impacto/control;
- `soil_compaction_mpa`: número ≥ 0;
- `veg_cover_pct`: 0–100;
- `erosion_class`: 0 ninguna, 1 ligera, 2 moderada, 3 severa;
- `trail_width_m`: número ≥ 0;
- `visitor_count`: entero ≥ 0;
- `distance_to_trail_m`: número ≥ 0;
- foto obligatoria en el ensayo final, opcional en pruebas de escritorio;
- `observed_at` obligatorio;
- geometría obligatoria.

### 2.4 Mapa web

Nombre: `SNTO_DEMO_PNSG_FieldValidation_Map`

Capas:

1. activos prioritarios;
2. observaciones impacto;
3. observaciones control;
4. límite PNSG, solo si su licencia y procedencia están documentadas;
5. cartografía contextual no editable.

**Puerta de salida:** mapa privado funcional, simbología inequívoca y edición limitada a observaciones.

## Fase 3 — Survey123

Se usará Survey123 Connect para conservar el XLSForm dentro del repositorio y poder revisar cambios.

**Progreso 2026-07-13:** Survey123 Connect instalado. XLSForm
`arcgis/demo/pnsg/SNTO_DEMO_PNSG_FieldValidation.xlsx` generado con cuatro
parcelas controladas, coordenadas y precisión GPS calculadas, rangos de calidad,
fotografías y clasificación explícita de evidencia. El esquema se ha alineado
con las catorce columnas canónicas de `src.validation.io`. Pendiente: importar
en Connect, analizar la encuesta, probar una captura sintética y publicar solo
en el grupo privado.

### Formulario

- selección del activo mediante lista controlada;
- generación o validación de `plot_id`;
- selección impacto/control;
- posición GPS y precisión;
- mediciones con unidades visibles;
- reglas de rango;
- campos obligatorios condicionados;
- fotografía y notas;
- aviso permanente de que es una demostración;
- cálculo visual preliminar opcional, sin sustituir el cálculo canónico de SNTO;
- modo offline.

### Pruebas

1. envío desde navegador con `evidence_class=synthetic`;
2. envío desde móvil online;
3. envío desde móvil offline y sincronización posterior;
4. edición de borrador;
5. rechazo de valores fuera de rango;
6. exportación CSV y comprobación de nombres de columnas.

**Puerta de salida:** los datos exportados pueden transformarse sin pérdida al esquema `FieldObservation`.

## Fase 4 — Field Maps y tareas

- activar el mapa para Field Maps;
- preparar área offline del piloto;
- mostrar activos como referencia y observaciones como editables;
- crear cuatro tareas de demostración;
- asignar responsable de prueba;
- comprobar navegación, adjuntos y sincronización;
- impedir la edición accidental de resultados satelitales.

**Puerta de salida:** una inspección puede completarse de principio a fin sin conexión.

## Fase 5 — Experience Builder

La arquitectura aprobada se mantiene en el
[paquete de Fase 2A](../integrations/arcgis/experience-builder/README.md). Este
roadmap gobierna la captura Survey123/Field Maps; el paquete de Fase 2A gobierna
la presentación map-centric, las páginas
Decidir/Diagnosticar/Evidenciar/Gobernar y Asset Detail.

El Dashboard queda diferido. Ninguna vista puede afirmar “método validado”,
campaña completada o acuerdo satélite↔campo sin datos reales, QA y muestra
suficiente.

**Puerta de salida:** app privada, comprensible, auditada con el checklist de
Fase 2A y sin duplicar el tablero Streamlit.

## Fase 6 — Integración con SNTO

La primera integración será deliberadamente simple:

1. exportar CSV desde ArcGIS;
2. conservar el archivo original como entrada inmutable;
3. ejecutar un script nuevo `scripts/import_arcgis_field_observations.py`;
4. normalizar fechas, booleanos, adjuntos y nombres;
5. escribir `clean_assets/field_validation/pnsg_field_observations.csv`;
6. validar contra `FieldObservation`;
7. ejecutar:

   ```powershell
   python scripts/run_field_validation.py `
     --park pnsg `
     --observations clean_assets/field_validation/pnsg_field_observations.csv
   ```

8. revisar el informe generado.

Solo después de que el flujo manual sea estable se evaluará ArcGIS API for Python. Si se incorpora, será una dependencia opcional y separada; no se añadirá de forma automática a `requirements.txt`.

**Puerta de salida:** la importación es reproducible, probada y no modifica los algoritmos científicos.

## Fase 7 — Ensayo completo y cierre

- limpiar datos sintéticos o mantenerlos en una vista separada;
- registrar una demostración completa;
- verificar permisos y ausencia de secretos;
- revisar metadatos, fuentes, licencias y atribuciones;
- generar informe SNTO;
- documentar limitaciones y tamaño muestral;
- preparar capturas y guion de presentación;
- decidir si el grupo sigue privado o se publica una vista expresamente aprobada.

**Definition of Done:** flujo repetible, trazable y reversible; sin cambios en fórmulas madre; evidencia sintética y real claramente separadas.

## 6. Estrategia de pruebas

- tests unitarios para la normalización ArcGIS→SNTO;
- fixture CSV exportado de ArcGIS sin datos personales;
- prueba de valores vacíos (`None`, nunca cero inventado);
- prueba de fechas y booleanos;
- prueba de columnas adicionales;
- prueba de duplicados por `plot_id`;
- prueba de coordenadas ausentes;
- ejecución del runner en modo campaña pendiente;
- ejecución con datos sintéticos marcados como tales;
- ninguna afirmación de validación científica basada en datos sintéticos.

## 7. Reversión

Si el piloto se descarta:

1. no se fusiona la rama;
2. se eliminan o archivan los elementos `SNTO_DEMO_` en ArcGIS;
3. no se altera `main`;
4. los datos de producción permanecen intactos;
5. el núcleo de SNTO continúa funcionando sin ninguna dependencia de ArcGIS.

## 8. Próxima acción necesaria

1. Revisar y versionar el paquete fuente canónico de
   [`../../arcgis/demo/pnsg/`](../../arcgis/demo/pnsg/).
2. Confirmar propietario actual y de continuidad, tipo de usuario, rol,
   transferibilidad y caducidad de la cuenta educativa.
3. Importar y analizar el XLSForm en Survey123 Connect.
4. Ejecutar solo una prueba `synthetic` controlada.
5. Publicar el servicio, si se aprueba, exclusivamente en el grupo privado.

No se ha completado una campaña de campo. No compartir contraseña, token, clave
ni archivo de credenciales.
