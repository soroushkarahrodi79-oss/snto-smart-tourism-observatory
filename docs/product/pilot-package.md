# Paquete de piloto — propuesta lista para contratación (A07)

> **Estado del documento.** El alcance técnico, los entregables, el calendario y
> los criterios de aceptación están **cerrados y verificados** contra lo que el
> sistema hace hoy. Las **decisiones comerciales y jurídicas siguen abiertas** y
> están marcadas con 🔲 — son del responsable del proyecto, no del sistema.
> Búscalas con `grep -n "🔲" docs/product/pilot-package.md`.
>
> Ninguna cifra económica de este documento está inventada: donde falta un
> precio, hay un hueco, no una estimación.

Responde a la acción **A07** de la matriz de prioridades
([`../reviews/2026/08-priority-roadmap.md`](../reviews/2026/08-priority-roadmap.md))
y al *Next Step* declarado en
[`commercialization.md`](commercialization.md): *"Build a procurement-ready pilot
package with validation, reporting, and GIS integration scope"*.

---

## 1. Decisiones abiertas (resumen para el responsable)

| # | Decisión | Por qué no la puede fijar el sistema |
|---|---|---|
| D1 | Precio del piloto y desglose | Depende de dedicación, coste de campaña y política de la UCM |
| D2 | Vía de contratación | Contrato menor / convenio UCM / encargo: es jurídico-administrativa |
| D3 | Titularidad de datos y resultados | Afecta a cartografía OAPN y a datos de campo del organismo |
| D4 | Licencia de uso del software para el organismo | Hoy el repositorio es de **uso académico** ([`../../LICENSE`](../../LICENSE)) |
| D5 | Quién ejecuta la campaña de campo | Equipo del Parque, UCM, o mixto — cambia coste y calendario |
| D6 | Cobertura de seguros y permisos de acceso | Normativa del espacio protegido |
| D7 | Duración del soporte tras el piloto | Compromiso de dedicación futura |

---

## 2. Qué es este piloto

Un **piloto acotado y evaluable** sobre **un espacio protegido**, que responde a
una pregunta concreta:

> ¿La señal satelital del SNTO identifica correctamente los tramos de sendero que
> el personal del Parque reconoce como deteriorados sobre el terreno?

Esa pregunta **hoy no tiene respuesta** en ningún sitio: la herramienta de
concordancia está implementada y probada, pero **la campaña de campo nunca se ha
ejecutado**. El piloto existe para ejecutarla. Es su principal aportación
científica y la condición para cualquier afirmación de validez posterior.

**No es** una implantación, ni una licencia de software, ni un compromiso de
servicio continuado.

---

## 3. Alcance técnico (cerrado)

Lo que ya está operativo y entra en el piloto sin desarrollo nuevo:

| Capacidad | Estado hoy | Evidencia |
|---|---|---|
| Estado ecológico por sendero (EHS, NDVI/NDMI) | Operativo | `real` — Sentinel-2 L2A |
| Atribución causal uso vs clima (SCM) | Operativo | `simulated` hasta exportar zonas multiescala reales |
| Confianza de decisión (DCS) con puerta de calidad | Operativo | `real` |
| Priorización e importe orientativo (TPI / TIS) | Operativo | `calibrated` |
| Seguimiento por zonas **PRUG** | Operativo | `real` (cartografía OAPN × señal Sentinel-2) |
| Preparación de dosier **CETS Fase I** | Operativo | cobertura declarada + evidencia calculada |
| Exportación **GIS** (GeoJSON / GeoPackage) | Operativo | `real` |
| Panel web con vistas por audiencia | Operativo | desplegado |
| Contrato de integración **OpenAPI** | Publicado | [`../api/openapi.json`](../api/openapi.json) |
| Concordancia satélite↔campo | **Herramienta lista, sin ejecutar** | ⛔ requiere la campaña |

**Fuera de alcance** salvo acuerdo expreso: despliegue de la API como servicio
(gobernado por [`ADR-012`](../decisions/ADR-012.md)), integración SSO corporativo,
migración a PostGIS, portal público, y ampliación a un segundo espacio protegido.

---

## 4. Entregables

1. **Informe de diagnóstico territorial** — estado por sendero, deterioro
   estacional, atribución causal y priorización, con la clase de evidencia de
   cada cifra.
2. **Capa GIS** lista para QGIS/ArcGIS, con `evidence_level` por elemento.
3. **Seguimiento por zonas PRUG** — desajuste protección↔presión por zona de
   gestión oficial.
4. **Preparación de dosier CETS Fase I** — correspondencia requisito a requisito
   con la evidencia que la respalda.
5. **Campaña de validación de campo ejecutada** — parcelas impacto/control
   georreferenciadas, con fotografía y medición.
6. **Resultado de concordancia satélite↔campo publicado con honestidad** —
   Spearman ρ y Cliff's δ, **se cumpla o no el umbral**. Un resultado negativo se
   reporta igual: es información de gestión, no un fracaso del piloto.
7. **Informe de límites** — qué queda demostrado y qué no.
8. **Acceso al panel** durante el piloto y traspaso de la documentación técnica.

🔲 **D7 — Soporte posterior al piloto:** definir si se incluye acompañamiento tras
la entrega y con qué dedicación.

---

## 5. Qué debe aportar el organismo

Sin esto el piloto no puede ejecutarse:

- **Cartografía oficial** de sendas y zonificación del espacio (para el PNSG ya
  está incorporada).
- **Acceso al terreno y permisos** para las parcelas de campo, incluidas zonas de
  uso restringido si entran en la muestra.
- **Un interlocutor técnico** del equipo gestor (estimación: pocas horas al mes).
- **Apoyo de campo** para la campaña.
- **Datos de afluencia**, si existen: aforos de sendero, conteos o registros de
  uso público. **Es hoy la brecha principal** — la capacidad de carga se apoya en
  una estimación curada, no en una medición. Si no existen, el piloto lo declara
  como limitación en lugar de simularlos.

🔲 **D5 — Quién ejecuta la campaña de campo:** equipo del Parque, UCM o mixto.
Condiciona coste (🔲 D1) y calendario (H3).

🔲 **D6 — Permisos, accesos y cobertura de seguros:** según la normativa del
espacio protegido y las zonas que entren en la muestra.

---

## 6. Calendario e hitos

La duración **no la fija una preferencia comercial, sino la fenología**: el
protocolo exige que las parcelas de campo se levanten *"en la ventana fenológica
de la escena satelital usada"*
([`../field_validation_protocol.md`](../field_validation_protocol.md) §5). Eso
ancla la campaña a la temporada de vegetación comparable con la escena.

| Hito | Contenido | Dependencia |
|---|---|---|
| H1 · Arranque | Alcance, activos, estratos de muestreo | Interlocutor designado |
| H2 · Diagnóstico satelital | Entregables 1–4 sobre el territorio | Cartografía oficial |
| H3 · Campaña de campo | Parcelas impacto/control | **Ventana fenológica** + permisos |
| H4 · Concordancia y cierre | Entregables 6–8 | H3 completado |

🔲 **D2 — Duración total y fechas:** dependen de la vía de contratación y de en
qué momento del año se firme respecto a la ventana fenológica.

---

## 7. Criterios de aceptación

Comprobables, sin ambigüedad:

- Los entregables 1–4 se generan desde el sistema y sus cifras **coinciden con
  los datos vivos** (verificado automáticamente en CI).
- La campaña alcanza el **mínimo metodológico de 3 parcelas co-localizadas**; el
  objetivo de calidad es **≥ 15–20 impacto + ≥ 15–20 control**, estratificadas
  (§5 del protocolo).
- El análisis de concordancia se ejecuta y **publica ρ y δ**, con su lectura.
- Cada cifra entregada lleva su clase de evidencia.

**El criterio de aceptación NO es que la correlación salga positiva.** Es que se
mida y se reporte con rigor. Condicionar el pago a un resultado científico
concreto incentivaría exactamente el sesgo que este proyecto evita.

---

## 8. Lo que este piloto no promete

Explícito, porque un documento de contratación que insinúa más de lo que puede
demostrar es el mayor riesgo reputacional del proyecto:

- **No promete validación previa.** Hasta que la campaña se ejecute, *"tendencia
  satelital real"* **no** equivale a *"validado en campo"* ([`ADR-003`](../decisions/ADR-003.md)).
- **No promete tendencia plurianual** donde solo hay dos escenas: eso es alerta
  temprana estacional. La serie 2021–2026 existe para 21 activos del PNSG, no
  para todos.
- **No promete medición de visitantes.** Sin aforos reales, la presión es una
  estimación curada declarada como tal.
- **No promete transferibilidad a otro espacio.** Cada bioma exige su propia
  validación ([`ADR-003`](../decisions/ADR-003.md)); el piloto valida uno.
- **No sustituye** la inspección técnica, la dirección facultativa ni el criterio
  del equipo gestor.

---

## 9. Condiciones económicas

🔲 **D1 — Precio y desglose.** Pendiente. Conceptos a cubrir, para que el desglose
sea completo:

| Concepto | Nota |
|---|---|
| Dedicación técnica (análisis, informes, acompañamiento) | |
| Campaña de campo (jornadas, desplazamiento, instrumental) | Depende de 🔲 D5 |
| Infraestructura cloud durante el piloto | Coste real actual: bajo (escala a cero) |
| Licencias de datos | Sentinel-2 y Copernicus son **abiertos**: sin coste |

🔲 **D2 — Vía de contratación.** A elegir según importe y normativa: contrato
menor, convenio con la UCM, o encargo. Determina también facturación y plazos.

**Referencia de encaje presupuestario** (de [`commercialization.md`](commercialization.md)):
líneas de seguimiento ambiental, gestión de visitantes, adaptación climática,
planificación de la conservación, turismo sostenible o reporte obligatorio.

---

## 10. Propiedad intelectual, datos y licencia

🔲 **D3 — Titularidad de datos y resultados.** A definir: cartografía oficial
aportada por el organismo, datos de campo generados en el piloto, e informes
derivados.

🔲 **D4 — Licencia de uso del software.** El repositorio se distribuye hoy para
**uso académico** ([`../../LICENSE`](../../LICENSE)). Un uso operativo continuado
por parte del organismo requiere decidir el marco.

**No condicionado a decisión:** el código es abierto y auditable, y la
metodología está documentada — el organismo puede verificar cualquier cifra en
lugar de confiar en una caja negra. Es una propiedad del proyecto, no una
concesión negociable.

---

## 11. Riesgos y dependencias

| Riesgo | Efecto | Mitigación |
|---|---|---|
| La ventana fenológica se pasa | Retrasa H3 un ciclo anual | Firmar con margen sobre la temporada |
| No se alcanza la muestra mínima | Sin concordancia significativa | Estratificar y sobredimensionar la muestra |
| Sin datos de afluencia | Capacidad de carga sigue estimada | Se declara como limitación, no se simula |
| La correlación sale débil | Cuestiona el proxy satelital | **Es un resultado válido** y se publica |
| Meteorología / nubosidad | Menos escenas útiles | Sentinel-2 revisita cada 5 días; margen en H2 |

---

## Documentos relacionados

- [Comercialización](commercialization.md) · [Posicionamiento](positioning.md) ·
  [Propuesta de valor](value-proposition.md)
- [Adopción institucional](../strategy/institutional-adoption.md)
- [Dossier institucional OAPN](../dossier_institucional_OAPN.md)
- [Protocolo de validación de campo](../field_validation_protocol.md)
- [Contrato de integración OpenAPI](../api/README.md)
