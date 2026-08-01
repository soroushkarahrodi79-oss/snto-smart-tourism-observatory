# A0c — Verificación de permisos de item (puerta previa obligatoria)

> El propietario verifica cada punto en la UI de ArcGIS Online. **No** se afirma
> aquí ningún permiso no verificado: todas las celdas de estado real quedan como
> `PENDING_OWNER_UI` hasta que el propietario las confirme. Ningún cambio de
> compartición se realiza en esta fase.

## Objetivo del MVP (estado requerido)

- Demo académica **privada**, operada por el propietario; **no pública**.
- Compartición **solo con el grupo privado** donde sea necesario.
- Captura a través del **form view** de Survey123.
- Visualización de evidencia a través del **results view**.
- Los usuarios de Experience Builder **no** deben recibir capacidad de edición no
  intencionada.

## Datos a capturar por item

Para cada item: owner · compartido con (solo owner / organización / grupo
específico / todos-público) · pertenencia al grupo · capacidad de actualización ·
capacidad de edición · si los miembros pueden actualizar el item · si la edición
de la capa alojada está habilitada · si el acceso anónimo es posible · si los
adjuntos son visibles · si el results view puede ser editado por los visores
previstos · riesgo de continuidad/transferencia de propiedad de la cuenta.

## Tabla A0c

| Item | Estado requerido | Acción del propietario | Evidencia a capturar | ¿Bloqueante? |
|---|---|---|---|---|
| Grupo privado | Privado; solo miembros previstos | Revisar miembros y política de compartición del grupo | Owner, nº miembros, política de compartición | **Sí** (define audiencia) |
| `pilot_assets` HFL | Compartido con el grupo privado; **sin acceso anónimo**; edición no expuesta a viewers | Revisar Share + Settings→Editing | Compartido con, editing on/off, anónimo sí/no | **Sí** |
| Survey123 servicio principal (capa) | Mínima exposición necesaria; edición solo a contribuyentes | Revisar Share + Editing | Compartido con, editing, quién edita | **Sí** |
| Survey123 **form view** | Solo contribuyentes de campo previstos | Revisar Share | Compartido con, editable por contribuyentes | Sí |
| Survey123 **results view** | Grupo privado; **acceso efectivo read-oriented** para viewers | Revisar Share + si viewers pueden editar la vista | Compartido con, ¿viewers pueden editar? (root es *Is Updatable View*) | **Sí** |
| Survey123 **Form item** | Solo contribuyentes de campo | Revisar Share | Compartido con | Sí |
| Web Map | Grupo privado (igual que sus capas) | Revisar Share | Compartido con | **Sí** |

## Reglas de honestidad

- **No** se afirma que el results view sea solo-lectura para todo usuario: el
  root reporta `Is Updatable View`; la política efectiva de edición debe
  confirmarse a nivel de item. Objetivo: que los viewers de EB **no** puedan
  editar.
- **No** se afirma el alcance de compartición exacto ni la pertenencia al grupo
  hasta la verificación del propietario.
- **Continuidad de cuenta educativa:** registrar owner actual, owner de respaldo
  institucional, transferibilidad de items y fecha de revisión/caducidad — riesgo
  de pérdida de todos los items si la cuenta se da de baja.

## Puerta de salida A0c

A0c se considera superada cuando **todas** las filas «bloqueante» están
confirmadas en el estado requerido y el riesgo de continuidad está registrado.
Solo entonces puede solicitarse la aprobación explícita de mutación para crear la
app y configurar el Web Map.
