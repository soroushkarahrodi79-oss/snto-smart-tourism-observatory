# SNTO Phase 1.0 — Evidence → Decision Matrix & Product Audit

**Authority:** ADR-016, [`SCIENTIFIC_PRODUCT_CONTRACT.md`](SCIENTIFIC_PRODUCT_CONTRACT.md).
Answers one question: *given an evidence combination, what is SNTO actually
allowed to do?* Then audits current product surfaces against the answer.

Legend for uses: **M** monitor/context · **F** flag & prioritize investigation/
inspection · **R5a** recommend monitoring/inspection · **R5b** recommend a
resource-committing intervention · **Rr** recommend a restrictive action
(closure/quota) · **P** public/institutional reporting · **E** evaluate
effectiveness · **C** claim causality/regeneration. ✅ authorized · 🟡 authorized
*with explicit label* · ⛔ prohibited.

## 1. Evidence combination → authorized use

| Evidence combination | M | F | R5a | R5b | Rr | P | E | C | Max ladder |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Sentinel REAL only** (today's PNSG state) | ✅ | ✅ | ✅ | ⛔ | ⛔ | 🟡 | ⛔ | ⛔ | L5a |
| Sentinel REAL + CALIBRATED climate | ✅ | ✅ | ✅ | ⛔ | ⛔ | 🟡 | ⛔ | ⛔ | L5a |
| Sentinel REAL + MITMA municipal mobility | ✅ (macro only) | ✅ | ✅ | ⛔ | ⛔ | 🟡 | ⛔ | ⛔ | L5a |
| Sentinel REAL + **real** asset-level visitor pressure | ✅ | ✅ | ✅ | ⛔ | ⛔ | 🟡 | ⛔ | ⛔ | L5a |
| Simulated SCM + REAL EHS | 🟡 (hypothesis) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L2 (hypothesis) |
| Visitor pressure **without** ecological observation | 🟡 (context) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L1 |
| Synthetic fixture only | 🟡 (demo) | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | L0 |
| Real intervention record + post-intervention REAL satellite (**no field**) | ✅ | ✅ | ✅ | ⛔ | ⛔ | 🟡 | ⛔ | ⛔ | L5a (not L6 — no comparator/field) |
| **Full: before/after + comparator + pressure + complete mgmt record + field (#26)** | ✅ | ✅ | ✅ | ✅ | 🟡 (with owner policy) | ✅ | ✅ | ✅ | L7 |

**Key results (acceptable non-answers):**
- With Sentinel REAL alone, the ceiling is **L5a**: recommend monitoring/
  inspection. Recommending a **resource-committing** intervention (R5b) is **not**
  authorized on satellite alone — even non-restrictive ones — and **effectiveness
  and causality are not authorized** ("not enough evidence" is the correct output).
- **Restrictive** recommendations (Rr) are never authorized below the full row,
  and even there require explicit owner policy sign-off.
- Municipal MITMA never upgrades a claim to trail-level pressure.
- A before/after change **without a comparator** is only an L2 observation, never
  L6 effectiveness.

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
| Visitor-pressure readiness | 🟡 AMBER | Correctly `INSUFFICIENT_EVIDENCE`; AMBER only because no real *target* feed yet |
| Synthetic fixtures | 🟢 GREEN | Classified `SYNTHETIC`; decision gates block them (Phase 0.5E) |
| **TIS / intervention euro-efficiency verdict** | 🔴 **RED-RISK** | Register item **C-10 (OVERSTATED)**: a benefit-per-euro verdict derived from unsourced SIMULATED elasticity constants. Owner decision Q-05 declares the coefficients illustrative-only; **the live UI text must be re-verified** to ensure it does not present them as observed/forecast effect. Not fixable in this docs PR — tracked as a corrective follow-up. |
| **LAC/ROS capacity at standard** | 🟢 GREEN | **Fixed in PR #158 (WP-C11).** `capacity_at_standard` now requires an `attribution` argument and returns `None` unless the SCM class is `LOCALIZED_IMPACT`, so the quota-shaped figure is withheld for the **165/218** `LANDSCAPE_DRIVEN` trails (and the 29 MIXED) whose deficit the formula cannot attribute to visitors; the `tab_portfolio` surface now applies the canonical `supports()` gate, so SYNTHETIC inputs authorize nothing. *History:* the initial audit missed this surface; it was recorded RED-RISK, then corrected. |
| "Economía Regenerativa" (socioeconomic tab title) | 🟡 AMBER | A socioeconomic *vision framing* label (SVI/jobs), not an evaluated ecological outcome — borderline; recommend a scope caveat or rename so a standing header is not read as a regeneration claim |
| Effectiveness / regenerative-outcome evaluation | ⚪ GREY | Not built; L6–L7 blocked by #26 + Pillars 1&3 |
| Management-response record | ⚪ GREY | Schema stub only; recording contract is WP-3 |

**One RED-RISK surface remains.** The TIS euro-efficiency verdict (C-10) is a
pre-existing `OVERSTATED` claims-register item whose live UI text must be
re-verified against this contract — tracked as **WP-C10**, a runtime-text issue.
The **LAC/ROS capacity-at-standard** surface — the second RED-RISK finding, which
the initial audit had missed — was **resolved in PR #158 (WP-C11)** and is now
GREEN. The remaining AMBERs are label-dependent, not overclaiming today.

> **Exit-criterion consequence (§J.3).** The contract's Definition of Done requires
> that the audit record **no RED surface**. One remains (C-10 / WP-C10). Phase 1.0
> therefore does **not** close on this criterion until WP-C10 lands; the criterion
> is not weakened to fit the finding.

## 3. What cannot currently be authorized (explicit)

- Any statement that management **caused** an ecological change.
- Any "**regenerative outcome**" as an evaluated result.
- Any satellite↔field "**validated**" claim.
- Any **restrictive** management action (closure / quota / access limit).
- Any **trail-level footfall** figure derived from municipal mobility.
- Any asset-level **capacity or quota figure** derived from an ecological deficit
  that the system's own attribution does not assign to visitor use.
- Any forecasting/ML output presented as decision-grade for visitor pressure.
