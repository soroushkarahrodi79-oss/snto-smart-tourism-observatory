# PNSG Research Authorisation Request — Draft Package

**Status:** DRAFT — technical content complete, territorial scope **decided**, **applicant identity fields are still placeholders and this must not be submitted as-is** · **Date:** 2026-08-09, territorial scope confirmed 2026-08-09
**Governs:** Master Execution Plan gate **G2** · Data Acquisition Triage open item · `FIELD_CAMPAIGN_EXECUTION_PLAN.md` §4.7

This document is the working draft of the authorisation request for the field campaign in `FIELD_CAMPAIGN_EXECUTION_PLAN.md`. It is **not** ready to submit: the technical content is complete and traceable to the frozen scientific plan, but every applicant-identity field is a placeholder, and one jurisdictional decision is still open. Neither may be filled in by inference — both need a real, human answer.

**No submission has been made. Nothing in this document has been sent to any authority.**

---

## 1. The administrative complication — read this first

PNSG's authorisation regime is **split by territory**, and it is not a formality: the two processes have different forms, different addressees, different submission channels, and (typically) different processing times.

| | **Comunidad de Madrid** | **Castilla y León (Segovia)** |
|---|---|---|
| Covers | The Madrid-side sector of the park | The Segovia-side sector |
| Legal basis | PRUG (Decreto 18/2020, Consejo de Gobierno de Madrid) | Same PRUG, Castilla y León implementing procedure |
| Addressee | Parque Nacional de la Sierra de Guadarrama, Consejería de Medio Ambiente (Comunidad de Madrid) | Servicio Territorial de Medio Ambiente de Segovia |
| Submission channel | Electronic — [Sede Electrónica, Comunidad de Madrid](https://sede.comunidad.madrid/autorizaciones-licencias-permisos-carnes/autorizacion-p-n-sierra-guadarrama) | Postal — Pza. Reina Doña Juana, 5, 40071 Segovia (electronic tramitación also exists via the [Junta de Castilla y León sede](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Tramite/1285083549419/Tramite)) |
| Form | [`Solicitud de autorización … territorio de Madrid`](https://www.parquenacionalsierraguadarrama.es/autorizaciones/download/30-autorizaciones/330-solictud-autorizacion-cm) | [`Solicitud de autorización … territorio de Castilla y León`](https://www.parquenacionalsierraguadarrama.es/autorizaciones/download/30-autorizaciones/306-solictud-autorizacion-cyl) |
| Research support contact | [CISE — Centro de Investigación, Seguimiento y Evaluación](https://www.parquenacionalsierraguadarrama.es/otras-unidades/cise), based in Rascafría with a lab at Puerto de los Cotos; coordinates external research projects | No park-run equivalent identified in this research |

**Verified fact from the repository's own trail geometry:** curated PNSG assets at longitude ≲ −4.0° (`pnsg_escalada_valsain` −4.013, `pnsg_escalada_puerto_de_navacerrada` −4.010, `pnsg_reserva_umbria_de_siete_picos` −4.041, `pnsg_reserva_umbria_de_cerro_ventoso` −4.051) sit on or near the Segovia side of the range crest, while the bulk of the network (La Pedriza, Peñalara, El Chorro) is Madrid-side. **The 218-trail sampling frame frozen in `PAPER1_SCIENTIFIC_CONTRACT.md` §F genuinely spans both jurisdictions.** This was not checked against an authoritative administrative-boundary layer — it is read off longitude and known place names, and should be verified with a real boundary overlay before it drives a decision (Backlog item, see §7).

### Decision: Madrid-side only 🔒 **CONFIRMED 2026-08-09 (owner decision)**

The sampling frame's territorial scope is **Comunidad de Madrid only**. Trail-segment selection (Backlog B-01) is constrained to segments within that territory; no Castilla y León application will be filed for Paper 1. Reasoning, recorded for the record:

1. **One process, one authority, one timeline** instead of two independent applications with two different lead times — the pilot (Master Plan gate G2) is already the schedule's longest dependency; doubling it would be a cost with no scientific benefit.
2. **CISE is the park's dedicated research-support unit and sits on the Madrid side** — a natural point of contact for both the formal application and informal pre-submission coordination.
3. The Madrid sector alone contains the full elevation/habitat gradient the stratified design needs — La Pedriza (granite, low elevation) through Peñalara (alpine, >2 100 m) — so **nothing in the Statistical Analysis Plan or the four ecological strata (S1–S4) requires Segovia-side segments.**
4. This is a **site-selection constraint, not a scientific-contract change** — the frame is still "218 OAPN trails" (Contract §F, F-1); this only narrows *which* of those 218 are eligible for Backlog B-01's stratified draw. Recorded there and in the Contract.

**Consequence, now firm rather than optional:** the longitude read-off in this document is not precise enough to filter the final 218-trail geometry — Backlog **B-01** must filter against a real Madrid/Castilla y León administrative boundary layer (public cartography, e.g. IGN límites administrativos) before the stratified segment draw runs, not the ≲ −4.0° heuristic used here to make the case for this decision.

---

## 2. Required documentation (per the park's own published requirements)

Confirmed from the park's authorisation pages: for research activities, in addition to the standard request form, applicants must attach:

1. **A supplementary technical report ("memoria")** describing the research activity — content drafted in §4 below.
2. **Proof of scientific standing** — either an institutional endorsement ("aval científico") or the principal investigator's CV. **Not fabricated here — you supply this.**
3. **A detail map ("plano de detalle")** locating the requested zone or itinerary.

## 3. Timeline and how it interacts with the campaign schedule

Spanish regional-government authorisation processes of this kind typically run **weeks to a few months**, not days. Two consequences for `FIELD_CAMPAIGN_EXECUTION_PLAN.md`:

- **This is the longest lead-time item on the entire dependency graph** (`PAPER1_MASTER_EXECUTION_PLAN.md` §8) — it should be filed now, in parallel with the desk work (strata derivation, site selection, acquisition manifest), not after.
- Filing in August 2026 makes a same-season field window unrealistic once agency turnaround is added. **The realistic target is the peak growing-season window (`SATELLITE_FIELD_MATCHING_PLAN.md` §2) in 2027**, unless the process is expedited. This is stated as a planning assumption below, not a claim about actual processing time, which nobody in this project has observed yet.

---

## 4. Draft memoria (technical project description)

*Everything below is drawn directly from the frozen Scientific Contract, the Field Campaign Execution Plan, and the Spatial/Satellite Matching Plans — no content here is invented for this document.*

> **Título del proyecto / Title**
> Can Sentinel-2 spectral stress track field-observed trail degradation? A control–impact validation in Parque Nacional de la Sierra de Guadarrama.
>
> **Investigador principal / equipo de campo**
> [PLACEHOLDER — name, DNI/NIE or passport number, institutional affiliation if any]. Field team: 2 observers minimum (repeatability protocol requires paired independent measurement on a subset of plots — `FIELD_CAMPAIGN_EXECUTION_PLAN.md` §5).
>
> **Institución / Institution**
> [PLACEHOLDER — university, research centre, or "independent researcher" if applicable]
>
> **Objetivo científico**
> Test whether a Sentinel-2-derived ecological-stress indicator (already computed and published for the park's 218-trail network) covaries with an independently measured field degradation index at co-located plots, using a stratified control–impact design. The study makes no claim of visitor-caused causation; it is an association study (see `PAPER1_SCIENTIFIC_CONTRACT.md` §B–D).
>
> **Ámbito territorial solicitado**
> Trail segments within the **Comunidad de Madrid** sector of Parque Nacional de la Sierra de Guadarrama, drawn from the park's official public-use trail cartography (OAPN WFS `UsoPublico_visor`). Exact segments to be finalised by stratified selection (§5 below); a provisional zone map covering the eligible Madrid-side segment pool is attached (§6).
>
> **Metodología**
> Non-destructive, non-invasive field plots. Per plot (20 × 20 m, sampled via 5 × 1 m² subplots): visual estimation of vegetation cover (%) and erosion class (0–3, visual scale), soil-compaction reading via hand penetrometer (minimal-depth ground insertion, no excavation, no soil removed from site), trail-width tape measurement, georeferenced photography, GPS position. No specimens collected, no vegetation removed, no soil samples taken off-site. Full protocol: `docs/field_validation_protocol.md` (audited) and `docs/paper1/FIELD_CAMPAIGN_EXECUTION_PLAN.md`.
>
> **Diseño muestral**
> Two-stage: a pilot round (≤16 plots across 2 strata, 1–2 field days) to estimate variance, followed by a main campaign whose size is fixed from the pilot's measured variance (no assumed sample size — `FIELD_CAMPAIGN_EXECUTION_PLAN.md` §2). Total field days: pilot 1–2 days; main campaign indicatively 4–8 days depending on pilot timing results (§8 of the same document). Control plots are placed ≥ 100 m from any mapped trail, in the same ecological stratum as their paired impact plot.
>
> **Fechas previstas**
> Target: **summer 2027, approximately 20 June – 31 July** (peak Mediterranean-montane growing season, bracketed below by high-elevation snowmelt and above by low-elevation drought senescence), timed to a Sentinel-2 acquisition window defined in advance (`SATELLITE_FIELD_MATCHING_PLAN.md` §2). Field days ordered low-elevation strata first, high-elevation (alpine) last. Weather-conditional: penetrometer readings require ≥ 48 h since significant rainfall. If authorisation is granted after the 2027 window, fieldwork moves to the equivalent 2028 window. Exact dates will be confirmed to the park administration once the permit is granted.
>
> **Impacto previsto y medidas de minimización**
> Foot access on and immediately adjacent to existing mapped trails only; no off-trail bushwhacking beyond the ≤ 20 m plot radius; no vegetation clearing; no marking left in the field beyond a temporary, removed-same-day subplot frame; photographs and GPS only as permanent record. Leave-no-trace practice throughout.
>
> **Uso previsto de los resultados**
> Academic publication (target venues assessed in `docs/paper1/JOURNAL_STRATEGY.md`) and open deposition of the field dataset and analysis code. No commercial use. A courtesy copy of the resulting field dataset and any publication will be offered to the park administration and to CISE.
>
> **Aval científico / CV**
> [PLACEHOLDER — attach separately; not fabricated in this draft]

## 5. What "finalising segments" needs before submission

The plano de detalle (§6) and the memoria's exact itinerary are strongest once real ecological strata are derived from OAPN vegetation/DEM layers and the stratified segment draw is run (`IMPLEMENTATION_BACKLOG.md` B-01, itself gated on the territorial-scope decision in §1). Two submission strategies, either is normal practice:

- **(a)** Submit now with a **zone-level** request (the eligible sector of the park, e.g. "Madrid-side public-use trail network"), which the park's own documentation explicitly accommodates ("zona **o** itinerario"), and supply the precise segment list as a follow-up once B-01 completes — likely well before fieldwork, since the permit will still be processing.
- **(b)** Complete B-01 first (a few desk-days), then submit with exact segments named.

**Recommendation: (a).** It removes the permit application from the campaign's critical path instead of adding to it — the permit's own processing time is already the longest lead item (§3), so nothing is gained by delaying its submission for a desk task that runs in parallel anyway.

## 6. Plano de detalle (map)

Not yet produced. Once the territorial scope is confirmed (§1), a park-boundary + eligible-trail-network map can be generated from committed data — this is the same input as `FIGURE_PLAN.md` Figure 1(b), which is already flagged as producible today from `data/outputs/pnsg/pipeline_a_results.geojson`. Producing it for the permit application is a natural first use of that figure script (`IMPLEMENTATION_BACKLOG.md` B-09).

## 7. What is needed from you before this can be submitted

Nothing above is submittable as-is. Two classes of blocker:

**Facts that cannot be inferred or fabricated:**

| # | Needed |
|---|---|
| 1 | Applicant legal name, ID number (DNI/NIE/passport), and institutional affiliation (or confirmation of independent-researcher status) |
| 2 | Contact address, email, phone |
| 3 | Scientific endorsement — an institutional letter, or your CV, to attach as the "aval científico" |
| ~~4~~ | ~~Territorial scope~~ — **resolved 2026-08-09: Madrid only** |
| 4 | Confirmation this should actually be submitted to the authority once complete — this is an external, real, hard-to-reverse action, and I will not send anything without that explicit go-ahead |

**One technical check now required, not optional (§1):**

5. Verify the Madrid/Castilla y León administrative boundary against an authoritative layer (e.g. IGN límites administrativos) rather than the longitude read-off used to justify this decision — this now directly gates which of the 218 trail segments are eligible for Backlog B-01's stratified draw.

---

## 8. Status against the Master Execution Plan

`PAPER1_MASTER_EXECUTION_PLAN.md` gate **G2 ("Research permit obtained")** — this document is the **first concrete step** toward it: the technical case is fully drafted and traceable to the frozen scientific plan. It advances no further until the identity/scope fields in §7 are supplied.

## Sources

- [Formularios de solicitud de autorización — PNSG](https://www.parquenacionalsierraguadarrama.es/es/visita/descargas/category/30-autorizaciones)
- [Autorización P.N. Sierra de Guadarrama — Sede Electrónica, Comunidad de Madrid](https://sede.comunidad.madrid/autorizaciones-licencias-permisos-carnes/autorizacion-p-n-sierra-guadarrama)
- [Solicitud de autorización — territorio de Madrid (PDF)](https://www.parquenacionalsierraguadarrama.es/autorizaciones/download/30-autorizaciones/330-solictud-autorizacion-cm)
- [Solicitud de autorización — territorio de Castilla y León (PDF)](https://www.parquenacionalsierraguadarrama.es/autorizaciones/download/30-autorizaciones/306-solictud-autorizacion-cyl)
- [Trámite — Junta de Castilla y León, actividades reguladas en el PRUG](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Tramite/1285083549419/Tramite)
- [Centro de Investigación, Seguimiento y Evaluación (CISE)](https://www.parquenacionalsierraguadarrama.es/otras-unidades/cise)
- [Parque Nacional de la Sierra de Guadarrama — Comunidad de Madrid](https://www.comunidad.madrid/medio-ambiente/parque-nacional-sierra-guadarrama)
