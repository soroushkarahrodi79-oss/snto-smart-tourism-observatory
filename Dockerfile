# syntax=docker/dockerfile:1
# ──────────────────────────────────────────────────────────────────────────────
# SNTO — Smart Natural Tourism Observatory · Streamlit dashboard
# Target: Azure Container Apps (consumption). No system GDAL required — the
# geospatial stack (rasterio/shapely) ships manylinux wheels for cp312.
# `--only-binary=:all:` makes the build FAIL FAST if any dep would compile
# from source (which would need system GDAL), instead of failing at runtime.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Dashboard runs without a database (mock-data mode is its native mode).
    USE_MOCK_DATA=true

WORKDIR /app

# Dependencies first for layer caching.
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && python -m pip install --only-binary=:all: -r requirements.txt

# Application code (data/, .venv*, tests, caches excluded via .dockerignore).
COPY . .

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

# Container Apps maps external 443 -> this targetPort. Streamlit binds it directly.
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8501')+'/_stcore/health',timeout=4).status==200 else 1)"

# Shell form so ${PORT:-8501} is honoured (Container Apps: 8501; App Service: set PORT).
CMD streamlit run app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false
