import type { ReadOnlyApiClient } from '@/api/client';
import { ApiError } from '@/api/errors';
import {
  alertListResponseSchema,
  alertOutSchema,
  managedAssetListResponseSchema,
  territoryListResponseSchema,
  territorySummaryOutSchema,
} from '@/api/schemas';
import type { MobileRepository } from '@/data/mobileRepository';
import { mapAlert, mapAsset, mapHomeSummary } from '@/data/http/mapping';

/**
 * Real /api/v2 read repository (Fase 2, ADR-014).
 *
 * Conforms to the same `MobileRepository` interface the synthetic fixture
 * repository implements, so screens never know which one they're talking to
 * (`@/data/repository` picks between them). Every method degrades honestly —
 * a 404 becomes `null` (the interface's "not found" contract), any other
 * failure (network, schema mismatch, server error) propagates as `ApiError`
 * for `useRepositoryQuery`'s error state, never a silently empty result.
 *
 * The territory is resolved once by slug (`mobileEnvironment.territorySlug`,
 * default `pnsg`) and cached in closure for the repository instance's
 * lifetime — one extra call the first time any method is used, none after.
 */
export function createMobileHttpRepository(
  client: ReadOnlyApiClient,
  territorySlug: string,
): MobileRepository {
  let territoryIdPromise: Promise<number> | null = null;

  async function resolveTerritoryId(): Promise<number> {
    if (territoryIdPromise === null) {
      territoryIdPromise = client
        .get('/api/v2/territories/', territoryListResponseSchema)
        .then((body) => {
          const match = body.territories.find((t) => t.slug === territorySlug);
          if (!match) {
            throw new ApiError(
              'not_found',
              `No territory registered with slug "${territorySlug}".`,
            );
          }
          return match.id;
        });
    }
    return territoryIdPromise;
  }

  async function fetchOrNull<T>(run: () => Promise<T>): Promise<T | null> {
    try {
      return await run();
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'not_found') {
        return null;
      }
      throw error;
    }
  }

  async function listAssetsInternal() {
    const territoryId = await resolveTerritoryId();
    const body = await client.get(
      `/api/v2/managed-assets/?territory_id=${territoryId}`,
      managedAssetListResponseSchema,
    );
    const fetchedAt = new Date().toISOString();
    return body.assets.map((dto) => mapAsset(dto, fetchedAt));
  }

  return {
    async getHomeSummary() {
      const territoryId = await resolveTerritoryId();
      const dto = await client.get(
        `/api/v2/territories/${territoryId}/summary`,
        territorySummaryOutSchema,
      );
      return mapHomeSummary(dto, new Date().toISOString());
    },

    listAssets: listAssetsInternal,

    async getAsset(assetId) {
      // No "get by external id" read endpoint exists yet — a small,
      // territory-scoped list lookup, consistent with how few assets a
      // single territory holds today (see ADR-014). A plain function
      // reference (not `this.listAssets()`), so it stays correct even if a
      // caller destructures the repository's methods.
      const assets = await listAssetsInternal();
      return assets.find((asset) => asset.id === assetId) ?? null;
    },

    async listAlerts() {
      const territoryId = await resolveTerritoryId();
      const body = await client.get(
        `/api/v2/alerts/?territory_id=${territoryId}`,
        alertListResponseSchema,
      );
      const fetchedAt = new Date().toISOString();
      return body.alerts.map((dto) => mapAlert(dto, fetchedAt));
    },

    async getAlert(alertId) {
      const numericId = Number(alertId);
      if (!Number.isInteger(numericId)) {
        return null;
      }
      return fetchOrNull(async () => {
        const dto = await client.get(`/api/v2/alerts/${numericId}`, alertOutSchema);
        return mapAlert(dto, new Date().toISOString());
      });
    },
  };
}
