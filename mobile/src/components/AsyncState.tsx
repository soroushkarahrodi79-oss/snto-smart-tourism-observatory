import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/theme/tokens';

export type AsyncStateKind =
  | 'loading'
  | 'empty'
  | 'offline'
  | 'unauthorized'
  | 'forbidden'
  | 'error';

const stateCopy: Record<Exclude<AsyncStateKind, 'loading'>, { title: string; body: string }> = {
  empty: {
    title: 'Sin resultados',
    body: 'No hay elementos disponibles para esta vista.',
  },
  offline: {
    title: 'Sin conexión',
    body: 'La información remota no está disponible. Los fixtures locales siguen identificados.',
  },
  unauthorized: {
    title: 'Sesión necesaria',
    body: 'La identidad móvil se incorporará después del contrato de autenticación.',
  },
  forbidden: {
    title: 'Acceso restringido',
    body: 'Tu perfil no tiene permiso para consultar este contenido.',
  },
  error: {
    title: 'No se pudo cargar',
    body: 'Inténtalo de nuevo cuando el servicio esté disponible.',
  },
};

export function AsyncState({ kind }: { kind: AsyncStateKind }) {
  if (kind === 'loading') {
    return (
      <View accessibilityRole="progressbar" style={styles.container}>
        <ActivityIndicator color={colors.forest700} />
        <Text style={styles.body}>Cargando…</Text>
      </View>
    );
  }

  const copy = stateCopy[kind];
  return (
    <View accessibilityRole="summary" style={styles.container}>
      <Text style={styles.title}>{copy.title}</Text>
      <Text style={styles.body}>{copy.body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    color: colors.ink900,
    fontSize: typography.heading,
    fontWeight: '700',
  },
  body: {
    color: colors.ink600,
    fontSize: typography.body,
    lineHeight: 22,
    textAlign: 'center',
  },
});
