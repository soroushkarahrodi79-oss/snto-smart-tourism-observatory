import { z } from 'zod';

export const healthResponseSchema = z.object({
  status: z.literal('ok'),
  version: z.string(),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

// ── /api/v2 read contract (Fase 2, ADR-014) ─────────────────────────────────
// Mirrors src/api/v2/schemas.py exactly. Parsed with Zod so a backend shape
// drift fails loudly (ApiError('invalid_response')) instead of silently
// showing malformed data.

export const territoryOutSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name: z.string(),
  budget_eur: z.number(),
  created_at: z.string(),
});

export const territoryListResponseSchema = z.object({
  total: z.number(),
  territories: z.array(territoryOutSchema),
});

export const territorySummaryOutSchema = z.object({
  territory_id: z.number(),
  slug: z.string(),
  name: z.string(),
  asset_count: z.number(),
  open_alert_count: z.number(),
  updated_at: z.string().nullable(),
  evidence_class: z.string().nullable(),
});

export const managedAssetOutSchema = z.object({
  id: z.number(),
  territory_id: z.number(),
  external_asset_id: z.string(),
  name: z.string(),
  asset_type: z.string(),
  region: z.string(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  latest_observed_at: z.string().nullable(),
  latest_evidence_class: z.string().nullable(),
});

export const managedAssetListResponseSchema = z.object({
  total: z.number(),
  assets: z.array(managedAssetOutSchema),
});

export const alertOutSchema = z.object({
  id: z.number(),
  asset_id: z.number(),
  level: z.string(),
  risk_score: z.number(),
  triggered_rules: z.array(z.string()),
  status: z.string(),
  reason: z.string().nullable(),
  created_at: z.string(),
});

export const alertListResponseSchema = z.object({
  total: z.number(),
  alerts: z.array(alertOutSchema),
});

export type TerritoryOutDto = z.infer<typeof territoryOutSchema>;
export type TerritorySummaryOutDto = z.infer<typeof territorySummaryOutSchema>;
export type ManagedAssetOutDto = z.infer<typeof managedAssetOutSchema>;
export type AlertOutDto = z.infer<typeof alertOutSchema>;
