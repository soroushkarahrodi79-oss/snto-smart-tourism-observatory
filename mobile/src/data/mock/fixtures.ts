import type {
  HomeSummary,
  ObservatoryAlert,
  TourismAsset,
} from '@/data/mobileRepository';
import type { EvidenceMetadata } from '@/types/evidence';

const FIXTURE_TIME = '2026-07-24T10:00:00.000Z';

const syntheticEvidence = (limitation: string): EvidenceMetadata => ({
  class: 'synthetic',
  source: 'Fixture local de demostración SNTO Mobile',
  observedAt: FIXTURE_TIME,
  fetchedAt: FIXTURE_TIME,
  validationStatus: 'not_field_validated',
  limitation,
});

export const HOME_FIXTURE: HomeSummary = {
  territoryName: 'PNSG · demo móvil',
  assetCount: 3,
  openAlertCount: 2,
  updatedAt: FIXTURE_TIME,
  evidence: syntheticEvidence(
    'Resumen sintético para validar navegación; no representa condiciones territoriales actuales.',
  ),
};

export const ASSET_FIXTURES: TourismAsset[] = [
  {
    id: 'asset-demo-01',
    name: 'Mirador de demostración',
    category: 'Mirador',
    municipality: 'Municipio sintético Norte',
    summary: 'Activo ficticio para probar el detalle y la trazabilidad de evidencia.',
    evidence: syntheticEvidence('Activo inventado; no usar para planificación ni navegación.'),
    location: null,
  },
  {
    id: 'asset-demo-02',
    name: 'Sendero de demostración',
    category: 'Sendero',
    municipality: 'Municipio sintético Centro',
    summary: 'Recorrido ficticio incluido únicamente como fixture local.',
    evidence: syntheticEvidence('Trazado y estado no verificados en campo.'),
    location: null,
  },
  {
    id: 'asset-demo-03',
    name: 'Centro de visitantes demo',
    category: 'Equipamiento',
    municipality: 'Municipio sintético Sur',
    summary: 'Equipamiento ficticio para validar estados de lista.',
    evidence: syntheticEvidence('Ubicación, horarios y servicios no son datos reales.'),
    location: null,
  },
];

export const ALERT_FIXTURES: ObservatoryAlert[] = [
  {
    id: 'alert-demo-01',
    title: 'Alerta analítica sintética',
    severity: 'warning',
    area: 'Sector ficticio Norte',
    summary: 'Señal de demostración para probar jerarquía visual y detalle.',
    createdAt: FIXTURE_TIME,
    evidence: syntheticEvidence(
      'No es una restricción oficial ni una recomendación de seguridad.',
    ),
  },
  {
    id: 'alert-demo-02',
    title: 'Aviso de capacidad sintético',
    severity: 'info',
    area: 'Sector ficticio Centro',
    summary: 'Aviso inventado para comprobar el estado de lista.',
    createdAt: FIXTURE_TIME,
    evidence: syntheticEvidence(
      'No es información operativa; confirme siempre con fuentes oficiales.',
    ),
  },
];
