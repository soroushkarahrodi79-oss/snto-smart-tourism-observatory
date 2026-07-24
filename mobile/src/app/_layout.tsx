import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { colors } from '@/theme/tokens';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          contentStyle: { backgroundColor: colors.sand50 },
          headerStyle: { backgroundColor: colors.sand50 },
          headerTintColor: colors.forest700,
          headerTitleStyle: { fontWeight: '700' },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="assets/[assetId]" options={{ title: 'Detalle del activo' }} />
        <Stack.Screen name="alerts/[alertId]" options={{ title: 'Detalle de la alerta' }} />
      </Stack>
    </>
  );
}
