import { useLocalSearchParams } from 'expo-router';
import { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidencePanel } from '@/components/EvidencePanel';
import { mobileRepository } from '@/data/repository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function AlertDetailScreen() {
  const { alertId } = useLocalSearchParams<{ alertId: string }>();
  const loadAlert = useCallback(
    () => mobileRepository.getAlert(alertId),
    [alertId],
  );
  const query = useRepositoryQuery(loadAlert);

  return (
    <AppScreen eyebrow="Alerta no operativa" title="Detalle de la alerta">
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' && !query.data ? <AsyncState kind="empty" /> : null}
      {query.status === 'success' && query.data ? (
        <>
          <View style={styles.card}>
            <Text style={styles.title}>{query.data.title}</Text>
            <Text style={styles.meta}>
              {query.data.severity.toUpperCase()} · {query.data.area}
            </Text>
            <Text style={styles.body}>{query.data.summary}</Text>
            <Text style={styles.warning}>
              No es una restricción oficial. Consulte siempre las autoridades competentes.
            </Text>
          </View>
          <EvidencePanel evidence={query.data.evidence} />
        </>
      ) : null}
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    color: colors.ink900,
    fontSize: typography.title,
    fontWeight: '800',
  },
  meta: {
    color: colors.red700,
    fontSize: typography.caption,
    fontWeight: '700',
  },
  body: {
    color: colors.ink600,
    fontSize: typography.body,
    lineHeight: 23,
  },
  warning: {
    backgroundColor: colors.amber100,
    borderRadius: radii.sm,
    color: colors.amber700,
    fontSize: typography.body,
    fontWeight: '700',
    lineHeight: 23,
    marginTop: spacing.sm,
    padding: spacing.md,
  },
});
