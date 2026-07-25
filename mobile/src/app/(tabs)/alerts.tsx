import { Link } from 'expo-router';
import { View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { AsyncState } from '@/components/AsyncState';
import { EvidenceBadge } from '@/components/EvidenceBadge';
import { RecordCard } from '@/components/RecordCard';
import { mobileMockRepository } from '@/data/mock/mobileMockRepository';
import { useRepositoryQuery } from '@/data/useRepositoryQuery';
import { spacing } from '@/theme/tokens';

export default function AlertsScreen() {
  const query = useRepositoryQuery(mobileMockRepository.listAlerts);

  return (
    <AppScreen
      eyebrow="Señales no operativas"
      title="Alertas"
      subtitle="Ejemplos sintéticos. Ningún elemento constituye una restricción oficial."
    >
      {query.status === 'loading' ? <AsyncState kind="loading" /> : null}
      {query.status === 'error' ? <AsyncState kind="error" /> : null}
      {query.status === 'success' && query.data.length === 0 ? (
        <AsyncState kind="empty" />
      ) : null}
      {query.status === 'success' ? (
        <View style={{ gap: spacing.md }}>
          {query.data.map((alert) => (
            <Link
              key={alert.id}
              href={{ pathname: '/alerts/[alertId]', params: { alertId: alert.id } }}
              asChild
            >
              <RecordCard
                title={alert.title}
                meta={`${alert.severity.toUpperCase()} · ${alert.area}`}
                body={alert.summary}
                badge={<EvidenceBadge evidenceClass={alert.evidence.class} />}
              />
            </Link>
          ))}
        </View>
      ) : null}
    </AppScreen>
  );
}
