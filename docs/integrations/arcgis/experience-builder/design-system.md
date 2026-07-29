# Sistema de diseño — Experience Builder (alineado con SNTO)

> Fase 2A · documentación únicamente. La **fuente de verdad** es el sistema de
> diseño institucional ya existente de SNTO; aquí se traduce a ArcGIS, **no** se
> inventa una identidad visual desconectada.

## 0. Fuentes de verdad (repositorio)

- **[Verificado]** CSS institucional en `src/ui/layout.py` (tokens de color,
  tipografía, KPIs, badges de alerta).
- **[Verificado]** Documentación UX: `docs/ux/design-system-review.md`,
  `docs/ux/visualization-review.md`, `docs/ux/accessibility.md`,
  `docs/ux/information-architecture.md`.

## 1. Paleta (tomada de `src/ui/layout.py`)

| Token | Valor | Uso |
|---|---|---|
| Navy institucional | `#1b2d42` | Barra/encabezados, superficies de marca |
| Texto primario | `#0d1b2a` | Títulos, valores KPI |
| Texto secundario | `#4b5b6b` / `#3d4a5c` | Subtítulos, etiquetas |
| Hairline / borde | `#d9e0e7` | Separadores, bordes de tarjeta |
| Fondo | `#f4f5f7` | Lienzo de página |
| Superficie | `#ffffff` | Tarjetas, popups |
| Muted | `#9aa4af` / `#7a8899` | Metadatos, sellos de fecha |
| Estado OK | `#22c55e` | Punto de estado «conectado/fresco» |

**[Propuesto]** En ArcGIS: usar estos valores en el tema del Experience Builder y
en la simbología para que la app «se sienta SNTO» y no un demo genérico.

## 2. Tipografía, espaciado y jerarquía

**[Propuesto]** Reflejar la escala de `layout.py`:

- KPI valor ~1.45rem/700; nombre de KPI ~0.875rem/600; metadato ~0.65rem
  mayúsculas con `letter-spacing`.
- Jerarquía: Título de página > pregunta de la capa > KPIs/mapa > detalle.
- Espaciado consistente (múltiplos de 4px), coherente con las tarjetas KPI.

## 3. Reglas de iconos

**[Propuesto]** Reusar los iconos de capa de `src/ui/navigation.py`
(**[Verificado]**): 🧭 Decidir · 🔬 Diagnosticar · 🛰️ Evidenciar · ⚖️ Gobernar.
Los iconos **acompañan** al texto de la capa; nunca son el único portador de
significado.

## 4. Tratamiento semántico de estado (no solo color)

**[Verificado] requisito de accesibilidad** (`docs/ux/accessibility.md`,
principio de no depender del color). Cada estado combina **color + forma/patrón +
etiqueta de texto + icono**:

| Estado | Color | Forma/patrón | Etiqueta |
|---|---|---|---|
| Degradando (`is_degrading=1`) | rojo | triángulo | «Degradando» |
| Estable | gris | círculo | «Estable» |
| Mejorando | verde | círculo relleno | «Mejorando» |
| Sin serie (`has_trend=0`) | gris claro | contorno discontinuo | «Sin serie» |

## 5. Badges de evidencia (tres dimensiones, `data-contract.md` §5)

**[Propuesto]** Badge textual + icono, nunca solo color:

- Dato de origen: `real` (●), `calibrated` (◐), `estimated` (≈),
  `simulated/synthetic` (◇ «DEMO»), `missing` (—).
- QA: `planned` / `draft` / `submitted` / `reviewed` / `rejected` (texto).
- Validación: `unvalidated` / `in_campaign` / `field_verified` (texto).
- Concordancia: `not_assessed` / `insufficient_sample` / `assessed`, con
  métricas solo tras comparación legítima.

Regla: los badges pueden coexistir en una ficha; **no** se fusionan en uno.

## 6. Estructura de popup de mapa (Feature Info)

**[Propuesto]** Orden fijo:

1. Nombre del activo + `asset_id`.
2. Badges de evidencia (3 dimensiones).
3. Tendencia: `trend`, `tau`, `p_value`, IC de Sen — o «Sin serie».
4. `ehs` / confianza — o «Sin dato».
5. `decision_caveat`.
6. Sello: `source_version` + fecha del snapshot + «Snapshot, no en vivo».

Los campos null se renderizan «Sin dato» con expresión Arcade (`null` ≠ `0`).

## 7. Reglas de gráficos (Chart widget)

**[Verificado]** Alinear con `docs/ux/visualization-review.md`. **[Propuesto]:**

- Impacto vs control (BACI) como barras agrupadas con etiqueta explícita de `n`.
- Nunca dibujar una serie de campo si `n` es insuficiente; mostrar «Muestra
  insuficiente» en su lugar.
- Ejes rotulados con unidades (MPa, %, m).

## 8. Comportamiento responsive

**[Propuesto]** (coherente con `page-blueprints.md`):

- Desktop: mapa + panel lateral.
- Tablet: panel como hoja lateral colapsable.
- Móvil: hoja inferior deslizable; en Evidenciar, ficha de parcela a pantalla
  completa (uso de campo).

## 9. Alternativas accesibles al color (resumen)

- Toda simbología categórica lleva **etiqueta o patrón**.
- Contraste AA sobre navy `#1b2d42` (ya resuelto en `layout.py` con textos
  `#E0E6EE`/`#F2F6FA`).
- Los estados de evidencia se leen sin percibir color (texto + forma).
