import { z } from 'zod';

import { ApiError } from '@/api/errors';

export interface ReadOnlyApiClient {
  get<T>(path: string, schema: z.ZodType<T>): Promise<T>;
}

interface ClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

const statusKind = (status: number): ApiError['kind'] => {
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status >= 500) return 'server';
  return 'invalid_response';
};

export function createReadOnlyApiClient({
  baseUrl,
  timeoutMs = 8_000,
  fetchImpl = fetch,
}: ClientOptions): ReadOnlyApiClient {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, '');

  return {
    async get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const response = await fetchImpl(
          `${normalizedBaseUrl}/${path.replace(/^\/+/, '')}`,
          {
            method: 'GET',
            headers: { Accept: 'application/json' },
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new ApiError(
            statusKind(response.status),
            `SNTO API request failed with status ${response.status}.`,
            response.status,
          );
        }

        const contentType = response.headers.get('content-type') ?? '';
        if (!contentType.includes('application/json')) {
          throw new ApiError('invalid_response', 'SNTO API returned a non-JSON response.');
        }

        const result = schema.safeParse(await response.json());
        if (!result.success) {
          throw new ApiError('invalid_response', 'SNTO API response did not match its schema.');
        }
        return result.data;
      } catch (error: unknown) {
        if (error instanceof ApiError) {
          throw error;
        }
        if (error instanceof Error && error.name === 'AbortError') {
          throw new ApiError('timeout', 'SNTO API request timed out.');
        }
        throw new ApiError('network', 'SNTO API request could not be completed.');
      } finally {
        clearTimeout(timeout);
      }
    },
  };
}
