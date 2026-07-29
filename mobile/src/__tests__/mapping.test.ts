import type { AlertOutDto, ManagedAssetOutDto, TerritorySummaryOutDto } from '@/api/schemas';
import {
  mapAlert,
  mapAlertSeverity,
  mapAsset,
  mapEvidence,
  mapHomeSummary,
} from '@/data/http/mapping';

const FETCHED_AT = '2026-07-25T10:00:00.000Z';

describe('mapEvidence', () => {
  it('carries a real evidence class through with an honest limitation', () => {
    const evidence = mapEvidence('real', '2026-06-01T00:00:00.000Z', FETCHED_AT);
    expect(evidence).toEqual({
      class: 'real',
      source: 'SNTO /api/v2',
      observedAt: '2026-06-01T00:00:00.000Z',
      fetchedAt: FETCHED_AT,
      validationStatus: 'not_field_validated',
      limitation: expect.stringContaining('Sin validación de campo'),
    });
  });

  it('degrades an unrecognised class to missing rather than guessing', () => {
    const evidence = mapEvidence('not-a-real-class', null, FETCHED_AT);
    expect(evidence.class).toBe('missing');
    expect(evidence.validationStatus).toBe('not_applicable');
  });

  it('treats a null class as missing, not fabricated', () => {
    const evidence = mapEvidence(null, null, FETCHED_AT);
    expect(evidence.class).toBe('missing');
    expect(evidence.observedAt).toBeNull();
  });
});

describe('mapAlertSeverity', () => {
  it.each([
    ['CRITICAL_INTERVENTION', 'critical'],
    ['URGENT_MONITORING', 'warning'],
    ['PREVENTIVE_ACTION', 'warning'],
    ['NORMAL', 'info'],
  ] as const)('%s -> %s', (level, expected) => {
    expect(mapAlertSeverity(level)).toBe(expected);
  });

  it('degrades an unrecognised level to the calmest severity, never throws', () => {
    expect(mapAlertSeverity('SOMETHING_NEW')).toBe('info');
  });
});

describe('mapAsset', () => {
  const baseDto: ManagedAssetOutDto = {
    id: 1,
    territory_id: 1,
    external_asset_id: 'pnsg-nat-001',
    name: 'Laguna de Peñalara',
    asset_type: 'trail',
    region: 'Comunidad de Madrid',
    status: 'detected',
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
    latitude: 40.82,
    longitude: -3.96,
    latest_observed_at: '2026-06-01T00:00:00.000Z',
    latest_evidence_class: 'calibrated',
  };

  it('uses the external id, not the internal numeric id', () => {
    expect(mapAsset(baseDto, FETCHED_AT).id).toBe('pnsg-nat-001');
  });

  it('maps a present centroid to a location', () => {
    expect(mapAsset(baseDto, FETCHED_AT).location).toEqual({
      latitude: 40.82,
      longitude: -3.96,
    });
  });

  it('maps a missing centroid to a null location, never a fabricated point', () => {
    const dto: ManagedAssetOutDto = { ...baseDto, latitude: null, longitude: null };
    expect(mapAsset(dto, FETCHED_AT).location).toBeNull();
  });

  it('carries the freshest evidence class through', () => {
    expect(mapAsset(baseDto, FETCHED_AT).evidence.class).toBe('calibrated');
  });

  it('an asset with no observation yet gets missing evidence, not a guess', () => {
    const dto: ManagedAssetOutDto = {
      ...baseDto,
      latest_observed_at: null,
      latest_evidence_class: null,
    };
    expect(mapAsset(dto, FETCHED_AT).evidence.class).toBe('missing');
  });
});

describe('mapAlert', () => {
  const baseDto: AlertOutDto = {
    id: 7,
    asset_id: 42,
    level: 'CRITICAL_INTERVENTION',
    risk_score: 0.91,
    triggered_rules: ['score=0.910 > critical_threshold=0.85'],
    status: 'open',
    reason: null,
    created_at: '2026-06-01T00:00:00.000Z',
  };

  it('stringifies the internal id (no external id exists for alerts)', () => {
    expect(mapAlert(baseDto, FETCHED_AT).id).toBe('7');
  });

  it('includes the risk score in the title, derived not fabricated', () => {
    expect(mapAlert(baseDto, FETCHED_AT).title).toContain('0.91');
  });

  it('never claims a specific evidence class the DTO does not carry', () => {
    expect(mapAlert(baseDto, FETCHED_AT).evidence.class).toBe('missing');
  });

  it('falls back to the triggered rules when there is no dismissal reason', () => {
    expect(mapAlert(baseDto, FETCHED_AT).summary).toContain('critical_threshold');
  });

  it('uses the reason when present (e.g. a dismissed alert)', () => {
    const dto: AlertOutDto = { ...baseDto, reason: 'Falso positivo confirmado en campo' };
    expect(mapAlert(dto, FETCHED_AT).summary).toBe('Falso positivo confirmado en campo');
  });
});

describe('mapHomeSummary', () => {
  const baseDto: TerritorySummaryOutDto = {
    territory_id: 1,
    slug: 'pnsg',
    name: 'PNSG',
    asset_count: 8,
    open_alert_count: 3,
    updated_at: '2026-06-01T00:00:00.000Z',
    evidence_class: 'real',
  };

  it('uses the real updated_at when present', () => {
    expect(mapHomeSummary(baseDto, FETCHED_AT).updatedAt).toBe('2026-06-01T00:00:00.000Z');
  });

  it('falls back to the fetch moment for an empty territory, never fabricated', () => {
    const dto: TerritorySummaryOutDto = {
      ...baseDto,
      asset_count: 0,
      updated_at: null,
      evidence_class: null,
    };
    const summary = mapHomeSummary(dto, FETCHED_AT);
    expect(summary.updatedAt).toBe(FETCHED_AT);
    expect(summary.evidence.class).toBe('missing');
  });
});
