import { createReadOnlyApiClient, type ReadOnlyApiClient } from '@/api/client';
import type { MobileEnvironment } from '@/config/env';
import { mobileEnvironment } from '@/config/env';
import { createMobileHttpRepository } from '@/data/http/mobileHttpRepository';
import type { MobileRepository } from '@/data/mobileRepository';
import { mobileMockRepository } from '@/data/mock/mobileMockRepository';

/**
 * Picks the mock or the real HTTP repository for a given environment
 * (Fase 2, ADR-014). A pure function so the selection itself is testable
 * without relying on module-load-time environment parsing.
 */
export function selectRepository(
  env: MobileEnvironment,
  makeClient: (baseUrl: string) => ReadOnlyApiClient = (baseUrl) =>
    createReadOnlyApiClient({ baseUrl }),
): MobileRepository {
  if (env.usesMockData) {
    return mobileMockRepository;
  }
  return createMobileHttpRepository(makeClient(env.apiBaseUrl), env.territorySlug);
}

/**
 * The single repository every screen consumes. Selection is entirely
 * `mobileEnvironment.usesMockData` — defaults to the synthetic fixture
 * repository unless `EXPO_PUBLIC_SNTO_USE_REMOTE_API=true` is explicitly set
 * (see `@/config/env`). Screens import this, never the mock or HTTP
 * repository directly, so the choice lives in exactly one place.
 */
export const mobileRepository: MobileRepository = selectRepository(mobileEnvironment);
