import { parseEnvironment } from '@/config/env';

describe('mobile environment parser', () => {
  it('uses safe local defaults and mock data', () => {
    expect(parseEnvironment({})).toEqual({
      environment: 'local',
      apiBaseUrl: 'http://127.0.0.1:8000',
      usesMockData: true,
      territorySlug: 'pnsg',
    });
  });

  it('stays on mock data even when an API base URL is configured', () => {
    // Fase 2 (ADR-014): configuring apiBaseUrl alone must not silently start
    // reading real data — only the explicit opt-in flag does.
    expect(
      parseEnvironment({
        EXPO_PUBLIC_SNTO_API_BASE_URL: 'https://api.example.test',
      }).usesMockData,
    ).toBe(true);
  });

  it('opts into the real API only with the explicit remote flag', () => {
    expect(
      parseEnvironment({ EXPO_PUBLIC_SNTO_USE_REMOTE_API: 'true' }).usesMockData,
    ).toBe(false);
  });

  it('accepts a custom territory slug', () => {
    expect(
      parseEnvironment({ EXPO_PUBLIC_SNTO_TERRITORY_SLUG: 'monfrague' }).territorySlug,
    ).toBe('monfrague');
  });

  it('requires HTTPS outside local mode', () => {
    expect(() =>
      parseEnvironment({
        EXPO_PUBLIC_SNTO_ENV: 'staging',
        EXPO_PUBLIC_SNTO_API_BASE_URL: 'http://api.example.test',
      }),
    ).toThrow('must use HTTPS');
  });

  it('rejects public keys that appear to carry secrets', () => {
    expect(() =>
      parseEnvironment({
        EXPO_PUBLIC_SNTO_ENV: 'local',
        EXPO_PUBLIC_API_KEY: 'do-not-bundle-this',
      }),
    ).toThrow('looks secret-bearing');
  });
});
