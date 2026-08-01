# Checklist de evidencia post-mutación

> A capturar por el propietario **después** de cada lote. Sin nombres de usuario,
> coordenadas crudas ni contenido de adjuntos en la documentación versionada;
> los Item IDs/URLs van solo al registro local ignorado.

## Tras Batch A (hardening)
- [ ] Captura de Settings de cada item mostrando protección de borrado activada
      (grupo, survey123_main, results_view, form_view, form_item, Web Map).
- [ ] results_view: export por otros = off (si A5 aprobado).
- [ ] form_view: aprobación de compartición pública editable = off (si A6).
- [ ] Web Map: Save As / búsqueda por dirección según decisión (A9/A10).
- [ ] pilot_assets: sin cambios (protección ya on).

## Tras Batch B (Web Map)
- [ ] Capturas de popups de observaciones y pilot_assets (campos mostrados/ocultos).
- [ ] Leyenda por evidencia/tendencia con etiqueta/patrón.
- [ ] Confirmar que no se añadieron definition expressions restrictivas.
- [ ] Copia/ajustes previos del Web Map guardados (rollback).

## Tras Batch C (Experience Builder)
- [ ] Captura del item EB nuevo (título/descripción DEMO).
- [ ] Fuentes conectadas (Web Map + results view).
- [ ] 5 páginas presentes.
- [ ] Compartición: solo grupo privado; nada público; sin anónimo.
- [ ] Protección de borrado de la app activada.
- [ ] Prueba con **cuenta miembro no-owner** (cuando exista): acceso correcto a
      fuentes, sin capacidad de edición no intencionada.

## Registro
Registrar Item IDs, URLs y fechas de verificación **solo** en
`arcgis/demo/pnsg/item-registry.local.yaml` (ignorado). La documentación
versionada registra solo el hecho y la disposición, no los identificadores.
