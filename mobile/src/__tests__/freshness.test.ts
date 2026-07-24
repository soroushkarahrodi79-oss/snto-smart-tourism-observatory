import { getFreshness } from '@/utils/freshness';

const NOW = new Date('2026-07-24T12:00:00.000Z');
const HOUR = 60 * 60 * 1_000;

describe('getFreshness', () => {
  it('marks recent observations as fresh', () => {
    expect(getFreshness('2026-07-24T11:30:00.000Z', NOW, HOUR)).toBe('fresh');
  });

  it('marks older observations as stale', () => {
    expect(getFreshness('2026-07-24T10:00:00.000Z', NOW, HOUR)).toBe('stale');
  });

  it.each([null, 'not-a-date', '2026-07-24T13:00:00.000Z'])(
    'returns unknown for unavailable or unsafe timestamps: %s',
    (observedAt) => {
      expect(getFreshness(observedAt, NOW, HOUR)).toBe('unknown');
    },
  );
});
