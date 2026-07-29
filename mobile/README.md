# SNTO Mobile

Expo SDK 57 + TypeScript foundation for the native SNTO field companion.

## Phase boundary

- **Phase 1** (ADR-013) shipped the native shell — Expo Router, evidence
  presentation, a schema-validated GET-only HTTP client — powered entirely by
  local synthetic fixtures.
- **Phase 2** (ADR-014) adds a real `MobileHttpRepository` conforming to the
  same `MobileRepository` contract, built and tested against a mocked
  `fetch` — it is code-complete but **still defaults to the synthetic
  fixtures**. `EXPO_PUBLIC_SNTO_USE_REMOTE_API=true` is the only thing that
  switches it on; setting `EXPO_PUBLIC_SNTO_API_BASE_URL` alone does not.

This package remains, by design:

- native iOS/Android only;
- read-only at the network boundary (no write method exists in the mobile bundle);
- explicit about evidence class, source, timestamps, validation status, and limitations for every value, real or synthetic;
- free of authentication, map SDKs, offline persistence, Azure resources, and deployment configuration.

Even with the remote flag on, `/api/v2` is not deployed as a service today
(ADR-012 — the owner's call); the HTTP repository has nothing reachable to
point at until it is. Do not add `X-API-Key`, shared secrets, privileged
tokens, or write methods to the mobile bundle.

## Local setup

Expo SDK 57 requires Node.js 22.13 or newer.

```powershell
cd mobile
Copy-Item .env.example .env
npm ci
npm start
```

`127.0.0.1` refers to the device itself. To test the real read repository
against a locally running backend, set in `.env`:

```
EXPO_PUBLIC_SNTO_USE_REMOTE_API=true
EXPO_PUBLIC_SNTO_API_BASE_URL=http://<reachable-dev-host>:8000
EXPO_PUBLIC_SNTO_TERRITORY_SLUG=pnsg
```

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
- `src/api/`: GET-only, schema-validated API client + Zod DTOs mirroring `/api/v2`.
- `src/data/`: `MobileRepository` contract, the synthetic adapter, the HTTP
  adapter (`data/http/`, Fase 2) and the mock/HTTP selector (`data/repository.ts`).
- `src/components/`: shared states and evidence presentation.
- `src/config/`: allowlisted public environment parsing (mock/remote switch, territory slug).
- `src/theme/`: reusable visual tokens.
- `src/types/`: evidence taxonomy.

Authentication, a map provider, offline cache, or any write workflow still
requires a separate architecture decision and phase approval (see ADR-013's
Phase 3+ conditions).
