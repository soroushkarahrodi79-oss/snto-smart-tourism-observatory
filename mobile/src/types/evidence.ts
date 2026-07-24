export const EVIDENCE_CLASSES = [
  'real',
  'calibrated',
  'simulated',
  'synthetic',
  'missing',
] as const;

export type EvidenceClass = (typeof EVIDENCE_CLASSES)[number];

export type ValidationStatus = 'field_validated' | 'not_field_validated' | 'not_applicable';

export interface EvidenceMetadata {
  class: EvidenceClass;
  source: string;
  observedAt: string | null;
  fetchedAt: string;
  validationStatus: ValidationStatus;
  limitation: string;
}

export const EVIDENCE_LABELS: Record<EvidenceClass, string> = {
  real: 'Real',
  calibrated: 'Calibrado',
  simulated: 'Simulado',
  synthetic: 'Sintético',
  missing: 'Sin evidencia',
};
