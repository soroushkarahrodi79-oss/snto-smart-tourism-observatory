# SNTO UI Evolution — v2.0 Design Specification

> **Status:** Specification / strategy only. Not an implementation plan.
> **Mode:** READING MODE — DESIGN STRATEGY, NO IMPLEMENTATION.
> **Source:** Product Design Review Board strategic report, *"Evolución estratégica UX / UI de SNTO: de observatorio académico a plataforma de decisión institucional"* (2026-07-08).
> **Case study:** Parque Nacional de la Sierra de Guadarrama (PNSG) · v1.0.0 deployed.
> **Scope discipline:** This document proposes **no** code changes. It is the repository-native translation of the design strategy report. Implementation is gated on `app.py` modularization (ADR-007) and persistent backend (ADR-006).

## Table of Contents

1. [Executive summary](#1-executive-summary)
2. [Current UX diagnosis (D1–D10)](#2-current-ux-diagnosis-d1d10)
3. [Target v2.0 product experience](#3-target-v20-product-experience)
4. [Persona-based UX model](#4-persona-based-ux-model)
5. [Information architecture: Decidir · Diagnosticar · Evidenciar · Gobernar](#5-information-architecture)
6. [Module priority table (P1/P2/P3)](#6-module-priority-table-p1p2p3)
7. [Design system evolution rules](#7-design-system-evolution-rules)
8. [Scientific visualization rules](#8-scientific-visualization-rules)
9. [Evidence-state visual language](#9-evidence-state-visual-language)
10. [Dashboard simplification strategy](#10-dashboard-simplification-strategy)
11. [Design roadmap: v1.1 · v1.2 · pre-v2 · v2.0 · v3.0](#11-design-roadmap)
12. [Risks of implementing too early](#12-risks-of-implementing-too-early)
13. [What must wait until `app.py` modularization](#13-what-must-wait-until-apppy-modularization)
14. [What can be done now without touching product code](#14-what-can-be-done-now-without-touching-product-code)
15. [Final decision](#15-final-decision)

### Related documents

- [UI Evolution (long-term direction)](ui-evolution.md)
- [Information Architecture](information-architecture.md)
- [Dashboard Review](dashboard-review.md)
- [Design System Review](design-system-review.md)
- [Visualization Review](visualization-review.md)
- [Accessibility](accessibility.md)
- [UX Review](ux-review.md)
- [Personas](../product/personas.md)
- [Master Strategic Index](../../MASTER_STRATEGIC_INDEX.md)
- [Claude Code Handoff 2026](../ai-context/CLAUDE_CODE_HANDOFF_2026.md)
- Archived source PDF: [`docs/reviews/2026/SNTO_Design_Strategy_Report_2026.pdf`](../reviews/2026/SNTO_Design_Strategy_Report_2026.pdf)

**Governing ADRs:** ADR-004 (separate real / calibrated / synthetic / simulated evidence), ADR-006 (persistent backend before operational workflows), ADR-007 (keep UI evolution separate from v1.0 stability), ADR-008 (use existing GIS/EO platforms as integration surfaces).

---

## 1. Executive summary

SNTO is today an outstanding scientific-product prototype in its **thesis** — the chain *ecological signal → tourism-pressure hypothesis → confidence → priority → budget → report* — and weak in its **form as a product**. The 2026 consensus scores it **61/100 global**, with **innovation 82/100** against **enterprise readiness 28/100**. The current dashboard *demonstrates capability* instead of *guiding decisions*: 10 executive KPIs simultaneously, alert rows, a financial simulator, socioeconomic tabs, and methodology expanders all compete on the same screen, and for every persona at once.

This specification diagnoses the current experience, defines the target v2.0 experience (**"Decision intelligence for protected natural tourism destinations"**), and proposes a modular information architecture, an evolution of the *existing* design system (without replacing the identity), scientific visualization rules, and a version-disciplined design roadmap. **All of the work here is strategy: no code change is proposed before `app.py` modularization (ADR-007).**

Three principles govern every recommendation:

1. **Scientific clarity beats visual spectacle.**
2. **The separation real / calibrated / synthetic / simulated is non-negotiable and first-class (ADR-004).**
3. **Uncertainty is shown where the decision is made, not only where it is documented.**

Board conclusion, verbatim: *"SNTO has the brain of a reference product and the body of an advanced academic prototype."* The visual evolution must be **designed now and executed later**. The prerequisite is the modularization of `app.py` (~2,890 lines) and the stabilization of real temporal evidence (PR #1, not merged).

---

## 2. Current UX diagnosis (D1–D10)

Critical audit of the deployed surface (Streamlit, v1.0.0), contrasted with the 2026 strategic reviews (park director 62/100; full-purchase probability 35%, paid-pilot probability 65%).

### D1 — Density: the home page is an inventory, not a decision
The first screen presents, simultaneously, a territorial banner, 10 executive KPIs in a grid, a row of alert cards, a map, and access to the simulator and socioeconomics. Nothing answers first: *"what needs my attention today, and why?"* The cognitive cost is paid by the user, not the system. The *"What does it mean? → Recommended action → Technical basis"* layer is an excellent pattern, but repeated across 10 KPIs at once it becomes **structural noise**.

### D2 — Confusion: three view modes that are not three experiences
The Technical / Manager / Scientific-audit modes toggle the *same canvas* with more or less detail, instead of reorganizing content around distinct tasks. A manager in "Manager" mode still sees the anatomy of the calculation; an auditor gets no audit trail, only more expanders. The view mode is currently a **density filter, not a role architecture**.

### D3 — Evidence: provenance exists but does not govern the visual hierarchy
The provenance badges (observed / calculated / estimated / simulated) and the "Synthetic demo" badge exist — a rare achievement. But they are **peripheral labels**: a simulated KPI and an observed KPI carry identical visual weight, identical value typography (1.45rem/700), and identical position. The evidence class must **modulate the presentation** of the datum, not merely annotate it (ADR-004).

### D4 — Incomplete decision flows: the alert has no lifecycle
A critical EHS alert cannot be assigned, field-verified, funded, or closed. The chain ends at "Recommended action" with no owner, committed cost, deadline, or status. The director review identifies this as the **principal blocker for institutional trust**: SNTO detects and prioritizes, but it does not account. *(Note: the lifecycle requires a persistent backend — this is v2.0 design, not v1.x.)*

### D5 — Methodology drowns the action
Methodology expanders (📐 🧪 ⚖️ 📋) coexist with the operational flow in every section. Methodological honesty is SNTO's greatest scientific strength and **must not be reduced — it must be relocated**: one click away from every figure ("technical basis"), but off the primary decision path. Today the product needs a narrator; the explicit goal is that it should not.

### D6 — Hierarchy: everything is a top-level KPI
The 10 KPIs share size, accent border, and density. There is no distinction between a **state** indicator (mean health), an **urgency** indicator (active alerts), and a **management** indicator (budget). The uniform grid communicates "everything matters equally", which is the opposite of prioritizing. **Defensible maximum on the home page: 3–4 figures with real typographic hierarchy.**

### D7 — Personas forced through the same funnel
Director, GIS analyst, scientific reviewer, destination manager, and auditor all enter through the same page and traverse the same tabs. The reviews agree: the central object must be the **"managed asset with evidence and action status"**, not the dashboard tabs.

### D8 — Uncertainty documented, not operational
The DCS and the sensitivity analysis exist, but uncertainty does not accompany the datum at the point of decision: an EHS of 35 is shown as `35`, not as `35 ± range` with confidence. The scientific review also flags **incomplete error propagation** (cloud masking → indices → weights → prioritization): the design must avoid any presentation that suggests unsupported precision — e.g. budgets to the euro (€136,275) derived from estimates.

### D9 — The traffic-light palette competes with indigo and with provenance
The three deliberate palettes (tactical traffic-light, indigo→slate tiers, provenance) are a correct design decision, but on dense screens they coexist **without precedence rules**: alert red next to "simulated" red next to the EHS ramp. A documented **grammar of which palette may appear in the same module** is missing.

### D10 — Academic-demonstrator look
Accumulated signals: emoji as primary iconography on executive surfaces, long embedded explanatory texts, "Synthetic demo" badges coexisting with institutional figures, and the absence of governance artifacts (official reports, audit trail, GIS export). Each is defensible in isolation; together they produce the reading **"brilliant demonstrator", not "system I depend on"**.

---

## 3. Target v2.0 product experience

**Category:** decision intelligence for protected natural tourism destinations — the **decision layer over** GIS, Earth observation, and BI, **never their substitute** (ADR-008).

The experience pivots from **inventory** (*"look at everything SNTO computes"*) to **verdict**:

> *"This is the decision you must make, this is the evidence, this is the uncertainty, and this is the recommended action."*

**Central product object:** the **managed asset** (trail, viewpoint, zone), with an action state:

```
detected → verified → assigned → funded → resolved → monitored
```

Each screen answers **one question for one role**; the UX success metric is **defensible time-to-decision per persona**, not functional coverage.

**Progressive-disclosure rule (three layers, applied product-wide):**

| Layer | Content |
| --- | --- |
| **Layer 1 — Decision** | what, urgency, confidence, cost, owner |
| **Layer 2 — Evidence** | series, maps, comparison against threshold and baseline, evidence class |
| **Layer 3 — Method** | formulas, calibration, limitations, ADRs |

Nothing in Layer 3 disappears; it simply **stops getting in the way**.

---

## 4. Persona-based UX model

The director is a **recurring decider, not a daily user**; the daily users are the analyst and the operations manager. All six experiences share the **same object (managed asset)** and the **same evidence language**; they differ in home page, density, and exports.

### Persona matrix

| Persona | Primary question | Home page they need | Decisions | Evidence & uncertainty | Exports / hidden by default |
| --- | --- | --- | --- | --- | --- |
| **National Park Director** | What needs my attention this week, with what confidence, and what will it cost me? | Decision brief: 3–5 priority assets with action, cost, confidence, owner, deadline | Approve investment, assign staff, order inspection, escalate to OAPN | Confidence per recommendation (DCS) and field-verification status; never figures without evidence class | Political/OAPN 1–2 page report. Hidden: formulas, calibration, raw series |
| **Technical GIS / EO analyst** | Is this signal real, and where does it come from? | Spatial diagnosis: map with toggleable layers, NDVI/NDMI series per asset, anomalies | Confirm / reject alerts, adjust baselines, prepare GIS packages | Pixel-to-indicator: scenes, cloud masks, temporal windows, full uncertainty bands | GeoJSON/GeoTIFF, series CSV. Hidden: budget and political narrative |
| **Scientific reviewer** | Is the method defensible and the claim level honest? | Methodology & audit center: pipeline, assumptions, limitations, pending validation | Endorse or condition use; define the validation protocol | Error propagation, sensitivity, causal hypothesis always in hypothesis language | Citable methodological annex. Hidden: nothing — full access |
| **Tourism destination manager** | Where is the visitor pressing, and which assets must I regulate or promote? | Pressure & carrying capacity: TPI per asset, seasons, investment/promotion tiers | Regulate access, redistribute flows, prioritize promotion (Tier III–IV) | Explicit observed vs estimated pressure; carrying capacity as a range, never a single number | Per-season summary. Hidden: spectral detail, satellite pipeline |
| **Public-administration decider** | Is this budget justified, and can I defend it? | Investment portfolio: tiers, cost-benefit, socioeconomic impact (jobs, local income) | Approve line items, order priorities across territories | Budgets as ranges with visible assumptions; socioeconomic impact marked as estimation | Official investment memo. Hidden: index mechanics, technical maps |
| **Auditor / evaluator** | Can I reconstruct how each recommendation was reached? | Audit center: data→decision traceability, versions, provenance log | Certify the process, flag non-conformities | Full evidence chain with class, date, source, and per-step transformations | Audit dossier. Hidden: nothing — but read-only |

---

## 5. Information architecture

Four navigable layers — **Decidir · Diagnosticar · Evidenciar · Gobernar** — replace the current tabs. The authoritative object hierarchy (per CPO review) is:

```
asset → risk → confidence → causal hypothesis → recommended action → cost → owner/status → evidence → report
```

### Decidir (Decide)
The verdict layer. Answers *"what must be decided this week?"* Executive decision panorama, urgent-action queue, intervention-budget simulator, and socioeconomic impact. Header figures in this layer admit **only observed/calculated** classes.

### Diagnosticar (Diagnose)
The "is it real, and where?" layer. Protected-area health, spatial diagnosis, master asset/trail catalogue, and pressure & carrying capacity. Uncertainty bands, baselines, and thresholds are always drawn.

### Evidenciar (Evidence)
The "show the raw data behind the signal" layer. Satellite evidence (Sentinel-2 2021–2026), confidence & uncertainty decomposition, data provenance, and field-validation status. Gaps and cloud masks are **never silently interpolated**.

### Gobernar (Govern)
The accountability layer. Methodology & audit (all of today's Layer 3, structured and versioned), reports/exports, and configuration / territorial management. Limitations are **first-class content, not fine print**.

---

## 6. Module priority table (P1/P2/P3)

**Legend:** P1 = essential in the first v2.0 cut · P2 = second v2.0 cut · P3 = may wait for v2.x/v3.0.

> "Urgent actions" with a full lifecycle depends on a persistent backend (ADR-006); its first v2.0 version may be **documentedly ephemeral local state, never simulating persistence**.

| Layer | Module | Purpose / decision supported | User | Key metrics & visualizations | Evidence · uncertainty | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| **Decidir** | Executive decision panorama | Director home: what to decide this week. Approve / postpone / request verification | Director, public decider | 3–4 ranked figures; pending-decision list with confidence and cost | Only observed/calculated in header figures; DCS visible per decision | **P1** |
| **Decidir** | Urgent actions | Triaged operational alert queue. Assign, escalate, dismiss with reason | Operations, director | Queue ordered by severity×confidence; asset card with action and status | Field-verification status per alert; false positives logged | **P1** |
| **Decidir** | Intervention-budget simulator | Compare investment scenarios per tier. Compose annual portfolio | Director, public decider | Indigo tiers; cost as range; avoided-risk delta per scenario | Always marked **simulated**; assumptions editable and visible | P2 |
| **Decidir** | Socioeconomic impact | Justify investment to administration: associated employment and income | Public decider, destination manager | Jobs, local income, tourism dependency; always with denominators | Class **estimated**; estimation methodology linked | P3 |
| **Diagnosticar** | Protected-area health | Aggregate ecological state and trend. Watch, not act | All | Mean EHS with band; distribution by severity; interannual trend | Uncertainty band on every series; baseline and threshold always drawn | **P1** |
| **Diagnosticar** | Spatial diagnosis | Where stress occurs. Focus inspection | Analyst, operations | Map with EHS / pressure / PRUG-zone layers; layer control with data-class legend | Scene coverage and cloud gaps visible as their own layer | **P1** |
| **Diagnosticar** | Asset / trail catalogue | Master registry of the 218 OAPN trails with action state. **Product core** | All | Filterable table: EHS, TPI, tier, confidence, status; asset card as a page | Evidence class per column; verification status per asset | **P1** |
| **Diagnosticar** | Pressure & carrying capacity | Relate visitor pressure to stress. Regulate flows and seasons | Destination manager, director | Temporal TPI; capacity as range; tourism-vs-climate attribution (SCM) as hypothesis with confidence | Causal-hypothesis language mandatory; correlation ≠ cause flagged | P2 |
| **Evidenciar** | Satellite evidence | See the Sentinel-2 data behind each signal. Confirm or reject alerts | Analyst, reviewer | NDVI/NDMI series 2021–2026 per asset; scenes, dates, quality; temporal comparator | Class **observed**; gaps and masks never silently interpolated | **P1** (after PR #1) |
| **Evidenciar** | Confidence & uncertainty | Explain each DCS: components, sensitivity, what would raise it. Calibrate how much to trust | Reviewer, analyst, director | DCS decomposition; sensitivity tornado; evidence-gap map | This **is** the uncertainty module — everything visible, including pending propagation | P2 |
| **Evidenciar** | Data provenance | Per-datum registry: source, date, class, transformations. Audit the lineage | Auditor, reviewer | Lineage table; data→indicator→decision diagram | The four classes with operational definition and examples | P2 |
| **Evidenciar** | Validation status | What is field-validated and what is not. Condition the claim level | Reviewer, director | Indicator × territory matrix with state (unvalidated / in campaign / validated); false ± | Absence of validation is shown, never disguised | P2 (v1.2 defines protocol) |
| **Gobernar** | Methodology & audit | All of today's embedded Layer 3: formulas, calibration, limitations, ADRs | Reviewer, auditor | Structured, versioned documentation; back-link from every product figure | Limitations as first-class content, not fine print | **P1** |
| **Gobernar** | Reports / exports | Generate the director brief, investment memo, GIS package, audit dossier | All | Official templates; paginated preview; GeoJSON/CSV | Every report inherits class badges and confidence notes — no exception | P2 |
| **Gobernar** | Configuration / territorial management | Register territories, thresholds, roles. Prepare multi-park without overpromising | Administrator | Sober forms; OAPN templates from v1.2 | Each territory inherits its own validation state (unvalidated by default) | P3 (full v3.0) |

---

## 7. Design system evolution rules

The existing SNTO system (institutional navy + light canvas, three deliberate palettes, Source Sans 3 / Source Serif 4 / Source Code Pro, accented cards) is correct and is **preserved intact**. The evolution adds **rules of use, not new identity elements**.

### Layout & spacing
- **One decision per region.** Each screen block supports a single question; mixing state, urgency, and management in the same grid is prohibited.
- **Spacing scale 4/8/12/16/24/32 px**, with a mandatory level jump between the **decision layer** (generous, 24–32) and the **analysis layer** (dense, 8–12). Density is an analyst privilege, not the default state.
- **Home-page rule:** maximum 4 header figures, 1 action list, 1 visual. Everything else is one click away.

### Typographic hierarchy
The existing scale is kept and given **intent**:
- **Decision value** `1.45rem/700` — reserved for figures that demand action.
- **Context value** `1.05rem/600` — for watch figures.
- **Micro-labels** uppercase `0.65–0.72rem` with `0.07em` — metadata only, never for in-flow content.

KPIs lose the universal right to the maximum size: **typographic hierarchy now encodes urgency.**

### Card hierarchy & density
- **Decision card** (3px top accent, feather shadow): only in the Decidir layer; maximum 5 per view.
- **Asset card** (4px left accent): lists and queues; accent color is dictated by **severity, never tier**.
- **Evidence card** (no accent, hairline border): Diagnosticar/Evidenciar layers. The absence of an accent means *"this informs, it does not urge"*.

### Palette-precedence rule
Within a single module **only one palette dominates** — traffic-light in operations, indigo in investment, provenance in audit; the other two are demoted to small badges.

---

## 8. Scientific visualization rules

**Objective:** make the datum hard to misread. **Transversal rule:** *nothing may look more precise, more validated, or more observed than it is.*

| Visualization | What is shown | Never hidden | Uncertainty & confidence | Evidence class |
| --- | --- | --- | --- | --- |
| **Observed vs baseline vs threshold** | The three references on the same canvas: value (solid), baseline (grey continuous), threshold (red dashed, labeled) | How the baseline was built (window, years); distance to threshold | Band over the baseline; threshold-crossing confidence as a badge | Badge in legend; derived baseline = dotted |
| **Confidence score (DCS)** | Discrete level + value + component decomposition on expand | Which component drags confidence down; what would raise it | Confidence **is** the visualization; no spurious decimals (68, not 68.4) | Components labeled by input class |
| **Uncertainty range** | Band or error bar coupled to the value ("35 ± 6"); in tables, a range column | That error propagation is partial (standard note while it is) | The range never collapses to save space; it abbreviates ("±6"), it is not removed | Estimated vs calculated ranges distinguished in tooltip |
| **Temporal trend** | 2021–2026 series with seasonality; ▲▼ deltas with explicit comparison period | Data gaps (clouds, no scene) as visible gaps, never silently interpolated | Trend band; change significance (test) as annotation | Solid = observed; dotted = derived/estimated |
| **Anomaly** | Deviation from seasonal baseline, with magnitude and duration | Discarded anomalies and their reason (logged false positive) | Probability of a real anomaly vs artifact; visible detection threshold | Alerts only on observed/calculated class |
| **Intervention priority (tiers)** | Existing indigo→slate scale, Roman numerals, assignment criterion on expand | That the tier is a **derived recommendation, not a measurement** | Tier confidence attached; assets on the boundary between tiers flagged | Class calculated; estimated inputs listed |
| **Ecological stress (EHS)** | Existing severity ramp + 3px bar + text label (Critical…Minimal); grey `#9e9e9e` = no data | "No data" as its own category — never painted as healthy | EHS with range in the asset card; scene quality that underpins it | Class badge next to the value in every card |
| **Tourism pressure (TPI)** | Index per asset and season; declared count sources | That pressure is partly inferred; tourism-vs-climate attribution as hypothesis (SCM) | Causal-attribution confidence always attached to the causal statement | Mixed: observed and estimated components broken out |
| **Carrying capacity** | Range [min–max] with assumptions; current occupancy against the range | The calculation assumptions; that no single true number exists | Represented as a zone, never a single line | Class estimated, visible in the chart itself |
| **Budget recommendation** | Rounded range ("€120–150k"), line items, criterion; never false precision to the euro | Basis of the calculation and sensitivity to cost assumptions | Low/central/high scenarios; confidence of the motivating priority | Class simulated as a badge printed also in exports |
| **Field-validation status** | State per asset/indicator: unvalidated · in campaign · verified (date, method, owner) | The proportion of the system still unvalidated (honest global figure) | Validation raises shown confidence; its absence visibly degrades it | Field verification is the only path to "observed" for attribution |

### Maps, charts, reports
- **Map layer control:** each layer declares its evidence class in its own legend; simulated layers are drawn with hatching or dashed stroke, **never** the same solid fill as observed ones. Cloud cover and scene gaps are a **toggleable layer, not a footnote**.
- **Chart annotation:** every series carries baseline, threshold, and event annotations (campaigns, fires, closures) directly on the canvas; the existing convention **NDVI solid green / NDMI dotted blue** is kept and extended: **dotted = derived, solid = observed**.
- **Report language:** exports use the documentary palette (Source Serif 4, academic blue `#1a4f9c`) already defined — the same language as the source report — with printed evidence-class badges and a **mandatory limitations note on the last page**.

### Accessibility (system rules)
- **No meaning by color alone:** every state carries redundant text or glyph (critical with the three palettes and the EHS ramp).
- **Minimum AA contrast** on all text over navy and over pale tints; audit `#f9a825` and `#b3b8d4` over white in particular.
- **Minimum body 14px** in product (current 0.62–0.68rem restricted to metadata); touch targets ≥ 44px on map controls.
- **Textual equivalents** for maps and charts (accessible data table per view); full keyboard navigation as a v2.0 acceptance criterion.
- **Reduced-density mode** as a user preference, not a degraded version.

---

## 9. Evidence-state visual language

The existing provenance palette is elevated from **label** to **presentation grammar**. The four classes (ADR-004):

### OBSERVED
Real satellite or field data. The **only** class with the right to solid fill, full value `1.45rem`, and use in executive header figures.

### CALCULATED
Deterministic derivation from observed data (indices, EHS). Full presentation with a badge; method linked one click away.

### ESTIMATED
Proxy or calibration (socioeconomics, carrying capacity). **Always with a range**; dotted line in series; **excluded from header figures**.

### SIMULATED
Scenario or synthetic datum (simulator, demo). Hatched/dashed in maps and charts; context banner in the module; **never mixed into an aggregate with real classes**.

### Governing rules
- **Degradation rule:** an aggregate inherits the **weakest class** of its inputs and declares it ("includes estimated components").
- **Header rule:** figures in the Decidir layer admit only **observed/calculated**; estimated and simulated live in their own modules with their own framing.
- **Export rule:** class badges are printed on every report and accompany every exported datum (`evidence_class` column in CSV/GeoJSON).
- **Anti-regression rule:** no redesign may reduce the current visibility of provenance; the acceptance criterion is **"more separation than today, never less"**.

---

## 10. Dashboard simplification strategy

1. **From 10 KPIs to 3–4 decision figures.** The ten current indicators are **not eliminated**: six migrate to "Protected-area health" and thematic modules. Nothing is lost; everything is relocated.
2. **From view modes to per-role home pages.** Technical / Manager / Audit become the layers **Diagnosticar / Decidir / Gobernar** with their own navigation, instead of a density switch.
3. **Methodology one click away, not inline.** Each figure keeps its "SNTO technical basis" as a link to the Methodology module; expanders disappear from the primary flow.
4. **The asset as a page.** The asset card (today a card in a row) becomes the **central page of the product**: state, evidence, history, action — **80% of the product's links land there**.
5. **Budget without false precision.** Rounded ranges throughout the Decidir layer; euro-level detail stays in the simulator, marked **simulated**.
6. **Measurable success:** director time-to-decision **< 2 minutes without a narrator**; **zero** evidence-class confusions in user testing; home-page load with **≤ 7 blocks**.

---

## 11. Design roadmap

| Phase | Design objective | Technical prerequisite | Risk · impact | What NOT to do |
| --- | --- | --- | --- | --- |
| **v1.1** | Only essential evidence clarity: reinforce class badges where missing, standard uncertainty note on budgets, director brief as a **light prototype** (A04) without touching the structure | PR #1 resolution (real Sentinel-2 2021–2026); CI green; nothing depends on PR #7 (closed, contaminated) | Risk: destabilizing deployed v1.0 · Impact: scientific trust preserved | No broad visual exploration, no tab reorganization, no new components (ADR-007) |
| **v1.2** | Controlled-expansion UX: evidence and report views for pilots, definition of the asset-state model (A08, design), first GIS export, institutional report template | v1.1 stabilized; validation protocol defined (A03); pilot partners | Risk: overpromising multi-park maturity · Impact: viable paid pilots (65%) | No major UI redesign, no tenancy, no national benchmarking |
| **Pre-v2** | **Technical gate, not a design gate:** modularization of `app.py` (UI / state / copy / orchestration separated), page-based surface, persistent backend designed (ADR-006). In parallel: v2.0 design spec, wireframes and prototypes **outside the product** | Page-architecture decision; `app.py` CSS component inventory moved into a formal system | Risk: redesigning over the monolith and duplicating the work · Impact: enables everything else | Do not implement any v2.0 screen in production before this gate |
| **v2.0** | Full UX/UI evolution: Decidir/Diagnosticar/Evidenciar/Gobernar layers, per-role home pages, intervention lifecycle, field verification, AA accessibility as an acceptance criterion | `app.py` modularized; identity and roles; persistence; versioned API (A11–A13) | Risk: XL scope, looking like generic SaaS · Impact: real candidate for institutional adoption | Do not dilute the SNTO identity or relax evidence separation for "polish" |
| **v3.0** | Institutional maturity: multi-park, benchmarking and OAPN rollups, complete audit dossier, public transparency portal where appropriate, internationalization | v2.0 operational; multi-territory validation (A14); deployment governance (ADR-009) | Risk: unproven generalization across habitats · Impact: category leadership | Do not launch a public portal before internal evidence is auditable |

---

## 12. Risks of implementing too early

- **Redesigning over the monolith:** every new screen written into `app.py` (2,890 lines of UI + state + copy + logic) will be rewritten during modularization — double work and regressions in the deployed v1.0.
- **Branch contamination:** the precedent exists — PR #7 was born docs-only and ended with 151 functional files. Visual work mixed with stabilization would repeat the pattern (rule: **do not mix v2.0 into v1.1/v1.2**).
- **Polish that erodes honesty:** simplifying without the evidence rules of sections 8–9 tends to hide uncertainty and caveats — exactly what is prohibited (ADR-004, R01, R04).
- **Appearance ahead of validation:** an interface more institutional than the evidence backing it invites overclaiming to public buyers (R05); field validation (v1.2) must precede the visual rhetoric.
- **Convergence to generic SaaS:** rushing the redesign tends to import commercial-dashboard patterns; SNTO's sober identity is a **trust asset, not aesthetic debt**.

---

## 13. What must wait until `app.py` modularization

Must wait for the pre-v2 technical gate (modularization + persistence + identity):

- Per-role home pages and page-based navigation.
- Intervention lifecycle and field verification (also require persistence and identity).
- Asset catalogue as a page.
- Audit center.
- Report generator.
- Any restructuring of the navigation system.

---

## 14. What can be done now without touching product code

Can proceed immediately, **without touching product code**:

- Complete v2.0 design specification (this document and the linked design system).
- Wireframes and external prototypes (outside the product).
- Formalization of the design system.
- User-testing protocol with real managers.
- The evidence-clarity micro-improvements scoped strictly to v1.1.

---

## 15. Final decision

> ## SNTO is not ready for visual redesign implementation now.

**Is SNTO ready to implement the visual redesign now? No. The evidence is conclusive.**

- `app.py` remains a monolith of ~2,890 lines (software quality 42/100).
- PR #1 — the real temporal evidence the redesign must display — is unmerged and conflicting.
- There is no persistence, identity, or audit (enterprise readiness 28/100).
- ADR-007 fixes the UI evolution at v2.0, **after** modularization.

Implementing now would duplicate work, risk the deployed v1.0, and tempt overclaiming. What **is** ready — and what this specification begins — is the **design**: specification, information architecture, evidence rules, and prototypes outside the product, so that the v2.0 window opens with the design already resolved.

**Recommendation:** adopt the target experience of sections 3–5 as the **v2.0 specification**; execute in v1.1 **only** the evidence-clarity improvements; use v1.2 for pilot and report views; and gate everything else on the pre-v2 milestone (modularization + persistence). **Design now, implement later.**

---

*Sources: CLAUDE.md · MASTER_STRATEGIC_INDEX.md · docs/ai-context/CLAUDE_CODE_HANDOFF_2026.md · docs/ux/\* · docs/product/\* · docs/strategy/\* · docs/roadmap/\* · docs/reviews/2026/\* · docs/methodology/\* · ADR-001–010 · SNTO Design System. Strategy document — implies no code changes, commits, or merges.*
