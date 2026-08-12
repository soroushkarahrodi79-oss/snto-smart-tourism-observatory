# SNTO Phase 1.0 — Evidence → Decision Matrix & Product Audit

**Authority:** ADR-016, [`SCIENTIFIC_PRODUCT_CONTRACT.md`](SCIENTIFIC_PRODUCT_CONTRACT.md).
Answers one question: *given an evidence combination, what is SNTO actually
allowed to do?* Then audits current product surfaces against the answer.

Legend for uses: **M** monitor/context · **F** flag & prioritize investigation ·
**Rn** recommend non-restrictive action · **Rr** recommend restrictive action ·
**P** public/institutional reporting · **E** evaluate effectiveness · **C** claim
causality/regeneration. ✅ authorized · 🟡 authorized *with explicit label* · ⛔
prohibited.

## 1. Evidence combination → authorized use

| Evidence combination | M | F | Rn | Rr | P | E | C | Max ladder |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Sentinel REAL only** (today's PNSG state) | ✅ | ✅ | ✅ | ⛔ | 🟡 | ⛔ | ⛔ | L5 |
| Sentinel REAL + CALIBRATED climate | ✅ | ✅ | ✅ | ⛔ | 🟡 | ⛔ | ⛔ | L5 |
| Sentinel REAL + MITMA municipal mobility | ✅ (macro only) | ✅ | ✅ | ⛔ | 🟡 | ⛔ | ⛔ | L5 |
| Sentinel REAL + **real** visitor pressure (asset-level) | ✅ | ✅ | ✅ | ⛔ | 🟡 | ⛔ | ⛔ | L5 |
| Simulated SCM + REAL EHS | 🟡 (hypothesis) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L2 (hypothesis) |
| Visitor pressure **without** ecological observation | 🟡 (context) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L1 |
| Synthetic fixture only | 🟡 (demo) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L0 |
| Real intervention record + post-intervention REAL satellite (no field) | ✅ | ✅ | ✅ | ⛔ | 🟡 | ⛔ | ⛔ | L5 (not L6 — field missing) |
| **Full: before/after + pressure + complete mgmt record + field (#26)** | ✅ | ✅ | ✅ | 🟡 (with owner policy) | ✅ | ✅ | ✅ | L7 |

**Key results (acceptable non-answers):**
- With Sentinel REAL alone, **effectiveness and causality are not authorized** —
  "not enough evidence" is the correct output.
- **Restrictive** recommendations (Rr) are never authorized below the full row,
  and even there require explicit owner policy sign-off.
- Municipal MITMA never upgrades a claim to trail-level pressure.

## 2. Current product-surface audit against the contract

**GREEN** — already satisfies the contract · **AMBER** — capability exists,
evidence/validation incomplete (labelled, tracked) · **RED** — would violate the
contract / overclaim · **GREY** — future capability, no evidence.

| Surface | Verdict | Basis (verified) |
|---|:--:|---|
| Executive dashboard / portfolio | 🟢 GREEN | Financial figures invariant across views; evidence labels present |
| Urgent actions | 🟢 GREEN | Backed by persistence services; no causal/validated language |
| Reports (executive brief, GIS export) | 🟢 GREEN | Two asset sets labelled distinctly; REAL-trend GIS only |
| CETS readiness | 🟢 GREEN | `resolve_signals()` live probe; **REAL is hard ceiling**, never "validated" |
| PRUG monitoring | 🟢 GREEN | Framed as seasonal early-warning (ΔEHS), never a compliance verdict |
| Executive briefs / dossier | 🟢 GREEN | Auto-sections regenerated from live sources; drift-checked in CI |
| API v2 responses | 🟢 GREEN | Fields degrade to `null`/`missing`; no evidence-class fabrication |
| Persistent assets / alerts | 🟢 GREEN | Alerts carry no `real` assumption; honest degradation |
| EHS / satellite trends | 🟢 GREEN | REAL, with valid-pixel accounting; Mann-Kendall p-values shown |
| SCM (spatial causal model) | 🟡 AMBER | Runs **simulated α-decay**; labelled "Hipótesis causal" + "no es medición causal ni una causa confirmada" — correct, but depends on that label never being dropped |
| Visual Change Explorer / temporal GIF | 🟡 AMBER | REAL imagery; must keep "visual change ≠ validated impact" framing |
| Visitor-pressure readiness | 🟡 AMBER | Correctly `INSUFFICIENT_EVIDENCE`; AMBER only because no real feed yet |
| Synthetic fixtures | 🟢 GREEN | Classified `SYNTHETIC`; decision gates block them (Phase 0.5E) |
| "Economía Regenerativa" (socioeconomic tab title) | 🟡 AMBER | A socioeconomic *framing* label, not an evaluated ecological outcome — keep it clearly scoped to SVI/jobs, never adjacent to a satellite-change claim |
| Effectiveness / regenerative-outcome evaluation | ⚪ GREY | Not built; L6–L7 blocked by #26 + pillars 1&3 |
| Management-response record | ⚪ GREY | Schema stub only; recording contract is WP-3 |

**No RED surfaces found.** SNTO's current surfaces do not imply more than the
evidence supports. The three AMBERs are *label-dependent*, not overclaiming
today; they are tracked as follow-ups, not blockers, and none requires a code
change in Phase 1.0.

## 3. What cannot currently be authorized (explicit)

- Any statement that management **caused** an ecological change.
- Any "**regenerative outcome**" as an evaluated result.
- Any satellite↔field "**validated**" claim.
- Any **restrictive** management action (closure / quota / access limit).
- Any **trail-level footfall** figure derived from municipal mobility.
- Any forecasting/ML output presented as decision-grade for visitor pressure.
