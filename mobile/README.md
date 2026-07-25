# SNTO Mobile

Expo SDK 57 + TypeScript foundation for the native SNTO field companion.

## Phase 1 boundary

This package is intentionally:

- native iOS/Android only;
- read-only at the network boundary;
- powered by local synthetic fixtures for every visible value;
- explicit about evidence class, source, timestamps, validation status, and limitations;
- free of authentication, map SDKs, offline persistence, Azure resources, and deployment configuration.

The configured API URL is a future read seam. Current screens never call it. Do not add
`X-API-Key`, shared secrets, privileged tokens, or write methods to the mobile bundle.

## Local setup

Expo SDK 57 requires Node.js 22.13 or newer.

```powershell
cd mobile
Copy-Item .env.example .env
npm ci
npm start
```

`127.0.0.1` refers to the device itself. If a later local API integration is tested on a
physical device, set `EXPO_PUBLIC_SNTO_API_BASE_URL` to a reachable development host.

## Quality checks

```powershell
npm run lint
npm run typecheck
npm test -- --runInBand
npx expo-doctor
npm run check:config
```

## Structure

- `src/app/`: Expo Router routes and layouts.
- `src/api/`: GET-only, schema-validated future API seam.
- `src/data/`: repository contract and synthetic adapter.
- `src/components/`: shared states and evidence presentation.
- `src/config/`: allowlisted public environment parsing.
- `src/theme/`: reusable visual tokens.
- `src/types/`: evidence taxonomy.

Any production-data integration, authentication, map provider, offline cache, or write
workflow requires a separate architecture decision and phase approval.
