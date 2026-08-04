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
import time

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
from src.services.change_animation_service import (
    DEFAULT_ANIMATION_DIMENSIONS,
    DEFAULT_ANIMATION_FPS,
    DEFAULT_MAX_FRAME_COUNT,
    AnimatedArtifact,
    ChangeAnimationRequest,
    GifDownloadError,
    GifInvalidError,
    GifTimeoutError,
    GifTooLargeError,
    InsufficientUsableFramesError,
    cached_run_change_animation,
)
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ResultStatus,
    cached_run_change_explorer,
    usable_territories,
)

logger = logging.getLogger(__name__)

SESSION_KEY = "snto_change_explorer_result"
ANIMATION_SESSION_KEY = "snto_change_animation_result"
ANIMATION_SIGNATURE_KEY = "snto_change_animation_signature"

# Frame-cap choices offered in the UI (a subset of the service's hard bounds).
_MAX_FRAME_OPTIONS = (4, 6, 8, 10, 12)
_ANIMATION_DIMENSION_OPTIONS = (256, 384)
_FPS_OPTIONS = (1, 2, 3)

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

    # 2) Run the service inside a visible loading state so long Earth Engine work
    #    never looks like a hang. Timing is logged (no secrets/URLs) so the exact
    #    service-vs-render boundary is observable.
    logger.info(
        "change_explorer UI: submit territory=%s product=%s dims=%s",
        ss["ce_territory"], getattr(ss["ce_product"], "value", ss["ce_product"]),
        ss["ce_dimensions"],
    )
    _t0 = time.monotonic()
    try:
        with st.spinner(
            "Analizando imágenes de Sentinel-2 en Earth Engine… "
            "(puede tardar unos segundos)"
        ):
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
    logger.info(
        "change_explorer UI: service done in %.1fs status=%s has_swipe=%s "
        "(rendering next)",
        time.monotonic() - _t0, result.status.value, result.has_swipe,
    )


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

    # The temporal GIF is an *optional*, explicitly-triggered extra shown only
    # below a successful swipe (never on NO_DATA / no-swipe). It never runs on
    # this rerun — only when its own separate form is submitted.
    if r.status is not ResultStatus.NO_DATA and r.has_swipe:
        _render_animation_section(r)


def _render_side_by_side(r: object, width: int) -> None:
    """Reliable fallback: before/after as two static images (no URL text shown)."""
    col_b, col_a = st.columns(2)
    with col_b:
        st.image(
            r.before_artifact.url,
            caption=f"ANTES · {_window_label(r.request.before)}",
            width=width,
        )
    with col_a:
        st.image(
            r.after_artifact.url,
            caption=f"DESPUÉS · {_window_label(r.request.after)}",
            width=width,
        )


def _render_swipe(r: object) -> None:
    width = min(int(r.request.dimensions), 704)
    swipe_ok = False
    try:
        image_comparison(
            img1=r.before_artifact.url,
            img2=r.after_artifact.url,
            label1=f"ANTES · {_window_label(r.request.before)}",
            label2=f"DESPUÉS · {_window_label(r.request.after)}",
            width=width,
            in_memory=True,  # embed base64 server-side; never exposes the URL
        )
        swipe_ok = True
        logger.info("change_explorer UI: swipe component rendered")
    except Exception:  # noqa: BLE001 - never surface a stack trace / URL
        logger.warning(
            "change_explorer UI: swipe component failed; using side-by-side fallback"
        )
        st.warning(
            "No se pudo mostrar el comparador deslizante; se muestran las imágenes "
            "**antes/después** lado a lado.",
            icon="🖼️",
        )
        _render_side_by_side(r, width)

    if swipe_ok:
        # The slider's JS/CSS loads client-side; if it does not render (e.g. a
        # blocked CDN) the component can appear blank without raising. Offer a
        # guaranteed, always-available separate view so the page is never blank.
        with st.expander("Ver imágenes antes/después por separado"):
            _render_side_by_side(r, width)


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


# ── Temporal GIF (🎞️) — optional, explicit, synchronous ────────────────────────

def _analysis_signature(r: object) -> tuple[object, ...]:
    """Identity of the *main* analysis a stored GIF belongs to.

    If the comparison is re-run for a different territory/product/window, a GIF
    generated for the previous analysis is no longer compatible and is dropped
    (never relabelled as belonging to the new result).
    """
    return (
        r.request.territory_id,
        r.product.value,
        r.request.before.start.isoformat(),
        r.request.before.end.isoformat(),
        r.request.after.start.isoformat(),
        r.request.after.end.isoformat(),
    )


def _animation_defaults(r: object) -> tuple[_dt.date, _dt.date]:
    """Default GIF span: earliest window start → latest window end (past only)."""
    start = min(r.request.before.start, r.request.after.start)
    end = max(r.request.before.end, r.request.after.end)
    return start, end


def _render_animation_section(r: object) -> None:
    st.divider()
    st.markdown("### 🎞️ Animación temporal")
    st.caption(
        "Genera **bajo demanda** un GIF de composiciones medianas Sentinel-2 a lo "
        "largo del periodo (mismo producto que la comparación). Es un extra "
        "**explícito y acotado**: no se ejecuta al cargar la página ni al mover los "
        "controles, sólo al pulsar *Generar GIF temporal*."
    )

    # A stored GIF from a *different* main analysis must not be shown here.
    signature = _analysis_signature(r)
    if st.session_state.get(ANIMATION_SIGNATURE_KEY) != signature:
        st.session_state.pop(ANIMATION_SESSION_KEY, None)
        st.session_state[ANIMATION_SIGNATURE_KEY] = signature

    default_start, default_end = _animation_defaults(r)
    today = _dt.date.today()
    with st.form("change_animation_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.date_input(
                "Inicio del periodo", value=default_start,
                max_value=today, key="ca_start",
            )
        with col2:
            st.date_input(
                "Fin del periodo", value=default_end,
                max_value=today, key="ca_end",
            )
        col3, col4, col5 = st.columns(3)
        with col3:
            st.selectbox(
                "Fotogramas máx.", options=_MAX_FRAME_OPTIONS,
                index=_MAX_FRAME_OPTIONS.index(DEFAULT_MAX_FRAME_COUNT),
                key="ca_max_frames",
            )
        with col4:
            st.selectbox(
                "Dimensiones (px)", options=_ANIMATION_DIMENSION_OPTIONS,
                index=_ANIMATION_DIMENSION_OPTIONS.index(
                    DEFAULT_ANIMATION_DIMENSIONS
                ),
                key="ca_dimensions",
            )
        with col5:
            st.selectbox(
                "FPS", options=_FPS_OPTIONS,
                index=_FPS_OPTIONS.index(DEFAULT_ANIMATION_FPS),
                key="ca_fps",
            )
        st.caption(
            "Cada fotograma es una composición **mediana** de una subventana "
            "temporal, con idéntico AOI, proyección y rango de visualización. "
            "Span máx. 24 meses · 2–12 fotogramas."
        )
        generate = st.form_submit_button("Generar GIF temporal", type="primary")

    if generate:
        _handle_animation_submit(r, signature)

    artifact = st.session_state.get(ANIMATION_SESSION_KEY)
    if artifact is not None:
        _render_animation_result(artifact)


def _handle_animation_submit(r: object, signature: tuple[object, ...]) -> None:
    ss = st.session_state
    # 1) Build/validate the request BEFORE any Earth Engine call. A failed GIF
    #    must never clear the swipe result (only the GIF session key is touched).
    try:
        request = ChangeAnimationRequest(
            territory_id=r.request.territory_id,
            product=r.product,
            start=ss["ca_start"],
            end=ss["ca_end"],
            max_cloud_pct=float(r.request.max_cloud_pct),
            dimensions=int(ss["ca_dimensions"]),
            max_frame_count=int(ss["ca_max_frames"]),
            frames_per_second=int(ss["ca_fps"]),
        )
    except (ValueError, TypeError) as exc:
        st.error(f"Revisa los parámetros de la animación: {exc}", icon="⚠️")
        return

    logger.info(
        "change_animation UI: submit territory=%s product=%s dims=%s frames=%s fps=%s",
        request.territory_id, request.product.value, request.dimensions,
        request.max_frame_count, request.frames_per_second,
    )
    try:
        with st.spinner(
            "Generando el GIF temporal en Earth Engine… "
            "(compone varias ventanas; puede tardar)"
        ):
            artifact = cached_run_change_animation(request)
    except EarthEngineDisabledError:
        st.info("El explorador está desactivado por configuración.", icon="🔒")
        return
    except EarthEngineConfigError:
        st.error(
            "Earth Engine no está configurado (falta `GEE_PROJECT_ID` o la clave "
            "de servicio). Es un problema de configuración, no de tus datos.",
            icon="🛠️",
        )
        return
    except EarthEngineAuthError:
        st.error(
            "Fallo de autenticación / permisos con Earth Engine al generar el GIF.",
            icon="🔑",
        )
        return
    except EarthEngineQuotaError:
        st.warning(
            "Earth Engine ha rechazado la generación del GIF por cuota o límite de "
            "tasa. Inténtalo de nuevo en unos minutos.",
            icon="⏳",
        )
        return
    except EarthEngineUnavailableError:
        st.error(
            "Earth Engine no está disponible en este momento (infraestructura). "
            "Inténtalo más tarde.",
            icon="📡",
        )
        return
    except InsufficientUsableFramesError:
        st.warning(
            "Menos de dos fotogramas con escenas Sentinel-2 útiles en el periodo. "
            "Amplía el rango o sube el umbral de nubosidad.",
            icon="🌥️",
        )
        return
    except GifTimeoutError:
        st.warning(
            "Se agotó el tiempo al descargar el GIF generado. Inténtalo de nuevo.",
            icon="⏳",
        )
        return
    except GifTooLargeError:
        st.warning(
            "El GIF generado supera el límite de 8 MiB. Reduce fotogramas o "
            "dimensiones.",
            icon="📦",
        )
        return
    except (GifInvalidError, GifDownloadError):
        st.error("No se pudo obtener el GIF generado.", icon="❌")
        return
    except EarthEngineError:
        logger.warning("Change Animation failed with an Earth Engine error.")
        st.error("No se pudo generar la animación temporal.", icon="❌")
        return

    # Only store on success; the signature ties it to the current main analysis.
    ss[ANIMATION_SESSION_KEY] = artifact
    ss[ANIMATION_SIGNATURE_KEY] = signature
    logger.info(
        "change_animation UI: done usable=%d/%d bytes=%d",
        artifact.frame_count, artifact.planned_frame_count, artifact.byte_size,
    )


def _render_animation_result(artifact: AnimatedArtifact) -> None:
    st.image(artifact.gif_bytes, output_format="GIF")

    period = (
        f"{artifact.request.start.isoformat()} → {artifact.request.end.isoformat()}"
    )
    size_kib = artifact.byte_size / 1024
    st.markdown(
        f"**{artifact.territory_name}** · Producto: "
        f"**{_PRODUCT_LABELS[artifact.product]}** · Periodo: {period}  \n"
        f"Fotogramas: **{artifact.frame_count}** usados / "
        f"{artifact.planned_frame_count} planificados · "
        f"{artifact.frames_per_second} FPS · {artifact.dimensions}px · "
        f"{size_kib:.0f} KiB · "
        f"{artifact.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    filename = (
        f"snto_{artifact.territory_id}_{artifact.product.value}_"
        f"{artifact.request.start.isoformat()}_{artifact.request.end.isoformat()}.gif"
    )
    st.download_button(
        "Descargar GIF",
        data=artifact.gif_bytes,
        file_name=filename,
        mime=artifact.mime_type,
    )

    if artifact.warnings:
        for w in artifact.warnings:
            st.caption(f"⚠️ {w}")

    with st.expander("Detalle de fotogramas"):
        st.write(
            [
                {
                    "#": f.frame_index,
                    "inicio": f.frame_start,
                    "fin": f.frame_end,
                    "escenas": f.scene_count,
                    "omitido": bool(f.warning),
                }
                for f in artifact.frames
            ]
        )

    st.caption(f"🎞️ {artifact.evidence_label}")
