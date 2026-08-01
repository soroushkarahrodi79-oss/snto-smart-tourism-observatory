# Especificación del nuevo item Experience Builder

> El item **no existe** (`DOES_NOT_EXIST — OWNER_UI_VERIFIED`). Esta es la
> especificación para crearlo; la creación **no está autorizada** aún.

| Atributo | Valor propuesto |
|---|---|
| Título | `SNTO · Espacio de decisión PNSG — DEMO académico` |
| Tipo | ArcGIS Experience Builder — Web Experience |
| Prefijo/gobernanza | `SNTO_DEMO_`; descripción obligatoria «Demostración académica; no usar para decisiones operativas» |
| Audiencia | **solo el grupo privado académico** |
| Propiedad | owner actual inicialmente, con plan documentado de transferencia/continuidad |
| Fuente de datos primaria | **el Web Map existente** |
| Fuentes secundarias (solo donde se requiera) | Survey123 **results view**; capa `pilot_assets` |
| Item ID | pendiente tras creación (solo en registro local ignorado) |

## Reglas duras

- **No crear capas alojadas duplicadas.** Reutilizar el Web Map y las capas
  existentes. Ninguna publicación de nuevos Hosted Feature Layers.
- **No** usar el **form view** como fuente de visualización de evidencia por
  defecto (es para captura). La evidencia se muestra con el **results view**.
- La creación de la app **no** concede automáticamente acceso a las fuentes de
  datos: cada dependencia debe compartirse consistentemente (ver
  `sharing-and-security.md`).
- Sin herramientas de análisis, geocoding, routing ni servicios premium (ver
  `qa-and-acceptance.md` y el apartado de créditos).

## Estructura de páginas

5 páginas / vistas: **Decidir, Diagnosticar, Evidenciar, Gobernar** + panel
transversal **Asset Detail** (detalle ver `page-architecture.md`). Reutiliza la
gramática de 4 capas de SNTO (`src/ui/navigation.py`) re-expresada en clave
map-centric.

## Tema

Paleta institucional SNTO (navy `#1b2d42`, texto `#0d1b2a`, hairline `#d9e0e7`,
estado OK `#22c55e`) según `docs/integrations/arcgis/experience-builder/design-system.md`.
