import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { mobileEnvironment } from '@/config/env';
import { colors, radii, spacing, typography } from '@/theme/tokens';

export default function ProfileScreen() {
  return (
    <AppScreen
      eyebrow="Configuración"
      title="Perfil"
      subtitle="La identidad y los roles móviles se definirán con un contrato de autenticación dedicado."
    >
      <View style={styles.card}>
        <Text style={styles.label}>Modo de datos</Text>
        <Text style={styles.value}>Fixtures locales sintéticos</Text>
        <Text style={styles.label}>Entorno</Text>
        <Text style={styles.value}>{mobileEnvironment.environment}</Text>
        <Text style={styles.label}>API configurada</Text>
        <Text style={styles.value}>{mobileEnvironment.apiBaseUrl}</Text>
      </View>
      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>Sin inicio de sesión ficticio</Text>
        <Text style={styles.noticeBody}>
          La Fase 1 no almacena credenciales, no incorpora claves compartidas y no permite
          operaciones de escritura.
        </Text>
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.md,
  },
  label: {
    color: colors.ink600,
    fontSize: typography.caption,
    fontWeight: '700',
    marginTop: spacing.sm,
    textTransform: 'uppercase',
  },
  value: {
    color: colors.ink900,
    fontSize: typography.body,
  },
  notice: {
    backgroundColor: colors.amber100,
    borderRadius: radii.md,
    gap: spacing.sm,
    padding: spacing.md,
  },
  noticeTitle: {
    color: colors.amber700,
    fontSize: typography.heading,
    fontWeight: '700',
  },
  noticeBody: {
    color: colors.ink900,
    fontSize: typography.body,
    lineHeight: 23,
  },
});
