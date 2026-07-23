# Kit de difusión SNTO — textos listos para publicar

Borradores para cada plataforma. Sustituye `[URL_DASHBOARD]` por la URL real. El
repositorio es `https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory`
y el DOI conceptual permanente es `10.5281/zenodo.20818269`. Las cifras son las
del Pipeline A real (PNSG, 2 escenas Sentinel-2). Mantén la honestidad
metodológica: alerta temprana, no intervención formal.

> **Dos pistas (lee [`PUBLICATION_STRATEGY.md`](PUBLICATION_STRATEGY.md) antes de publicar):**
> el software se publica siguiendo las *releases de código*; la ciencia, siguiendo la
> *evidencia*. Las secciones **§1–§4 son el lanzamiento v1.0.0** (registro histórico de lo
> ya publicado, correcto y sin overclaiming). La sección **§6 es el hito de plataforma
> v2.0** — **solo hechos de ingeniería** (arquitectura, tests, despliegue), **sin cifras
> científicas nuevas** ni claims de validación (esos esperan a la campaña de campo #26).

---

## 1. LinkedIn — secuencia de lanzamiento (espaciar 5-7 días)

> **Formato:** imagen única por post (no carrusel PDF — para cuentas <5K seguidores la imagen
> rinde más). Etiqueta UCM, OAPN, EUROPARC, Copernicus, ESA y a las supervisoras. Fija el Post 0.

### Post 0 — Lanzamiento / ancla (publicar HOY, fijar al perfil)

> 🛰️ Después de meses de trabajo, el **SNTO** ya está publicado y en abierto.
>
> El **Smart Nature Tourism Observatory** detecta el estrés ecológico de los senderos de un parque
> nacional **desde el satélite, antes de que el deterioro sea visible a simple vista** — y traduce cada
> hallazgo en una **prioridad de inversión con presupuesto y nivel de confianza**.
>
> Lo desarrollé como TFM en la **Universidad Complutense de Madrid** y lo apliqué al **Parque Nacional
> Sierra de Guadarrama** con cartografía oficial OAPN.
>
> Qué encontró (2 escenas Sentinel-2 reales, 218 senderos):
> 📉 **46 senderos** con deterioro estacional activo
> 🎯 **24 con señal de uso turístico** vs 165 de origen climático
> 💶 **~1.435.700 €** de presupuesto de intervención priorizado por causa y confianza
>
> Honestidad metodológica: con 2 escenas esto es **alerta temprana estacional**, no tendencia
> plurianual. El propio sistema lo declara.
>
> Todo en abierto — código, 493 tests, dashboard en vivo y software citable con DOI:
> 📄 Software (DOI permanente): https://doi.org/10.5281/zenodo.20818269
> 🖥️ Dashboard: [URL_DASHBOARD]
> 💻 GitHub: https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory
>
> Si trabajas en gestión de espacios protegidos o teledetección, me encantaría tu mirada crítica. 👇
>
> #Teledetección #Sentinel2 #TurismoSostenible #ParquesNacionales #RemoteSensing #OpenScience #UCM

**Imagen:** `docs/screenshot-dashboard.png` (el dashboard con los KPIs).

### Post 1 — El problema (gancho)

> Los parques nacionales españoles gestionan el impacto del turismo casi siempre **tarde**: se actúa
> cuando la erosión de un sendero ya se ve a simple vista. Para entonces, restaurar es caro y a veces
> imposible.
>
> Durante mi TFM en la @Universidad Complutense de Madrid construí el **SNTO**, un observatorio que le
> da la vuelta a esa lógica: detecta el estrés ecológico de un sendero **desde el satélite, antes de
> que sea visible**.
>
> Lo apliqué al **Parque Nacional Sierra de Guadarrama** con cartografía oficial OAPN.
> En los próximos días cuento cómo funciona y qué encontró. 🧵
>
> 🔗 Dashboard en vivo: [URL_DASHBOARD]
>
> #TurismoSostenible #Teledetección #ParquesNacionales #Sentinel2 #UCM

### Post 2 — La tecnología (cómo)

> ¿Cómo se "ve" el cansancio de un sendero desde el espacio? 🛰️
>
> El SNTO usa imágenes **Sentinel-2** (Copernicus, abiertas) y dos índices:
> · **NDVI** → vigor de la vegetación
> · **NDMI** → humedad
>
> La clave no es solo medir la degradación, sino **atribuir su causa**: el sistema analiza el gradiente
> espacial alrededor de cada traza y separa el daño **localizado** (pisoteo, uso turístico) del daño
> **a escala de paisaje** (sequía, clima). Porque la respuesta de gestión es completamente distinta.
>
> Y nunca recomienda gastar dinero sin evidencia suficiente: un *gate* de confianza bloquea las
> recomendaciones cuando los datos no dan.
>
> 🔗 Cómo está construido: https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory
>
> #RemoteSensing #GIS #NDVI #OpenData

### Post 3 — Los resultados (impacto, el que más engagement genera)

> Resultados del SNTO sobre el **Parque Nacional Sierra de Guadarrama** (2 escenas Sentinel-2 reales,
> 218 senderos con cartografía oficial OAPN):
>
> 📉 **46 de 218 senderos** con deterioro estacional activo.
> 🎯 De los degradados: **24 con señal de uso turístico**, 165 con señal climática a escala de paisaje.
> 💶 Presupuesto de intervención estimado: **~1.435.700 €**, priorizado por causa y confianza.
>
> Importante y honesto: con 2 escenas esto es **alerta temprana**, no diagnóstico plurianual. El propio
> sistema lo declara.
>
> Todo el código es abierto. 493 tests, desplegado en la nube.
> 🔗 https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory · 🔗 [URL_DASHBOARD]
>
> ¿Trabajas en gestión de espacios protegidos? Me encantaría tu opinión. 👇
>
> #TurismoRegenerativo #ParquesNacionales #DataScience #Sostenibilidad #EUROPARC

**Etiquetar cuando sea posible:** UCM, OAPN (Organismo Autónomo de Parques Nacionales), EUROPARC
España, MITERD, Copernicus EU.
**Añadir a la sección "Proyectos" del perfil** con enlaces a repo y dashboard.

### Post 4 — Versión EN (comunidad internacional GIS / RemoteSensing, ~día +26)

> 🛰️ New open-source preprint: turning Sentinel-2 into **proactive** management intelligence for
> national-park tourism.
>
> The **Smart Nature Tourism Observatory (SNTO)** detects trail-level ecological stress from space —
> *before* it's visible on the ground — and, crucially, performs **spatial causal attribution** to
> separate use-driven degradation from climate-driven change.
>
> Applied to **Sierra de Guadarrama National Park (Spain)** with official OAPN cartography:
> 📉 **46 of 218 trails** with active seasonal degradation
> 🎯 **24 use-driven** vs 165 landscape/climate-driven
> 💶 **~€1.44M** indicative, confidence-gated intervention budget
>
> Honest by design: with two Sentinel-2 scenes this is a **seasonal early-warning signal, not a
> multi-year trend** — and the system states it.
>
> Open code, 493 tests, live dashboard, and citable software:
> 📄 https://doi.org/10.5281/zenodo.20818269 · 💻 GitHub · 🖥️ [URL_DASHBOARD]
>
> Feedback from the #RemoteSensing / #GIS community very welcome. cc @ESA @CopernicusEU
>
> #RemoteSensing #Sentinel2 #GIS #ProtectedAreas #OpenScience #SustainableTourism

**Imagen:** `docs/figures/ehs_map.png` (el mapa de senderos por EHS).

---

## 2. X / Twitter — hilo para la comunidad GIS (6-8 tweets)

1. 🛰️ Detectar el desgaste de un sendero **antes** de que se vea a simple vista. Eso hace el SNTO,
   el observatorio open-source que construí sobre el Parque Nacional Sierra de Guadarrama. Hilo 🧵👇

2. El problema: la gestión del impacto turístico en espacios protegidos suele ser reactiva. Cuando la
   erosión es visible, restaurar es caro o imposible.

3. La materia prima: imágenes #Sentinel2 (@CopernicusEU, abiertas). Dos índices, NDVI (vigor vegetal)
   y NDMI (humedad), calibrados por percentiles reales de cada escena. [imagen mapa PNSG por EHS]

4. La parte que más me importa: **atribución causal**. Analizando el gradiente espacial 0–50 / 50–200 /
   200–1000 m, separo daño localizado (uso) de daño a escala de paisaje (clima). [imagen SCM]

5. Resultado sobre 218 senderos: 46 con deterioro activo, 24 con señal de uso, 165 climática.
   Presupuesto de intervención priorizado ~1,44M €.

6. Honestidad: con 2 escenas es señal estacional (ΔEHS), NO tendencia. Mann-Kendall necesita serie
   larga, y el sistema lo declara. Nada de overclaiming.

7. 493 tests, CI/CD, desplegado en Azure + Hugging Face Spaces, dashboard con 3 vistas
   (técnica / gestor / auditoría). Todo abierto.
   Código: https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory

8. Investigación académica en la UCM (supervisión: Carmen Mínguez · Susana Ramírez García / REGENERA).
   Software citable: https://doi.org/10.5281/zenodo.20818269
   Feedback de la comunidad #GIS #RemoteSensing muy bienvenido. cc @ESA_EO @CopernicusEU

**Hashtags:** #GIS #RemoteSensing #Sentinel2 #OpenData #Spain #EcoTurismo

---

## 3. ResearchGate / Zenodo — abstract para el Whitepaper (preprint / technical report)

**Título:** SNTO — Smart Nature Tourism Observatory: a satellite-based territorial intelligence
framework for proactive, regenerative governance of protected-area tourism.

**Abstract (EN):**
Protected natural areas largely manage tourism impact reactively, intervening only once trail
degradation is visually evident. This work presents the SNTO, an open-source territorial intelligence
observatory that converts Sentinel-2 remote sensing (NDVI/NDMI) into actionable management
intelligence for national parks. The framework (i) computes a scene-percentile-calibrated Ecological
Health Score per trail, (ii) performs spatial causal attribution to distinguish use-driven from
climate-driven degradation via a 0–50/50–200/200–1000 m impact gradient, (iii) gates spending
recommendations behind a Decision Confidence Score, and (iv) prioritizes restoration budget while
quantifying the cost of inaction. Applied to the Sierra de Guadarrama National Park (Spain) using
official OAPN cartography and two real Sentinel-2 scenes, it flags 46 of 218 trails with active
seasonal degradation and an indicative ~€1.44M intervention budget. The system explicitly bounds its
claims (seasonal early-warning, not multi-year trend) and aligns with European protected-area
reporting frameworks (Natura 2000 / EUROPARC / CETS). All code, tests (493) and documentation are
open.

**Keywords:** remote sensing, Sentinel-2, NDVI, NDMI, protected areas, sustainable tourism, causal
attribution, territorial intelligence, Spain, Sierra de Guadarrama, OAPN.

---

## 4. Metadatos Zenodo (al crear el release v1.0.0)

- **Upload type:** Software (y un segundo registro tipo *Publication → Report* para el Whitepaper).
- **Title:** SNTO — Smart Nature Tourism Observatory
- **Authors:** Karahrodi, Soroush (Universidad Complutense de Madrid)
- **License:** ver `LICENSE` (uso académico). En Zenodo: "Other (Open)".
- **Keywords:** las de `CITATION.cff`.
- **Related identifiers:** repositorio GitHub (isSupplementTo).
- Tras obtener el DOI, añadir el badge al README y descomentar el bloque `identifiers` en `CITATION.cff`.

---

## 5. Checklist de orden de publicación

- [x] Screenshot real del dashboard → `docs/screenshot-dashboard.png`
- [x] `CITATION.cff` con DOI Zenodo
- [x] DOI conceptual Zenodo 10.5281/zenodo.20818269 cableado (badge README, CITATION.cff, kit)
- [x] Hugging Face Space desplegado → huggingface.co/spaces/soroushkararodi/snto-observatory
- [x] Whitepaper HTML generado → `docs/SNTO_Whitepaper_2026_Karahrodi.html`
- [x] Preprint académico generado → `docs/SNTO_Preprint_2026_Karahrodi.html`
- [x] **SIGUIENTE:** Abrir `SNTO_Preprint_2026_Karahrodi.html` en Chrome → Ctrl+P → Guardar como PDF → subir a ResearchGate (tipo "Preprint") + Zenodo (tipo "Publication → Preprint")
- [x] Topics y Social Preview en GitHub (Settings → Topics: `remote-sensing` `sentinel-2` `tourism` `spain` `streamlit`)
- [ ] Verificar URL Azure en README §7 (si hay placeholder)
- [ ] LinkedIn post 1 → (5-7 días) post 2 → post 3 (textos en §1 de este doc)
- [x] Hilo en X/Twitter con imagen del mapa (textos en §2)
- [ ] Dossier institucional → OAPN / EUROPARC (vía UCM) → `docs/dossier_institucional_OAPN.md`

---

## 6. Hito de plataforma v2.0 (Pista A — solo ingeniería, sin ciencia nueva)

> Publicable **ahora**. Habla de **arquitectura/producto**, no de resultados científicos.
> No repite las cifras del PNSG (46 senderos, causa, presupuesto): esas ya se contaron en el
> lanzamiento v1.0.0 y no hay evidencia nueva. Acompaña con la captura del shell de 4 capas
> (`docs/screenshot-dashboard.png`).

### LinkedIn — post único "v2.0"

> 🧭 Actualización mayor del **SNTO**: de un panel único a una **capa de decisión modular**.
>
> Cuando lo publiqué (TFM en la **UCM**) era un dashboard. Un año de desarrollo después,
> **v2.0** reorganiza toda la herramienta alrededor de **cómo decide** quien gestiona un
> parque, no de qué sabe medir el satélite:
>
> 🧭 **Cuatro capas de decisión** — Decidir · Diagnosticar · Evidenciar · Gobernar
> 👥 **Vistas por rol** (gestor / técnico / auditoría), cada una con su nivel de detalle
> 🗂️ **El activo como página**: cada sendero, su ficha, su evidencia y su trazabilidad
> 🛠️ **Backend persistente** (SQLAlchemy + PostgreSQL en Azure), ciclo de vida de cada
> alerta y **rastro de auditoría** de cada decisión
> ✅ **900+ tests**, CI separado del deploy, todo en abierto
>
> Lo que **no** cambia, a propósito: la honestidad metodológica. La correlación satélite↔campo
> sigue pendiente de una campaña de terreno — y el sistema lo declara. Nada de "validado" hasta
> tenerla.
>
> 🖥️ Dashboard: [URL_DASHBOARD] · 💻 GitHub · 📄 Notas de release (v2.0.0)
>
> #DecisionIntelligence #RemoteSensing #ParquesNacionales #OpenScience #UCM

**Imagen:** `docs/screenshot-dashboard.png` (shell de 4 capas, vista Auditoría).

### X / Twitter — 2 tweets

1. 🧭 SNTO v2.0: de dashboard a **capa de decisión modular**. Cuatro capas (Decidir ·
   Diagnosticar · Evidenciar · Gobernar), vistas por rol, el activo como página, backend
   persistente con auditoría. 900+ tests, abierto. [imagen shell 4 capas]

2. Lo que NO cambió a propósito: la honestidad. La validación satélite↔campo sigue pendiente
   de campaña de terreno y el sistema lo declara. Cero overclaiming. 💻 GitHub · 🖥️ [URL_DASHBOARD]

### Zenodo / GitHub Release

Notas y metadatos en [`releases/v2.0.0.md`](releases/v2.0.0.md). El tag
`v2.0.0` ya está archivado con el DOI canónico
[`10.5281/zenodo.21472647`](https://doi.org/10.5281/zenodo.21472647): no crear
otra versión v2.0.0.
