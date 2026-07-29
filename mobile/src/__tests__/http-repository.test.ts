import { createReadOnlyApiClient } from '@/api/client';
import { createMobileHttpRepository } from '@/data/http/mobileHttpRepository';

const jsonResponse = (body: unknown, status = 200) =>
  ({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: async () => body,
  }) as unknown as Response;

const TERRITORIES = {
  total: 2,
  territories: [
    { id: 1, slug: 'pnsg', name: 'PNSG', budget_eur: 150000, created_at: 'x' },
    { id: 2, slug: 'monfrague', name: 'Monfragüe', budget_eur: 1, created_at: 'x' },
  ],
};

const SUMMARY = {
  territory_id: 1,
  slug: 'pnsg',
  name: 'PNSG',
  asset_count: 2,
  open_alert_count: 1,
  updated_at: '2026-06-01T00:00:00.000Z',
  evidence_class: 'real',
};

const ASSETS = {
  total: 1,
  assets: [
    {
      id: 1,
      territory_id: 1,
      external_asset_id: 'pnsg-nat-001',
      name: 'Laguna de Peñalara',
      asset_type: 'trail',
      region: 'Madrid',
      status: 'detected',
      created_at: 'x',
      updated_at: 'x',
      latitude: 40.82,
      longitude: -3.96,
      latest_observed_at: '2026-06-01T00:00:00.000Z',
      latest_evidence_class: 'real',
    },
  ],
};

const ALERTS = {
  total: 1,
  alerts: [
    {
      id: 7,
      asset_id: 1,
      level: 'URGENT_MONITORING',
      risk_score: 0.6,
      triggered_rules: [],
      status: 'open',
      reason: null,
      created_at: 'x',
    },
  ],
};

function buildRepository(fetchImpl: jest.Mock) {
  const client = createReadOnlyApiClient({
    baseUrl: 'https://api.example.test',
    fetchImpl: fetchImpl as unknown as typeof fetch,
  });
  return createMobileHttpRepository(client, 'pnsg');
}

describe('mobile HTTP repository', () => {
  it('resolves the configured territory slug once and caches it across calls', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(SUMMARY))
      .mockResolvedValueOnce(jsonResponse(ASSETS));
    const repository = buildRepository(fetchImpl);

    await repository.getHomeSummary();
    await repository.listAssets();

    // 3 calls total, not 4: the territories list is fetched once (during
    // getHomeSummary) and reused by listAssets' own territory resolution.
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    const urls = fetchImpl.mock.calls.map((call) => call[0] as string);
    expect(urls.filter((u) => u.endsWith('/territories/'))).toHaveLength(1);
    expect(urls.some((u) => u.includes('/territories/1/summary'))).toBe(true);
    expect(urls.some((u) => u.includes('/managed-assets/?territory_id=1'))).toBe(true);
  });

  it('getHomeSummary maps the territory summary honestly', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(SUMMARY));
    const repository = buildRepository(fetchImpl);

    const summary = await repository.getHomeSummary();
    expect(summary.territoryName).toBe('PNSG');
    expect(summary.assetCount).toBe(2);
    expect(summary.evidence.class).toBe('real');
  });

  it('listAssets maps every asset, including its location', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(ASSETS));
    const repository = buildRepository(fetchImpl);

    const assets = await repository.listAssets();
    expect(assets).toHaveLength(1);
    expect(assets[0]?.id).toBe('pnsg-nat-001');
    expect(assets[0]?.location).toEqual({ latitude: 40.82, longitude: -3.96 });
  });

  it('getAsset finds by external id within the territory list', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(ASSETS));
    const repository = buildRepository(fetchImpl);

    const asset = await repository.getAsset('pnsg-nat-001');
    expect(asset?.name).toBe('Laguna de Peñalara');
  });

  it('getAsset returns null for an unknown id, never throws', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(ASSETS));
    const repository = buildRepository(fetchImpl);

    await expect(repository.getAsset('does-not-exist')).resolves.toBeNull();
  });

  it('listAlerts maps every alert for the territory', async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValueOnce(jsonResponse(TERRITORIES))
      .mockResolvedValueOnce(jsonResponse(ALERTS));
    const repository = buildRepository(fetchImpl);

    const alerts = await repository.listAlerts();
    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.severity).toBe('warning');
  });

  it('getAlert fetches directly by id, no territory resolution needed', async () => {
    const fetchImpl = jest.fn().mockResolvedValueOnce(jsonResponse(ALERTS.alerts[0]));
    const repository = buildRepository(fetchImpl);

    const alert = await repository.getAlert('7');
    expect(alert?.id).toBe('7');
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('getAlert returns null on a 404, not an exception', async () => {
    const fetchImpl = jest.fn().mockResolvedValueOnce(jsonResponse({ detail: 'x' }, 404));
    const repository = buildRepository(fetchImpl);

    await expect(repository.getAlert('999')).resolves.toBeNull();
  });

  it('getAlert returns null for a non-numeric id without a network call', async () => {
    const fetchImpl = jest.fn();
    const repository = buildRepository(fetchImpl);

    await expect(repository.getAlert('not-a-number')).resolves.toBeNull();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('propagates a real failure (not a 404) rather than swallowing it', async () => {
    const fetchImpl = jest.fn().mockResolvedValueOnce(jsonResponse({}, 500));
    const repository = buildRepository(fetchImpl);

    await expect(repository.getAlert('1')).rejects.toMatchObject({ kind: 'server' });
  });

  it('throws when the configured territory slug does not exist on the backend', async () => {
    const fetchImpl = jest.fn().mockResolvedValueOnce(
      jsonResponse({ total: 0, territories: [] }),
    );
    const repository = buildRepository(fetchImpl);

    await expect(repository.getHomeSummary()).rejects.toMatchObject({ kind: 'not_found' });
  });
});
