import { Tabs } from 'expo-router';

import { colors } from '@/theme/tokens';

export const TAB_DEFINITIONS = [
  { name: 'index', title: 'Inicio' },
  { name: 'map', title: 'Mapa' },
  { name: 'assets', title: 'Activos' },
  { name: 'alerts', title: 'Alertas' },
  { name: 'profile', title: 'Perfil' },
] as const;

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.forest700,
        tabBarInactiveTintColor: colors.ink600,
        tabBarStyle: {
          backgroundColor: colors.white,
          borderTopColor: colors.sand300,
        },
      }}
    >
      {TAB_DEFINITIONS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{ title: tab.title }}
        />
      ))}
    </Tabs>
  );
}
