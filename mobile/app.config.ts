import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: 'SNTO Mobile',
  slug: 'snto-mobile',
  version: '0.1.0',
  description: 'Native read-only field companion for the Smart Nature Tourism Observatory.',
  platforms: ['ios', 'android'],
  orientation: 'portrait',
  scheme: 'snto',
  icon: './assets/icon.png',
  backgroundColor: '#F5F2E9',
  primaryColor: '#164C3B',
  userInterfaceStyle: 'light',
  plugins: [
    'expo-router',
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 180,
        resizeMode: 'contain',
        backgroundColor: '#F5F2E9',
        dark: {
          backgroundColor: '#102821',
        },
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
  android: {
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png',
      backgroundColor: '#F5F2E9',
    },
  },
};

export default config;
