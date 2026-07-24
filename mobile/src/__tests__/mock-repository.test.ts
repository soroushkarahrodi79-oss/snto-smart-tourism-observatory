import { mobileMockRepository } from '@/data/mock/mobileMockRepository';

describe('synthetic mobile repository', () => {
  it('labels every fixture as synthetic and not field validated', async () => {
    const [home, assets, alerts] = await Promise.all([
      mobileMockRepository.getHomeSummary(),
      mobileMockRepository.listAssets(),
      mobileMockRepository.listAlerts(),
    ]);

    const evidence = [
      home.evidence,
      ...assets.map((asset) => asset.evidence),
      ...alerts.map((alert) => alert.evidence),
    ];

    expect(evidence).not.toHaveLength(0);
    for (const item of evidence) {
      expect(item.class).toBe('synthetic');
      expect(item.validationStatus).toBe('not_field_validated');
      expect(item.source).toContain('Fixture local');
      expect(item.limitation).not.toHaveLength(0);
    }
  });

  it('returns null for unknown detail identifiers', async () => {
    await expect(mobileMockRepository.getAsset('unknown')).resolves.toBeNull();
    await expect(mobileMockRepository.getAlert('unknown')).resolves.toBeNull();
  });
});
