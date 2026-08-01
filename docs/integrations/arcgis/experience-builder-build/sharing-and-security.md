# Modelo de compartición y seguridad

> Compartir la app **no** concede automáticamente acceso a todas las fuentes de
> datos: cada item dependiente debe compartirse consistentemente.

## Estado verificado por A0c (2026-08-01, OWNER_UI_VERIFIED)

Todos los items (grupo, pilot_assets, servicio Survey123, form view, results
view, form item, Web Map) están **compartidos con owner + grupo privado SNTO;
NO org-wide; NO público** — coincide con el modelo propuesto abajo. Brechas de
hardening detectadas (protección de borrado off en varios items; export activo
en results view; aprobación de compartición pública editable activa en form
view) se abordan en `hardening-batch-a.md`. El grupo tiene **1 solo miembro (el
owner)** → QA multiusuario pendiente (`multiuser-qa-plan.md`).

## Modelo propuesto

| Item | Compartición propuesta |
|---|---|
| App Experience Builder | grupo privado |
| Web Map | mismo grupo privado |
| `pilot_assets` | mismo grupo privado |
| Survey123 **results view** | mismo grupo privado, acceso efectivo **read-oriented** |
| Survey123 **form item / form view** | **solo** contribuyentes de campo previstos |
| Survey123 servicio principal (capa) | **mínima exposición necesaria** |

## Reglas de seguridad

- **Nunca público** durante la demo académica.
- Los viewers de EB **no** deben recibir capacidad de edición no intencionada
  (confirmar en A0c; el results view root es `Is Updatable View` → verificar
  política efectiva a nivel de item).
- GPS, fotos, adjuntos y registros de observación permanecen dentro del grupo
  privado; ninguna compartición pública antes de una revisión explícita.
- Ninguna credencial, URL de servicio o Item ID en la propia app ni en su
  contenido de usuario.

## Checklist del propietario antes del lanzamiento

- [ ] App compartida con el grupo privado.
- [ ] Web Map compartido con el **mismo** grupo.
- [ ] `pilot_assets` compartida con el **mismo** grupo.
- [ ] Results view compartida con el mismo grupo; viewers **no** pueden editar.
- [ ] Form item/view compartido **solo** con contribuyentes.
- [ ] Servicio principal Survey123 con exposición mínima.
- [ ] **Nada** compartido públicamente.
- [ ] Todas las fuentes de datos dependientes accesibles para la audiencia
      prevista (probar con una cuenta miembro del grupo, no owner).
- [ ] Continuidad de cuenta y transferibilidad registradas.
