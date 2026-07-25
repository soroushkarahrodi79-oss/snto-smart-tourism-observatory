import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidencePanel } from '@/components/EvidencePanel';
import { mobileEnvironment } from '@/config/env';
import { mobileRepository } from '@/data/repository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function HomeScreen() {
  const query = useRepositoryQuery(mobileRepository.getHomeSummary);

  return (
    <AppScreen
      eyebrow={
        mobileEnvironment.usesMockData
          ? 'Fundación móvil · Fase 1'
          : 'SNTO Mobile · Fase 2 · datos reales'
      }
      title="Observatorio en campo"
      subtitle={
        mobileEnvironment.usesMockData
          ? 'Navegación y contratos locales con evidencia explícita. Sin conexión a producción.'
          : 'Datos reales de /api/v2, con evidencia y limitación declaradas por elemento.'
      }
    >
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' ? (
        <>
          <View style={styles.hero}>
            <Text style={styles.territory}>{query.data.territoryName}</Text>
            <Text style={styles.disclaimer}>
              {mobileEnvironment.usesMockData
                ? 'Todos los valores de esta versión son sintéticos y no están validados en campo.'
                : 'Datos reales del backend SNTO. Ningún activo está validado en campo (campaña #26 pendiente).'}
            </Text>
          </View>
          <View style={styles.stats}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{query.data.assetCount}</Text>
              <Text style={styles.statLabel}>
                {mobileEnvironment.usesMockData ? 'activos demo' : 'activos'}
              </Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{query.data.openAlertCount}</Text>
              <Text style={styles.statLabel}>
                {mobileEnvironment.usesMockData ? 'alertas demo' : 'alertas abiertas'}
              </Text>
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
