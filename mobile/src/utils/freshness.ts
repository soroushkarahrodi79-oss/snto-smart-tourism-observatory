export type Freshness = 'fresh' | 'stale' | 'unknown';

export function getFreshness(
  observedAt: string | null,
  now: Date,
  maxAgeMs: number,
): Freshness {
  if (!observedAt) return 'unknown';

  const observedTime = Date.parse(observedAt);
  if (!Number.isFinite(observedTime)) return 'unknown';

  const age = now.getTime() - observedTime;
  if (age < 0) return 'unknown';
  return age <= maxAgeMs ? 'fresh' : 'stale';
}
