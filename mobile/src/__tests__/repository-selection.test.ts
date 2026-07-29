import { selectRepository } from '@/data/repository';
import { mobileMockRepository } from '@/data/mock/mobileMockRepository';
import type { MobileEnvironment } from '@/config/env';

const baseEnv: MobileEnvironment = {
  environment: 'local',
  apiBaseUrl: 'http://127.0.0.1:8000',
  usesMockData: true,
  territorySlug: 'pnsg',
};

describe('repository selection (Fase 2, ADR-014)', () => {
  it('defaults to the synthetic mock repository', () => {
    expect(selectRepository(baseEnv)).toBe(mobileMockRepository);
  });

  it('selects the HTTP repository only when usesMockData is explicitly false', () => {
    const repository = selectRepository({ ...baseEnv, usesMockData: false });
    expect(repository).not.toBe(mobileMockRepository);
    // conforms to the same shape — every MobileRepository method present
    expect(typeof repository.getHomeSummary).toBe('function');
    expect(typeof repository.listAssets).toBe('function');
    expect(typeof repository.getAsset).toBe('function');
    expect(typeof repository.listAlerts).toBe('function');
    expect(typeof repository.getAlert).toBe('function');
  });

  it('passes the configured base URL to the HTTP client factory', () => {
    const makeClient = jest.fn().mockReturnValue({ get: jest.fn() });
    selectRepository(
      { ...baseEnv, usesMockData: false, apiBaseUrl: 'https://api.example.test' },
      makeClient,
    );
    expect(makeClient).toHaveBeenCalledWith('https://api.example.test');
  });
});
