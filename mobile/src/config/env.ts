import { z } from 'zod';

const environmentSchema = z.enum(['local', 'development', 'staging', 'production']);
const forbiddenKeyPattern = /(SECRET|TOKEN|API_KEY|PASSWORD)/i;

const rawEnvironmentSchema = z
  .record(z.string(), z.string().optional())
  .superRefine((environment, context) => {
    for (const key of Object.keys(environment)) {
      if (key.startsWith('EXPO_PUBLIC_') && forbiddenKeyPattern.test(key)) {
        context.addIssue({
          code: 'custom',
          message: `Public environment key "${key}" looks secret-bearing and is forbidden.`,
        });
      }
    }
  });

export interface MobileEnvironment {
  environment: z.infer<typeof environmentSchema>;
  apiBaseUrl: string;
  usesMockData: true;
}

export function parseEnvironment(
  raw: Record<string, string | undefined>,
): MobileEnvironment {
  const parsedRaw = rawEnvironmentSchema.parse(raw);
  const environment = environmentSchema.parse(parsedRaw.EXPO_PUBLIC_SNTO_ENV ?? 'local');
  const apiBaseUrl =
    parsedRaw.EXPO_PUBLIC_SNTO_API_BASE_URL?.replace(/\/+$/, '') ??
    'http://127.0.0.1:8000';
  const url = z.url().parse(apiBaseUrl);

  if (environment !== 'local' && !url.startsWith('https://')) {
    throw new Error('EXPO_PUBLIC_SNTO_API_BASE_URL must use HTTPS outside local mode.');
  }

  return {
    environment,
    apiBaseUrl: url,
    usesMockData: true,
  };
}

export const mobileEnvironment = parseEnvironment({
  EXPO_PUBLIC_SNTO_ENV: process.env.EXPO_PUBLIC_SNTO_ENV,
  EXPO_PUBLIC_SNTO_API_BASE_URL: process.env.EXPO_PUBLIC_SNTO_API_BASE_URL,
});
