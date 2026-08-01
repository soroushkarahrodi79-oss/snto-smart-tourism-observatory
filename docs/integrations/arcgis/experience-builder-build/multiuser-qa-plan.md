# Plan de QA multiusuario (pendiente)

> **Brecha abierta:** el grupo privado tiene **exactamente 1 miembro (el owner)**.
> El comportamiento efectivo de un usuario no-owner **no** se ha probado. La QA
> multiusuario está **pendiente** y es independiente de los lotes A/B/C.

## Por qué importa

A0c verificó la configuración desde la perspectiva del owner. **No** prueba que
un miembro no-owner del grupo:

- pueda ver la app EB, el Web Map y las capas compartidas;
- **no** pueda editar `pilot_assets` ni las observaciones (edición no
  intencionada);
- **no** pueda editar la results view (root reporta `Is Updatable View`);
- pueda capturar vía form view (add-only) sin ver registros existentes.

## Prerrequisito

- Añadir **una segunda cuenta UCM autorizada** de prueba al grupo privado (por
  invitación). No convertir el grupo en shared-update salvo decisión explícita.

## Pruebas a ejecutar (con la cuenta no-owner)

1. Acceso a la app EB y a todas sus fuentes de datos (sin errores de permiso).
2. Intento de edición de `pilot_assets` → **debe fallar** (solo lectura).
3. Intento de edición de la results view → **debe fallar** o no estar disponible.
4. Captura en form view → add-only; **no** ve registros existentes.
5. Verificar que la app y las capas **no** son visibles fuera del grupo (probar
   con una cuenta ajena al grupo, si es posible).
6. Confirmar que ningún dato sensible (observador, notas, coordenadas, adjuntos)
   se expone a quien no debe.

## Estado

`MULTIUSER_QA: PENDING` — no bloquea la creación operada por el owner (Batch C),
pero **debe completarse antes** de considerar la demo lista para presentación a
terceros o para cualquier ampliación de audiencia.

## Relacionado

Continuidad de cuenta educativa (owner de respaldo, transferibilidad,
caducidad) sigue **pendiente** — ver `permission-gate-a0c.md` y el registro local.
