import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidencePanel } from '@/components/EvidencePanel';
import { mobileMockRepository } from '@/data/mock/mobileMockRepository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function HomeScreen() {
  const query = useRepositoryQuery(mobileMockRepository.getHomeSummary);

  return (
    <AppScreen
      eyebrow="Fundación móvil · Fase 1"
      title="Observatorio en campo"
      subtitle="Navegación y contratos locales con evidencia explícita. Sin conexión a producción."
    >
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' ? (
        <>
          <View style={styles.hero}>
            <Text style={styles.territory}>{query.data.territoryName}</Text>
            <Text style={styles.disclaimer}>
              Todos los valores de esta versión son sintéticos y no están validados en campo.
            </Text>
          </View>
          <View style={styles.stats}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{query.data.assetCount}</Text>
              <Text style={styles.statLabel}>activos demo</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{query.data.openAlertCount}</Text>
              <Text style={styles.statLabel}>alertas demo</Text>
            </View>
          </View>
          <EvidencePanel evidence={query.data.evidence} />
        </>
      ) : null}
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.forest900,
    borderRadius: radii.md,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  territory: {
    color: colors.white,
    fontSize: typography.heading,
    fontWeight: '800',
  },
  disclaimer: {
    color: colors.moss100,
    fontSize: typography.body,
    lineHeight: 23,
  },
  stats: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  stat: {
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    flex: 1,
    gap: spacing.xs,
    padding: spacing.md,
  },
  statValue: {
    color: colors.forest700,
    fontSize: typography.title,
    fontWeight: '800',
  },
  statLabel: {
    color: colors.ink600,
    fontSize: typography.caption,
  },
});
