import { Link } from 'expo-router';
import { View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidenceBadge } from '@/components/EvidenceBadge';
import { RecordCard } from '@/components/RecordCard';
import { mobileMockRepository } from '@/data/mock/mobileMockRepository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { spacing } from '@/theme/tokens';

export default function AssetsScreen() {
  const query = useRepositoryQuery(mobileMockRepository.listAssets);

  return (
    <AppScreen
      eyebrow="Catálogo local"
      title="Activos"
      subtitle="Fixtures sintéticos para validar listas, detalle y trazabilidad."
    >
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' && query.data.length === 0 ? (
        <AsyncState kind="empty" />
      ) : null}
      {query.status === 'success' ? (
        <View style={{ gap: spacing.md }}>
          {query.data.map((asset) => (
            <Link
              key={asset.id}
              href={{ pathname: '/assets/[assetId]', params: { assetId: asset.id } }}
              asChild
            >
              <RecordCard
                title={asset.name}
                meta={`${asset.category} · ${asset.municipality}`}
                body={asset.summary}
                badge={<EvidenceBadge evidenceClass={asset.evidence.class} />}
              />
            </Link>
          ))}
        </View>
      ) : null}
    </AppScreen>
  );
}
