import { StyleSheet, Text, View } from 'react-native';

import { EvidenceBadge } from '@/components/EvidenceBadge';
import { colors, radii, spacing, typography } from '@/theme/tokens';
import type { EvidenceMetadata } from '@/types/evidence';

export function EvidencePanel({ evidence }: { evidence: EvidenceMetadata }) {
  return (
    <View style={styles.panel}>
      <View style={styles.heading}>
        <Text style={styles.title}>Trazabilidad</Text>
        <EvidenceBadge evidenceClass={evidence.class} />
      </View>
      <Text style={styles.label}>Fuente</Text>
      <Text style={styles.value}>{evidence.source}</Text>
      <Text style={styles.label}>Limitación</Text>
      <Text style={styles.value}>{evidence.limitation}</Text>
      <Text style={styles.validation}>No validado en campo · {evidence.fetchedAt}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.md,
  },
  heading: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  title: {
    color: colors.ink900,
    fontSize: typography.heading,
    fontWeight: '700',
  },
  label: {
    color: colors.ink600,
    fontSize: typography.caption,
    fontWeight: '700',
    marginTop: spacing.xs,
    textTransform: 'uppercase',
  },
  value: {
    color: colors.ink900,
    fontSize: typography.body,
    lineHeight: 22,
  },
  validation: {
    color: colors.red700,
    fontSize: typography.caption,
    marginTop: spacing.sm,
  },
});
