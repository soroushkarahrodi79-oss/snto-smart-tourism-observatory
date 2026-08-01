# Arquitectura por página — Experience Builder MVP

> Widgets estándar de ArcGIS Online. Ninguna construcción se realiza aún.

## 1. Decidir — visión ejecutiva de decisión

**Widgets:** Map · Filter · List (activos piloto) · Indicator cards · Legend ·
Text (panel de `decision_caveat`).

**Indicadores propuestos** (derivados de campos verificados de `pilot_assets`):
total de activos piloto; activos con tendencia decreciente (`trend=decreasing`);
activos con tendencia significativa (`trend_significant`); activos de alta
confianza (`confidence=high`); activos con evidencia de campo; activos pendientes
de verificación de campo.

**Interacciones:** seleccionar un activo en la List → zoom/selección en el Map;
seleccionar una entidad del Map → actualiza indicadores y panel de detalle; los
filtros afectan Map, List e indicadores.

**Reglas de evidencia:** ningún valor `simulated`/`estimated` como titular;
`confidence` + badge de evidencia junto a cada cifra; máximo 3–4 cifras de
decisión reales.

## 2. Diagnosticar — señales analíticas e incertidumbre

**Widgets:** Map · Feature Info · Table · Filter · Text (panel de metodología) ·
Chart opcional donde esté soportado.

**Campos:** `trend`, `tau`, `p_value`, `sens_slope`, `confidence`,
`change_point_date`, `n_observations`, `provenance`, `decision_caveat`.

**Dejar claro:** la tendencia **no es causalidad**; la geometría de activo
provisional difiere del punto representativo; las coordenadas provisionales **no**
son límites autoritativos; `missing` **no** es `0`; `synthetic` **no** es `real`.

## 3. Evidenciar — observaciones de campo y adjuntos

**Fuente preferida:** Survey123 **results view**.

**Widgets:** Map · List · Feature Info · **Attachment** · Filter · Table.

**Filtros:** `asset_id`, `plot_id`, `evidence_class`, `qa_status`, `observed_at`.

**Interacciones:** seleccionar una observación abre sus atributos y adjuntos;
seleccionar un activo filtra las observaciones relacionadas **lógicamente por
`asset_id`** — **no se asume ninguna relationship class formal**.

**Estado real hoy:** aún no hay campaña; las parcelas pueden estar
`planned`/`missing`. No etiquetar `planned` como «observada»; no afirmar acuerdo
satélite↔campo.

## 4. Gobernar — gobernanza de evidencia y flujo

**Widgets:** Text · Button/link · paneles de proceso/timeline · enlaces a
documentación embebidos opcionales.

**Contenido:** clases de evidencia; flujo QA (`planned`→`draft`→`submitted`→
`reviewed`/`rejected`); procedencia de fuentes; limitaciones; responsabilidades
del propietario; cadencia de actualización (snapshot manual, no en vivo); aviso
de continuidad de la cuenta educativa.

**Regla:** **no** exponer credenciales, URLs de servicio ni Item IDs internos.

## 5. Asset Detail — fusión transversal de un solo activo

**Widgets:** Map · Feature Info · lista de observaciones relacionadas (filtrada
lógicamente por `asset_id`) · Attachment · indicadores · Text
(metodología/caveat).

**Interacción:** dirigida por el activo seleccionado; mostrar **evidencia
analítica separada de la evidencia de campo**; **no** presentar datos `planned` y
`observed` como equivalentes; **no** inferir una relación formal de ArcGIS.

Implementable íntegramente con widgets estándar (Feature Info + List + Text +
parámetros de URL). Ninguna brecha de widget que exija desarrollo personalizado.
