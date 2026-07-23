# SNTO — Estrategia de publicación (dos pistas)

> **Regla de una frase:** el *software* se publica siguiendo las **releases de
> código**; la *ciencia* se publica siguiendo la **evidencia**. No mezclar.

Este documento fija la política para que la difusión no sobre-afirme (ADR-003,
ADR-004) ni se quede obsoleta. Es la referencia a consultar antes de cada
release, post o preprint.

## Por qué dos pistas

El código de SNTO avanza mucho más rápido que la evidencia científica. La
arquitectura ya es v2.0 (backend persistente, UI por roles) y va camino de v3.0
(enterprise/multi-tenant), pero la **metodología no cambia desde v1.3.0** y la
**validación de campo (#26) todavía no se ha ejecutado ni una vez**. Publicar
las dos cosas al mismo ritmo llevaría, o bien a un preprint que se reescribe sin
contenido científico nuevo, o bien a afirmar validación que no existe. La
solución es separarlas.

| | **Pista A — Artefacto de software** | **Pista B — Publicación científica** |
|---|---|---|
| **Qué publica** | El código como artefacto citable (Zenodo *Software*, GitHub Release) | El método y, cuando exista, los resultados de validación (preprint, ResearchGate, revista) |
| **Disparador** | Una **release de código** significativa (hito mayor: v2.0.0, v3.0.0) | **Evidencia científica nueva** (la campaña de campo #26; réplica multi-territorio A14) |
| **Permitida hoy** | ✅ Sí (ADR-003: *"methods/software publication"* está permitida) | ⚠️ Solo con lenguaje acotado; **prohibido** afirmar "validado" hasta #26 |
| **Cadencia** | En cada hito mayor tageado (no en dev markers) | Cuando hay resultado nuevo que reportar, no por versión de software |
| **Claim máximo** | "capa de decisión open-source, X tests, desplegada" | "apoyo a la decisión + generación de hipótesis causales" (ADR-003) — **nunca** "monitorización validada" |

## Qué SÍ se puede publicar ahora (Pista A)

- **Archivo Zenodo de la release actual** (p. ej. v2.0.0) → DOI de versión bajo
  el *concept DOI* existente (`10.5281/zenodo.20818270`). Tipo *Software*.
- **GitHub Release** con notas (ver `docs/releases/`).
- **Posts de plataforma** (LinkedIn/X): hitos de ingeniería — arquitectura, nº
  de tests, despliegue, vistas por rol. **Sin cifras científicas nuevas.**
- **Petición de colaboración** a OAPN/EUROPARC **para** la campaña de campo
  (distinto de pedir adopción operativa como sistema validado).

## Qué NO se publica hasta la campaña de campo #26 (Pista B)

- Un preprint científico "nuevo" motivado solo por v2.0/v3.0 (no hay ciencia
  nueva → debilita el próximo, no lo fortalece).
- Cualquier claim de **"validado"** o de **correlación satélite↔campo probada**.
- Un dossier a OAPN/EUROPARC que presente SNTO como **sistema de monitorización
  operativo y validado**.

## El hito de publicación que de verdad importa

No es v3.0 (madurez de plataforma, no ciencia). Es la **campaña de campo #26**:
todo el aparato de código ya está listo (runner de concordancia satélite↔campo
`src/ui/services/field_agreement.py`, captura de parcelas
`src/ui/services/field_capture.py`). En cuanto se recojan ≥15 parcelas reales
co-localizadas y el runner emita un ρ de Spearman real, se desbloquea el **paper
fuerte** (la "v2 del paper") — el que convierte a SNTO de "prototipo prometedor"
en "método validado para el PNSG". Ese es el momento de la Pista B.

## Convención de claims (recordatorio de ADR-003 / ADR-004)

- Lenguaje permitido: *decision-support*, *early-warning estacional*, *causal
  hypothesis generation*, *calibrado por percentiles de escena*.
- Lenguaje prohibido hasta validar: *validado*, *monitorización operativa
  probada*, *tendencia plurianual confirmada como causal*.
- Cada cifra lleva su clase de evidencia (real / calibrado / sintético /
  simulado). Nunca se relaja: "más separación que hoy, nunca menos".

## Checklist por release (Pista A)

1. `pyproject.toml` tageado en el hito (semver).
2. Notas de release en `docs/releases/vX.Y.Z.md` (qué cambió, con clases de
   evidencia intactas).
3. Zenodo → *New version* → subir el `.zip` del tag → metadatos (bloque en las
   notas de release) → DOI de versión.
4. `CITATION.cff` alineado con la versión archivada.
5. Post de plataforma (opcional), solo hechos de ingeniería.

## Relación con otros documentos

- Política de claims: [`decisions/ADR-003.md`](decisions/ADR-003.md).
- Separación de evidencia: [`decisions/ADR-004.md`](decisions/ADR-004.md).
- Kit de difusión (textos): [`kit_difusion.md`](kit_difusion.md).
- Notas de release: [`releases/`](releases/).
- Defensa académica: [`defensibilidad_academica.md`](defensibilidad_academica.md).
