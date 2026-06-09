# GEE — Guía de desbloqueo (timebox de 1 jornada)

> **Objetivo.** Convertir el bloqueo "serie multi-anual real" en una tarea de ~30–45 min. El adaptador (`src/ingestion/gee_adapter.py`) ya está implementado y soporta autenticación por cuenta de servicio; lo único que falta son **credenciales** y un **runner de extracción**. Esta guía cubre ambos.
>
> **Fallback si encalla:** no pasa nada. La defensa del TFM ya no depende de esto — ver `docs/nota_metodologica_temporalidad.md` (el ΔEHS estacional es el resultado real de Sierra del Rincón y Mann-Kendall se demuestra en el Pipeline B). GEE solo *eleva* el Pipeline A a tendencia con datos reales; no es condición de aprobado.

---

## Paso 1 — Proyecto de Google Cloud + Earth Engine (10 min)

1. Crea o elige un proyecto en https://console.cloud.google.com/ (anota el **Project ID**, p. ej. `snto-gee`).
2. Habilita la **Earth Engine API**: `APIs & Services ▸ Enable APIs ▸ "Earth Engine API"`.
3. Registra el proyecto en Earth Engine: https://code.earthengine.google.com/ (acepta los términos; con cuenta académica el uso es gratuito).

## Paso 2 — Cuenta de servicio + clave JSON (10 min)

1. `IAM & Admin ▸ Service Accounts ▸ Create Service Account` → nombre `snto-ee-extractor`.
2. Rol: `Earth Engine Resource Viewer` (y `Service Usage Consumer` si lo pide).
3. En la cuenta creada: `Keys ▸ Add Key ▸ Create new key ▸ JSON`. Se descarga un archivo `*.json`.
4. Guárdalo **fuera del repo** (p. ej. `~/.config/snto/gee-key.json`). **Nunca lo commitees** — verifica que `*.json` de credenciales esté en `.gitignore`.
5. En Earth Engine, registra el email de la cuenta de servicio como usuario: https://signup.earthengine.google.com/#!/service_accounts

## Paso 3 — Instalar dependencia (2 min)

```bash
pip install earthengine-api
```

## Paso 4 — Variables de entorno (1 min)

Añade a tu `.env` (y a `.env.example` sin valores reales):

```dotenv
GEE_PROJECT_ID=snto-gee
GEE_KEY_FILE=/ruta/absoluta/a/gee-key.json
```

## Paso 5 — Runner de extracción

Guarda esto como `run_gee_extraction.py` en la raíz del repo. **Confirma la línea marcada `# TODO`**: debe cargar las geometrías reales de los senderos de Sierra del Rincón (desde `data/clean_assets/` o desde PostGIS, según tu fuente actual).

```python
"""Extrae la serie temporal multi-anual real de Sierra del Rincón vía GEE."""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.ingestion.gee_adapter import GEEAdapter
from src.assets.models import TourismAsset, Geometry, GeometryType

PROJECT_ID = os.environ["GEE_PROJECT_ID"]
KEY_FILE = os.environ["GEE_KEY_FILE"]
YEARS = range(2021, 2026)  # 2021–2025 → 5 años, Mann-Kendall robusto
OUT = Path("data/gee_timeseries")
OUT.mkdir(parents=True, exist_ok=True)


def load_snr_assets() -> list[TourismAsset]:
    # TODO: cargar las geometrías reales de los senderos de Sierra del Rincón.
    # Usa la MISMA fuente que tu Pipeline A (p. ej. el GeoJSON limpio en
    # data/clean_assets/production_hiking_trails.geojson). Ejemplo de patrón:
    #
    # gj = json.loads(Path("data/clean_assets/production_hiking_trails.geojson").read_text())
    # return [
    #     TourismAsset(
    #         asset_id=f"snr-trail-{i:03d}",
    #         name=feat["properties"].get("name", f"trail-{i}"),
    #         asset_type="trail",
    #         geometry=Geometry(type=GeometryType.LINESTRING,
    #                           coordinates=feat["geometry"]["coordinates"]),
    #         region="Sierra del Rincón",
    #     )
    #     for i, feat in enumerate(gj["features"])
    # ]
    raise NotImplementedError("Conecta la fuente real de senderos (ver comentario).")


def main() -> None:
    adapter = GEEAdapter(project_id=PROJECT_ID, key_file=KEY_FILE)
    assets = load_snr_assets()
    print(f"Extrayendo {len(assets)} activos × {len(list(YEARS))} años…")

    for asset in assets:
        series = []
        for year in YEARS:
            obs = adapter.fetch_time_series(asset, year=year, months=12)
            series.extend(o.model_dump() for o in obs)
            print(f"  {asset.asset_id} {year}: {len(obs)} composites mensuales válidos")
        out_file = OUT / f"{asset.asset_id}.json"
        out_file.write_text(json.dumps(series, indent=2, default=str))
        print(f"  → {out_file} ({len(series)} observaciones)")


if __name__ == "__main__":
    main()
```

```bash
python run_gee_extraction.py
```

> **⚠️ Aviso (ahorra tiempo de depuración):** en `src/ingestion/gee_adapter.py` el método `_initialize()` llama a `ee.ServiceAccountCredentials(email="", key_file=...)` con el email vacío. Según la versión de `earthengine-api`, esto puede hacer fallar la autenticación. Si ves un error de credenciales, edita esa línea para pasar el email real de la cuenta de servicio (el campo `client_email` del JSON), p. ej. leyéndolo del propio key file o de la variable `GEE_SERVICE_ACCOUNT` que ya existe en `.env.example`.

## Paso 6 — Validación rápida (timebox-check)

- Si cada activo devuelve **≥ 8–10 composites mensuales válidos por año** sobre 5 años → tienes ~40–60 puntos: Mann-Kendall es estadísticamente robusto. Conecta esa serie al Pipeline A (en lugar de las 2 escenas) y el ΔEHS estacional se convierte en tendencia inter-anual real.
- Si la cobertura es pobre (muchos meses descartados por nubes) → es esperable en zona montañosa; documenta el gap-filling como limitación y mantén el ΔEHS estacional como resultado principal.

## Disciplina de timebox

⏱ **Corta a las 8 h.** Si a media jornada sigues peleando con credenciales o cuotas de GEE, **para y usa el fallback**: el TFM ya está defendido sin esto (`docs/nota_metodologica_temporalidad.md`). GEE es mejora, no requisito.

---

*Guía de apoyo al TFM SNTO · junio 2026. El adaptador `gee_adapter.py` ya implementa autenticación por cuenta de servicio (`ee.ServiceAccountCredentials`) y composición mensual con máscara SCL.*
