# Contribuir al SNTO

Gracias por tu interés en el **Smart Nature Tourism Observatory**. Este es un
proyecto de investigación académica (TFM, Universidad Complutense de Madrid).
Las contribuciones son bienvenidas dentro de los términos de la
[licencia de uso académico](LICENSE).

## Antes de empezar

- Lee el [README](README.md) (arquitectura de dos pipelines) y el
  [WHITEPAPER](WHITEPAPER_SNTO_Architecture_Blueprint.md).
- Revisa la sección **"Honestidad sobre limitaciones"** del README: muchas
  brechas conocidas son de **datos**, no de método, y ya están declaradas.
- Las salidas socioeconómicas son **escenarios prospectivos**, no mediciones.
  Cualquier contribución debe preservar esa honestidad metodológica.

## Entorno de desarrollo

```bash
python -m venv .venv
. .venv/Scripts/activate          # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
```

El dashboard corre sin base de datos con `USE_MOCK_DATA=true` (ver `.env.example`).

```bash
streamlit run app.py
```

## Calidad: obligatorio antes de un Pull Request

```bash
ruff check .          # linter
pytest                # toda la suite debe quedar verde (0 regresiones)
```

- **No se aceptan PRs que rompan la suite de tests.**
- Si añades una métrica o capa nueva, añade tests que la cubran.
- Respeta la **convención de scores salud vs. estrés** (`src/metrics/semantics.py`):
  health = 100 − stress. Mezclar direcciones es el bug más fácil de introducir.

## Estilo de commits

Formato convencional, en el idioma del repo (español):

```
feat(scope): descripción corta en imperativo
fix(scope): ...
docs(scope): ...
ci(scope): ...
```

## Tipos de contribución especialmente bienvenidos

1. **Datos de validación de campo** (penetrómetro, cobertura, erosión) para
   pseudo-validar los índices satelitales — ver `docs/field_validation_protocol.md`.
2. **Series temporales multi-anuales reales** vía Google Earth Engine
   (`gee_adapter.py`) para activar la detección de tendencias Mann-Kendall.
3. **Cartografía DEM** (altitud/orientación) para baselines estratificados.
4. **Nuevos territorios** de la Red de Parques Nacionales (OAPN).

Para cualquiera de estos, abre primero un *issue* con la plantilla
**"Solicitud / aporte de datos"** para coordinar.

## Reporte de errores y mejoras

Usa las plantillas de issue (`.github/ISSUE_TEMPLATE/`). Incluye versión de
Python, sistema operativo y, si aplica, el `run_context.json` generado.
