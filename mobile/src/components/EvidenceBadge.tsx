import { StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/theme/tokens';
import {
  EVIDENCE_LABELS,
  type EvidenceClass,
} from '@/types/evidence';

const palette: Record<EvidenceClass, { background: string; foreground: string }> = {
  real: { background: colors.moss100, foreground: colors.forest700 },
  calibrated: { background: colors.blue100, foreground: colors.blue700 },
  simulated: { background: colors.amber100, foreground: colors.amber700 },
  synthetic: { background: colors.red100, foreground: colors.red700 },
  missing: { background: colors.sand100, foreground: colors.ink600 },
};

export function EvidenceBadge({ evidenceClass }: { evidenceClass: EvidenceClass }) {
  const selected = palette[evidenceClass];
  const label = EVIDENCE_LABELS[evidenceClass];

  return (
    <View
      accessibilityLabel={`Clase de evidencia: ${label}`}
      style={[styles.badge, { backgroundColor: selected.background }]}
    >
      <Text style={[styles.label, { color: selected.foreground }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radii.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  label: {
    fontSize: typography.caption,
    fontWeight: '700',
  },
});
