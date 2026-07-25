# ADR-013 — Fundación del cliente móvil SNTO

- **Estado:** Aceptada para Fase 1
- **Fecha:** 2026-07-24
- **Alcance:** `mobile/`

## Contexto

SNTO necesita una experiencia nativa orientada a consulta en campo. El backend
actual contiene endpoints de lectura y escritura, pero todavía no ofrece un
contrato de identidad móvil seguro y el servicio `/api/v2` no está desplegado.
Empaquetar una API key compartida o atribuir acciones mediante un encabezado
controlado por el cliente no proporciona identidad ni auditoría suficientes.

La taxonomía canónica de evidencia del observatorio es `real`, `calibrated`,
`simulated`, `synthetic` y `missing`. Un cliente debe preservar esa procedencia y
no presentar fixtures como observaciones reales.

## Decisión

Crear una aplicación Expo SDK 57 + TypeScript dentro de `mobile/` con:

- soporte nativo para iOS y Android;
- Expo Router y cinco rutas principales;
- un repositorio tipado que separa pantallas de adaptadores de datos;
- fixtures locales exclusivamente `synthetic` y `not_field_validated`;
- metadatos visibles de fuente, tiempo, validación y limitaciones;
- un cliente HTTP futuro limitado a `GET`, con timeout, errores centrales y
  validación Zod;
- variables públicas allowlisted y rechazo de nombres que sugieran secretos;
- CI independiente para lint, tipos, pruebas y configuración pública.

La Fase 1 no conectará pantallas con producción y no incluirá escrituras,
autenticación, mapas, caché offline, Azure ni despliegue.

## Consecuencias

La navegación y los contratos se pueden validar sin crear una falsa apariencia
de disponibilidad operativa. El adaptador mock se podrá sustituir por un
adaptador HTTP sin acoplar las pantallas al transporte.

El mapa es un placeholder explícito. El perfil no simula autenticación. La
aplicación requiere conectividad cuando se habilite un adaptador remoto, salvo
que una decisión posterior apruebe persistencia offline.

## Condiciones para fases posteriores

Antes de leer datos reales desde el móvil se debe acordar un contrato API
versionado, desplegarlo y aplicar autenticación de usuario. Antes de cualquier
escritura se requieren autorización por roles, atribución server-side,
idempotencia, auditoría y protección contra reintentos.

Un proveedor de mapas necesita una decisión separada sobre licencias,
telemetría, privacidad, caché y funcionamiento sin conexión. La lógica
científica y las reglas de gobernanza seguirán ejecutándose en el backend.
