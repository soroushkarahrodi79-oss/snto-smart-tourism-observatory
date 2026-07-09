"""
scripts/download_s2_pnsg.py
===========================
Descarga escenas Sentinel-2 L2A para PNSG (tile T30TVL) de los años 2021-2025
desde el Copernicus Data Space Ecosystem (CDSE) — acceso gratuito.

Estrategia de selección
-----------------------
Por cada año se descarga LA MEJOR escena de julio o agosto:
  - Nubosidad < 15 % sobre el tile completo
  - Preferencia por julio (pico vegetación subalpina en Guadarrama)
  - Si no hay escena en julio, se busca en agosto y luego junio

Resultado
---------
  data/raw_assets/raster_data/PNSG/
    2021/  S2A_MSIL2A_...T30TVL...SAFE/
    2022/  ...
    2023/  ...
    2024/  ...
    2025/  (ya existe — se salta automáticamente)

Autenticación
-------------
CDSE requiere cuenta gratuita en https://dataspace.copernicus.eu/
Exporta tus credenciales antes de ejecutar:

    set CDSE_USER=tu@email.com
    set CDSE_PASS=tu_contraseña

O pásalas como argumento:
    python scripts/download_s2_pnsg.py --user tu@email.com --password tu_contraseña

Dependencias
------------
    pip install requests tqdm

El script NO requiere earthengine-api ni GDAL.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuración PNSG ────────────────────────────────────────────────────────

TILE = "T30TVL"
YEARS = [2021, 2022, 2023, 2024, 2025]

# Meses de búsqueda por prioridad (julio → agosto → junio)
SEARCH_MONTHS = [
    ("07", "08"),  # julio + agosto como ventana primaria
    ("06",),       # junio como fallback
]

MAX_CLOUD_PCT = 15.0  # nubosidad máxima aceptable sobre el tile

OUTPUT_ROOT = Path("data/raw_assets/raster_data/PNSG")

# ── URLs CDSE ─────────────────────────────────────────────────────────────────

_CDSE_TOKEN_URL  = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
_CDSE_DOWNLOAD_BASE = "https://zipper.dataspace.copernicus.eu/odata/v1/Products"


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_token(user: str, password: str) -> str:
    """Obtiene un token de acceso OAuth2 de CDSE."""
    resp = requests.post(
        _CDSE_TOKEN_URL,
        data={
            "grant_type": "password",
            "username": user,
            "password": password,
            "client_id": "cdse-public",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log.info("Token CDSE obtenido correctamente.")
    return token


def refresh_token_if_needed(user: str, password: str, token_ts: float, token: str) -> tuple[str, float]:
    """Renueva el token si ha pasado más de 8 minutos (expira en 10)."""
    if time.time() - token_ts > 480:
        log.info("Renovando token CDSE...")
        token = get_token(user, password)
        token_ts = time.time()
    return token, token_ts


# ── Búsqueda de productos ─────────────────────────────────────────────────────

def search_best_scene(year: int) -> dict | None:
    """
    Busca la escena de menor nubosidad en julio/agosto (y junio como fallback)
    para el tile T30TVL del año dado.

    Returns: dict con campos 'Id', 'Name', 'ContentLength', 'CloudCover'
             o None si no se encontró ninguna escena válida.
    """
    candidate: dict | None = None
    best_cloud = 100.0

    search_windows = [
        (f"{year}-07-01", f"{year}-09-01"),  # julio + agosto
        (f"{year}-06-01", f"{year}-07-01"),  # junio fallback
    ]

    for date_start, date_end in search_windows:
        params = {
            "$filter": (
                f"Collection/Name eq 'SENTINEL-2' "
                f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
                f"    and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') "
                f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'tileId' "
                f"    and att/OData.CSC.StringAttribute/Value eq '{TILE}') "
                f"and ContentDate/Start gt {date_start}T00:00:00.000Z "
                f"and ContentDate/Start lt {date_end}T00:00:00.000Z "
                f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"    and att/OData.CSC.DoubleAttribute/Value lt {MAX_CLOUD_PCT})"
            ),
            "$orderby": "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value) asc",
            "$top": "5",
        }

        try:
            resp = requests.get(_CDSE_SEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
            products = resp.json().get("value", [])
        except requests.RequestException as exc:
            log.warning("Error en búsqueda CDSE para %d %s-%s: %s", year, date_start, date_end, exc)
            continue

        for product in products:
            # Extraer cloudCover de los atributos
            cloud = _extract_cloud(product)
            if cloud is not None and cloud < best_cloud:
                best_cloud = cloud
                candidate = product
                candidate["_cloud_pct"] = cloud

        if candidate is not None:
            break  # encontramos algo en la ventana primaria

    if candidate:
        log.info(
            "  Año %d → %s  (nubosidad=%.1f%%)",
            year, candidate["Name"], candidate.get("_cloud_pct", -1),
        )
    else:
        log.warning("  Año %d → sin escena válida con nubosidad < %.0f%%", year, MAX_CLOUD_PCT)

    return candidate


def _extract_cloud(product: dict) -> float | None:
    for attr in product.get("Attributes", []):
        if attr.get("Name") == "cloudCover":
            try:
                return float(attr["Value"])
            except (KeyError, TypeError, ValueError):
                pass
    return None


# ── Descarga ──────────────────────────────────────────────────────────────────

def download_scene(product: dict, year: int, token: str) -> Path | None:
    """
    Descarga el producto como ZIP y lo descomprime en OUTPUT_ROOT/YYYY/.
    Salta si el directorio de año ya contiene una carpeta .SAFE.

    Returns: Path al directorio .SAFE descomprimido, o None si se saltó.
    """
    year_dir = OUTPUT_ROOT / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    # Comprobar si ya existe un .SAFE descargado
    existing_safe = list(year_dir.glob("*.SAFE"))
    if existing_safe:
        log.info("  Año %d → ya existe %s — saltando.", year, existing_safe[0].name)
        return existing_safe[0]

    product_id   = product["Id"]
    product_name = product["Name"]
    zip_path     = year_dir / f"{product_name}.zip"

    download_url = f"{_CDSE_DOWNLOAD_BASE}({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    log.info("  Descargando %s ...", product_name)
    try:
        with requests.get(download_url, headers=headers, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            with open(zip_path, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True,
                desc=f"  {year}", leave=False,
            ) as bar:
                for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                    f.write(chunk)
                    bar.update(len(chunk))
    except requests.RequestException as exc:
        log.error("  Error descargando año %d: %s", year, exc)
        zip_path.unlink(missing_ok=True)
        return None

    # Descomprimir
    log.info("  Descomprimiendo %s ...", zip_path.name)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(year_dir)
        zip_path.unlink()  # borrar ZIP tras extracción exitosa
    except zipfile.BadZipFile as exc:
        log.error("  ZIP corrupto para año %d: %s", year, exc)
        zip_path.unlink(missing_ok=True)
        return None

    safe_dirs = list(year_dir.glob("*.SAFE"))
    if safe_dirs:
        log.info("  Año %d → descomprimido en %s", year, safe_dirs[0].name)
        return safe_dirs[0]

    log.error("  No se encontró carpeta .SAFE tras descomprimir año %d", year)
    return None


# ── Informe final ─────────────────────────────────────────────────────────────

def write_manifest(results: dict[int, str | None]) -> None:
    manifest_path = OUTPUT_ROOT / "download_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tile": TILE,
                "years": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    log.info("Manifiesto escrito en %s", manifest_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga Sentinel-2 L2A para PNSG (T30TVL) 2021-2025")
    parser.add_argument("--user",     default=os.environ.get("CDSE_USER", ""), help="Email CDSE")
    parser.add_argument("--password", default=os.environ.get("CDSE_PASS", ""), help="Contraseña CDSE")
    parser.add_argument("--years",    nargs="+", type=int, default=YEARS, help="Años a descargar")
    parser.add_argument("--max-cloud", type=float, default=MAX_CLOUD_PCT, help="Nubosidad máxima %%")
    parser.add_argument("--dry-run",  action="store_true", help="Solo buscar, no descargar")
    args = parser.parse_args()

    if not args.user or not args.password:
        log.error(
            "Credenciales CDSE requeridas.\n"
            "  Opción 1: set CDSE_USER=tu@email.com && set CDSE_PASS=contraseña\n"
            "  Opción 2: python scripts/download_s2_pnsg.py --user EMAIL --password PASS\n"
            "  Registro gratuito en: https://dataspace.copernicus.eu/"
        )
        sys.exit(1)

    token = get_token(args.user, args.password)
    token_ts = time.time()

    results: dict[int, str | None] = {}

    log.info("=== Buscando escenas Sentinel-2 L2A para tile %s ===", TILE)
    for year in sorted(args.years):
        log.info("--- Año %d ---", year)
        product = search_best_scene(year)

        if product is None:
            results[year] = None
            continue

        if args.dry_run:
            results[year] = f"[DRY-RUN] {product['Name']}"
            continue

        token, token_ts = refresh_token_if_needed(args.user, args.password, token_ts, token)
        safe_path = download_scene(product, year, token)
        results[year] = str(safe_path) if safe_path else None

    # Resumen
    log.info("\n=== RESUMEN ===")
    ok = 0
    for year, path in sorted(results.items()):
        status = "OK" if path else "FALLO"
        if path:
            ok += 1
        log.info("  %d: [%s] %s", year, status, path or "sin datos")

    log.info("%d/%d años con escena disponible.", ok, len(args.years))
    write_manifest(results)


if __name__ == "__main__":
    main()
