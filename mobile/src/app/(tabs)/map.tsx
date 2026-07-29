import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function MapScreen() {
  return (
    <AppScreen
      eyebrow="Capacidad diferida"
      title="Mapa"
      subtitle="La cartografía se incorporará cuando exista una decisión de proveedor, licencias y operación offline."
    >
      <View style={styles.placeholder}>
        <Text style={styles.symbol}>⌁</Text>
        <Text style={styles.title}>Sin mapa simulado</Text>
        <Text style={styles.body}>
          Esta pantalla reserva el contrato de navegación. No descarga teselas, no solicita
          ubicación y no representa capas territoriales.
        </Text>
        <Text style={styles.phase}>Planificado para una fase posterior</Text>
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  placeholder: {
    alignItems: 'center',
    backgroundColor: colors.moss100,
    borderColor: colors.forest500,
    borderRadius: radii.md,
    borderStyle: 'dashed',
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.xl,
  },
  symbol: {
    color: colors.forest700,
    fontSize: 52,
    fontWeight: '300',
  },
  title: {
    color: colors.ink900,
    fontSize: typography.heading,
    fontWeight: '800',
  },
  body: {
    color: colors.ink600,
    fontSize: typography.body,
    lineHeight: 23,
    textAlign: 'center',
  },
  phase: {
    color: colors.forest700,
    fontSize: typography.caption,
    fontWeight: '700',
    marginTop: spacing.sm,
    textTransform: 'uppercase',
  },
});
