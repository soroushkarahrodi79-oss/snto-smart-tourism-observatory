import { useLocalSearchParams } from 'expo-router';
import { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidencePanel } from '@/components/EvidencePanel';
import { mobileEnvironment } from '@/config/env';
import { mobileRepository } from '@/data/repository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function AssetDetailScreen() {
  const { assetId } = useLocalSearchParams<{ assetId: string }>();
  const loadAsset = useCallback(
    () => mobileRepository.getAsset(assetId),
    [assetId],
  );
  const query = useRepositoryQuery(loadAsset);

  return (
    <AppScreen
      eyebrow={mobileEnvironment.usesMockData ? 'Activo sintético' : 'Activo SNTO'}
      title="Detalle del activo"
    >
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' && !query.data ? <AsyncState kind="empty" /> : null}
      {query.status === 'success' && query.data ? (
        <>
          <View style={styles.card}>
            <Text style={styles.title}>{query.data.name}</Text>
            <Text style={styles.meta}>
              {query.data.category} · {query.data.municipality}
            </Text>
            <Text style={styles.body}>{query.data.summary}</Text>
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
    color: colors.forest500,
    fontSize: typography.caption,
    fontWeight: '700',
  },
  body: {
    color: colors.ink600,
    fontSize: typography.body,
    lineHeight: 23,
  },
});
