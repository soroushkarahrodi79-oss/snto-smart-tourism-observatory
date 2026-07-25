import type { EvidenceMetadata } from '@/types/evidence';

export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface HomeSummary {
  territoryName: string;
  assetCount: number;
  openAlertCount: number;
  updatedAt: string;
  evidence: EvidenceMetadata;
}

export interface AssetLocation {
  latitude: number;
  longitude: number;
}

export interface TourismAsset {
  id: string;
  name: string;
  category: string;
  municipality: string;
  summary: string;
  evidence: EvidenceMetadata;
  // Fase 2 (ADR-014): a rough map-pin centroid, or null when the backend
  // couldn't derive one. No map SDK renders this yet (ADR-013 defers that
  // as a separate licensing decision) — the data is available for when it does.
  location: AssetLocation | null;
}

export interface ObservatoryAlert {
  id: string;
  title: string;
  severity: AlertSeverity;
  area: string;
  summary: string;
  createdAt: string;
  evidence: EvidenceMetadata;
}

export interface MobileRepository {
  getHomeSummary(): Promise<HomeSummary>;
  listAssets(): Promise<TourismAsset[]>;
  getAsset(assetId: string): Promise<TourismAsset | null>;
  listAlerts(): Promise<ObservatoryAlert[]>;
  getAlert(alertId: string): Promise<ObservatoryAlert | null>;
}
