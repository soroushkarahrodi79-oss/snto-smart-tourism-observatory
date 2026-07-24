import { z } from 'zod';

import { createReadOnlyApiClient } from '@/api/client';
import { ApiError } from '@/api/errors';

const response = (body: unknown, status = 200, contentType = 'application/json') =>
  ({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => contentType },
    json: async () => body,
  }) as unknown as Response;

describe('read-only API client', () => {
  it('issues GET requests with no credential or write headers', async () => {
    const fetchImpl = jest.fn(async () => response({ status: 'ok' }));
    const client = createReadOnlyApiClient({
      baseUrl: 'https://api.example.test/',
      fetchImpl: fetchImpl as typeof fetch,
    });

    await expect(
      client.get('/health', z.object({ status: z.literal('ok') })),
    ).resolves.toEqual({ status: 'ok' });

    expect(fetchImpl).toHaveBeenCalledWith(
      'https://api.example.test/health',
      expect.objectContaining({
        method: 'GET',
        headers: { Accept: 'application/json' },
      }),
    );
    expect(JSON.stringify(fetchImpl.mock.calls[0])).not.toContain('X-API-Key');
  });

  it('rejects responses that do not match the declared schema', async () => {
    const client = createReadOnlyApiClient({
      baseUrl: 'https://api.example.test',
      fetchImpl: jest.fn(async () => response({ status: 'unexpected' })) as typeof fetch,
    });

    await expect(
      client.get('/health', z.object({ status: z.literal('ok') })),
    ).rejects.toMatchObject({ kind: 'invalid_response' } satisfies Partial<ApiError>);
  });

  it('maps authorization failures without exposing response bodies', async () => {
    const client = createReadOnlyApiClient({
      baseUrl: 'https://api.example.test',
      fetchImpl: jest.fn(async () => response({ detail: 'private' }, 403)) as typeof fetch,
    });

    await expect(client.get('/restricted', z.unknown())).rejects.toMatchObject({
      kind: 'forbidden',
      status: 403,
    } satisfies Partial<ApiError>);
  });
});
