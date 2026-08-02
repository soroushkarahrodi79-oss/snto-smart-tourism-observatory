"""
Explorador de cambio visual (Sentinel-2) — Evidenciar layer (ADR-015).

First user-facing vertical slice of the Visual Change Explorer: pick a registered
territory, configure before/after windows, run explicitly, and see a draggable
before/after swipe (True Colour or NDVI) plus a static dNDVI result and quality
metadata. All Earth Engine work happens in ``change_explorer_service``; this tab
only collects inputs and renders the typed result. No GIF, tiles or pan/zoom.
"""
from __future__ import annotations

import datetime as _dt
import logging

import streamlit as st
from streamlit_image_comparison import image_comparison

from src.analysis.change_detection.models import CompositeKind, DateWindow
from src.config.settings import settings
from src.integrations.earth_engine.errors import (
    EarthEngineAuthError,
    EarthEngineConfigError,
    EarthEngineDisabledError,
    EarthEngineError,
    EarthEngineQuotaError,
    EarthEngineUnavailableError,
)
from src.integrations.earth_engine.palettes import DNDVI
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ResultStatus,
    cached_run_change_explorer,
    usable_territories,
)

logger = logging.getLogger(__name__)

SESSION_KEY = "snto_change_explorer_result"

_PRODUCT_LABELS = {
    CompositeKind.TRUE_COLOUR: "Color real (RGB)",
    CompositeKind.NDVI: "NDVI (vegetación)",
}
_DIMENSION_OPTIONS = (256, 384, 512, 640)

# Sensible, non-misleading defaults: two comparable summer windows in the past
# (peak subalpine vegetation), never "today", never a future date.
_DEFAULT_BEFORE = (_dt.date(2023, 7, 1), _dt.date(2023, 8, 31))
_DEFAULT_AFTER = (_dt.date(2024, 7, 1), _dt.date(2024, 8, 31))


def _window_label(win: DateWindow) -> str:
    return f"{win.start.isoformat()} → {win.end.isoformat()}"


def render_tab_change_explorer(_view: object = None) -> None:
    """Render the Visual Change Explorer tab (feature-flag gated)."""
    st.subheader("🛰️ Explorador de cambio visual (Sentinel-2)")

    if not settings.snto_enable_change_explorer:
        st.info(
            "El **Explorador de cambio visual** está desactivado. "
            "Actívalo con `SNTO_ENABLE_CHANGE_EXPLORER=true` (requiere además las "
            "credenciales `GEE_*`). Ver `docs/decisions/ADR-015`.",
            icon="🔒",
        )
        return

    st.caption(
        "Compara dos ventanas temporales de Sentinel-2 (composición mediana) sobre "
        "un territorio registrado. La ejecución es **explícita**: ajusta los "
        "controles y pulsa *Analizar cambios*."
    )

    territories = usable_territories()
    if not territories:
        st.warning("No hay territorios con AOI utilizable en el registro.")
        return

    _render_form(territories)

    # A failed submit clears the stored result (handled in _handle_submit), so an
    # old result is never presented as current.
    result = st.session_state.get(SESSION_KEY)
    if result is not None:
        _render_result(result)


def _render_form(territories: list[tuple[str, str]]) -> None:
    today = _dt.date.today()
    with st.form("change_explorer_form"):
        ids = [t[0] for t in territories]
        names = {t[0]: t[1] for t in territories}
        st.selectbox(
            "Territorio",
            options=ids,
            format_func=lambda k: names[k],
            key="ce_territory",
        )
        st.radio(
            "Producto de comparación",
            options=[CompositeKind.TRUE_COLOUR, CompositeKind.NDVI],
            format_func=lambda p: _PRODUCT_LABELS[p],
            key="ce_product",
            horizontal=True,
        )
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Ventana ANTES**")
            st.date_input(
                "Inicio (antes)", value=_DEFAULT_BEFORE[0],
                max_value=today, key="ce_before_start",
            )
            st.date_input(
                "Fin (antes)", value=_DEFAULT_BEFORE[1],
                max_value=today, key="ce_before_end",
            )
        with col_a:
            st.markdown("**Ventana DESPUÉS**")
            st.date_input(
                "Inicio (después)", value=_DEFAULT_AFTER[0],
                max_value=today, key="ce_after_start",
            )
            st.date_input(
                "Fin (después)", value=_DEFAULT_AFTER[1],
                max_value=today, key="ce_after_end",
            )
        st.slider(
            "Nubosidad máxima por escena (filtro a nivel de escena · "
            "CLOUDY_PIXEL_PERCENTAGE)",
            min_value=0, max_value=100, value=20, step=5, key="ce_cloud",
        )
        st.caption(
            "Este umbral descarta **escenas** completas demasiado nubosas. Aparte, "
            "la máscara **SCL** elimina píxeles inválidos (nube/sombra/nieve) "
            "*dentro* de cada escena conservada."
        )
        st.selectbox(
            "Dimensiones de salida (px)", options=_DIMENSION_OPTIONS,
            index=_DIMENSION_OPTIONS.index(512), key="ce_dimensions",
        )
        submitted = st.form_submit_button("Analizar cambios", type="primary")

    if submitted:
        _handle_submit()


def _handle_submit() -> None:
    ss = st.session_state
    # 1) Build/validate windows and request BEFORE any Earth Engine call.
    try:
        before = DateWindow(ss["ce_before_start"], ss["ce_before_end"])
        after = DateWindow(ss["ce_after_start"], ss["ce_after_end"])
        request = ChangeExplorerRequest(
            territory_id=ss["ce_territory"],
            product=ss["ce_product"],
            before=before,
            after=after,
            max_cloud_pct=float(ss["ce_cloud"]),
            dimensions=int(ss["ce_dimensions"]),
        )
    except (ValueError, TypeError) as exc:
        ss.pop(SESSION_KEY, None)
        st.error(f"Revisa los parámetros: {exc}", icon="⚠️")
        return

    # 2) Run the service; map known EE failures to safe, actionable messages.
    try:
        result = cached_run_change_explorer(request)
    except EarthEngineDisabledError:
        ss.pop(SESSION_KEY, None)
        st.info("El explorador está desactivado por configuración.", icon="🔒")
        return
    except EarthEngineConfigError:
        ss.pop(SESSION_KEY, None)
        st.error(
            "Earth Engine no está configurado (falta `GEE_PROJECT_ID` o la clave "
            "de servicio). Es un problema de configuración, no de tus datos.",
            icon="🛠️",
        )
        return
    except EarthEngineAuthError:
        ss.pop(SESSION_KEY, None)
        st.error(
            "Fallo de autenticación / permisos con Earth Engine. Revisa la cuenta "
            "de servicio y el registro del proyecto.",
            icon="🔑",
        )
        return
    except EarthEngineQuotaError:
        ss.pop(SESSION_KEY, None)
        st.warning(
            "Earth Engine ha rechazado la petición por cuota o límite de tasa. "
            "Inténtalo de nuevo en unos minutos.",
            icon="⏳",
        )
        return
    except EarthEngineUnavailableError:
        ss.pop(SESSION_KEY, None)
        st.error(
            "Earth Engine no está disponible en este momento (problema de "
            "infraestructura). Inténtalo más tarde.",
            icon="📡",
        )
        return
    except EarthEngineError:
        ss.pop(SESSION_KEY, None)
        logger.warning("Change Explorer failed with an Earth Engine error.")
        st.error("No se pudo completar el análisis satelital.", icon="❌")
        return

    ss[SESSION_KEY] = result


def _render_result(result: object) -> None:
    r = result  # typed ChangeExplorerResult
    st.divider()
    st.markdown(
        f"**{r.territory_name}** · Producto: **{_PRODUCT_LABELS[r.product]}**  \n"
        f"Generado para: ANTES {_window_label(r.request.before)} · "
        f"DESPUÉS {_window_label(r.request.after)} · "
        f"{r.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    if r.status is ResultStatus.NO_DATA or not r.has_swipe:
        st.warning(
            "Sin datos suficientes para componer las imágenes: no hay escenas o no "
            "quedan píxeles válidos tras la máscara SCL en alguna de las ventanas. "
            "Prueba a ampliar las fechas o subir el umbral de nubosidad.",
            icon="🌥️",
        )
    else:
        if r.status is ResultStatus.DEGRADED_COVERAGE:
            st.warning(
                "Cobertura de píxeles válidos por debajo del mínimo SNTO (30 %) en "
                "alguna ventana: las composiciones pueden ser poco fiables.",
                icon="⚠️",
            )
        _render_swipe(r)

    if r.dndvi_artifact is not None:
        _render_dndvi(r)

    _render_quality(r)
    st.caption(f"🛰️ {r.evidence_label}")


def _render_swipe(r: object) -> None:
    width = min(int(r.request.dimensions), 704)
    try:
        image_comparison(
            img1=r.before_artifact.url,
            img2=r.after_artifact.url,
            label1=f"ANTES · {_window_label(r.request.before)}",
            label2=f"DESPUÉS · {_window_label(r.request.after)}",
            width=width,
            in_memory=True,  # embed base64 server-side; never exposes the URL
        )
    except Exception:  # noqa: BLE001 - never surface a stack trace / URL
        logger.warning("Swipe images could not be loaded (URL may have expired).")
        st.warning(
            "No se pudieron cargar las imágenes de comparación (es posible que la "
            "URL temporal haya caducado). Vuelve a ejecutar el análisis.",
            icon="🖼️",
        )


def _render_dndvi(r: object) -> None:
    st.markdown("**Diferencia de NDVI (dNDVI = NDVI después − NDVI antes)**")
    try:
        st.image(
            r.dndvi_artifact.url,
            caption=f"dNDVI · {_window_label(r.request.after)} vs "
            f"{_window_label(r.request.before)}",
            width=min(int(r.request.dimensions), 704),
        )
    except Exception:  # noqa: BLE001
        st.warning("No se pudo cargar la capa dNDVI.", icon="🖼️")
    st.caption(f"🎨 {DNDVI.legend}")
    st.caption(
        "Interpretación: **negativo = descenso de NDVI**, cerca de cero = poco "
        "cambio observado, **positivo = aumento de NDVI**. Es un cambio "
        "**observacional**, no una prueba de causalidad turística ni de "
        "degradación; requiere validación de campo (#26)."
    )


def _render_quality(r: object) -> None:
    st.markdown("**Calidad de la evidencia por ventana**")
    col_b, col_a = st.columns(2)
    for col, q, title in (
        (col_b, r.before_quality, "ANTES"),
        (col_a, r.after_quality, "DESPUÉS"),
    ):
        with col:
            st.markdown(f"*{title}*")
            st.write(
                {
                    "Escenas (tras filtro de escena)": q.scene_count,
                    "Nubosidad media de escena (CLOUDY_PIXEL_PERCENTAGE, %)":
                        None if q.mean_scene_cloud_pct is None
                        else round(q.mean_scene_cloud_pct, 1),
                    "Cobertura de píxeles válidos en AOI (SCL, %)":
                        None if q.valid_pixel_fraction is None
                        else round(q.valid_pixel_fraction * 100, 1),
                    "Umbral de nubosidad solicitado (%)": q.requested_max_cloud_pct,
                    "Dataset": q.dataset_id,
                    "Composición": q.composite_method,
                }
            )
            if q.warnings:
                for w in q.warnings:
                    st.caption(f"⚠️ {w}")
    st.caption(
        "La *nubosidad de escena* (metadato por granulo) y la *cobertura de "
        "píxeles válidos en el AOI* (derivada de SCL) son medidas distintas."
    )
