import { parseEnvironment } from '@/config/env';

describe('mobile environment parser', () => {
  it('uses safe local defaults and mock data', () => {
    expect(parseEnvironment({})).toEqual({
      environment: 'local',
      apiBaseUrl: 'http://127.0.0.1:8000',
      usesMockData: true,
    });
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
