import type {
  AlertOutDto,
  ManagedAssetOutDto,
  TerritorySummaryOutDto,
} from '@/api/schemas';
import type {
  AlertSeverity,
  AssetLocation,
  HomeSummary,
  ObservatoryAlert,
  TourismAsset,
} from '@/data/mobileRepository';
import { EVIDENCE_CLASSES, type EvidenceClass, type EvidenceMetadata } from '@/types/evidence';

/**
 * Pure DTO -> domain mappers for the HTTP repository (Fase 2, ADR-014).
 *
 * Kept separate from the repository (which only orchestrates fetch calls) so
 * every mapping decision — evidence honesty, alert-severity bucketing — is
 * independently unit-testable without a network mock.
 */

const LIMITATION_BY_CLASS: Record<EvidenceClass, string> = {
  real: 'Observación satelital real (Sentinel-2). Sin validación de campo — la campaña (#26) sigue pendiente.',
  calibrated: 'Reconstrucción calibrada con juicio experto, no observación directa. Sin validación de campo.',
  simulated: 'Escenario o simulación, no una observación. Sin validación de campo.',
  synthetic: 'Dato sintético de demostración; no representa condiciones reales.',
  missing: 'Sin observación registrada todavía para este elemento.',
};

function isEvidenceClass(value: string): value is EvidenceClass {
  return (EVIDENCE_CLASSES as readonly string[]).includes(value);
}

/**
 * Builds an honest EvidenceMetadata from a backend evidence-class string.
 *
 * `evidenceClass` is `Observation.source` (or null when the asset/territory
 * has no observation yet) — the canonical vocabulary is shared verbatim with
 * the backend (src.platform.evidence.EvidenceClass), so an unrecognised
 * string degrades to `missing` rather than being guessed. `validationStatus`
 * is `not_field_validated` for any present class (true project-wide: the #26
 * campaign has not run) and `not_applicable` when there is nothing to
 * validate at all.
 */
export function mapEvidence(
  evidenceClass: string | null,
  observedAt: string | null,
  fetchedAt: string,
): EvidenceMetadata {
  const resolvedClass: EvidenceClass =
    evidenceClass && isEvidenceClass(evidenceClass) ? evidenceClass : 'missing';
  return {
    class: resolvedClass,
    source: 'SNTO /api/v2',
    observedAt: observedAt ?? null,
    fetchedAt,
    validationStatus: resolvedClass === 'missing' ? 'not_applicable' : 'not_field_validated',
    limitation: LIMITATION_BY_CLASS[resolvedClass],
  };
}

const SEVERITY_BY_LEVEL: Record<string, AlertSeverity> = {
  CRITICAL_INTERVENTION: 'critical',
  URGENT_MONITORING: 'warning',
  PREVENTIVE_ACTION: 'warning',
  NORMAL: 'info',
};

/** Never throws on an unrecognised level — degrades to the calmest severity. */
export function mapAlertSeverity(level: string): AlertSeverity {
  return SEVERITY_BY_LEVEL[level] ?? 'info';
}

const LEVEL_LABEL: Record<string, string> = {
  CRITICAL_INTERVENTION: 'Intervención crítica',
  URGENT_MONITORING: 'Vigilancia urgente',
  PREVENTIVE_ACTION: 'Acción preventiva',
  NORMAL: 'Normal',
};

function mapLocation(
  latitude: number | null,
  longitude: number | null,
): AssetLocation | null {
  return latitude !== null && longitude !== null ? { latitude, longitude } : null;
}

export function mapAsset(dto: ManagedAssetOutDto, fetchedAt: string): TourismAsset {
  return {
    id: dto.external_asset_id,
    name: dto.name,
    category: dto.asset_type,
    municipality: dto.region,
    summary: `Estado: ${dto.status}.`,
    evidence: mapEvidence(dto.latest_evidence_class, dto.latest_observed_at, fetchedAt),
    location: mapLocation(dto.latitude, dto.longitude),
  };
}

export function mapAlert(dto: AlertOutDto, fetchedAt: string): ObservatoryAlert {
  const levelLabel = LEVEL_LABEL[dto.level] ?? dto.level;
  return {
    id: String(dto.id),
    title: `${levelLabel} · riesgo ${dto.risk_score.toFixed(2)}`,
    severity: mapAlertSeverity(dto.level),
    // The alert DTO only carries asset_id (no joined asset name) — an honest,
    // non-fabricated fallback rather than an extra per-alert round trip.
    // TODO(Fase 3+): a joined /alerts read that includes the asset name.
    area: `Activo #${dto.asset_id}`,
    summary: dto.reason ?? `Reglas activadas: ${dto.triggered_rules.join(', ') || 'ninguna registrada'}.`,
    createdAt: dto.created_at,
    // AlertOut carries no evidence-class field of its own (unlike
    // Observation) — never assumed 'real'; degrades honestly to 'missing'
    // rather than guessing the provenance of the data that raised it.
    evidence: mapEvidence(null, dto.created_at, fetchedAt),
  };
}

/**
 * `updatedAt` falls back to the fetch moment when the territory has no
 * observation yet — that only claims "as of this check", never a fabricated
 * territorial freshness.
 */
export function mapHomeSummary(
  dto: TerritorySummaryOutDto,
  fetchedAt: string,
): HomeSummary {
  return {
    territoryName: dto.name,
    assetCount: dto.asset_count,
    openAlertCount: dto.open_alert_count,
    updatedAt: dto.updated_at ?? fetchedAt,
    evidence: mapEvidence(dto.evidence_class, dto.updated_at, fetchedAt),
  };
}
