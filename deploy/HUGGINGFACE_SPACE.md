# Publicar el dashboard SNTO en Hugging Face Spaces

Hugging Face Spaces ejecuta Streamlit de forma nativa y es **gratuito**. Da una demo pública sin
depender de Azure y con visibilidad en la comunidad de data science / remote sensing.

El dashboard corre sin base de datos con `USE_MOCK_DATA=true` (el default de `.env.example`), así que
no necesita PostGIS en el Space.

## Pasos

### 1. Crear el Space
- Ve a **huggingface.co/new-space**.
- Owner: tu usuario · Space name: `snto-observatory`.
- **SDK: Streamlit** · Hardware: CPU basic (free) · Visibility: Public.

### 2. Cabecera del Space (README del Space)
El Space necesita su propio `README.md` con este *front-matter* YAML al principio (Hugging Face lo
lee para configurar el contenedor). Crea este archivo **en el repo del Space**, no en el de GitHub
(o duplícalo):

```yaml
---
title: SNTO — Smart Nature Tourism Observatory
emoji: 🏔️
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.40.0"
app_file: app.py
pinned: false
license: other
---
```

> Ajusta `sdk_version` a la versión de Streamlit que tengas en `requirements.txt`.

### 3. Variables de entorno del Space
En **Settings → Variables and secrets** del Space añade:

```
USE_MOCK_DATA = true
```

(No subas secretos de BD ni de Azure: el demo no los usa.)

### 4. Subir el código
Dos opciones:

**A) Git (recomendado)**
```bash
git remote add space https://huggingface.co/spaces/TU_USUARIO/snto-observatory
git push space main
```

**B) Sincronización automática desde GitHub**
Configura un GitHub Action que haga `git push` al remoto del Space en cada release (HF documenta el
workflow oficial "Managing Spaces with GitHub Actions").

### 5. Cuidado con el tamaño
- El Space free tiene límites de almacenamiento. **No subas los rásteres Sentinel-2 ni los `.SAFE`**
  (ya están en `.gitignore`). El demo con `USE_MOCK_DATA=true` no los necesita.
- Verifica que `requirements.txt` instala limpio en el contenedor de HF (rasterio/geopandas tienen
  ruedas para Linux, no debería haber problema). Si el build falla por una dependencia pesada que el
  demo no usa, considera un `requirements-hf.txt` reducido.

### 6. Verificación
- Espera a que el Space construya (pestaña "Logs").
- Abre la URL pública y comprueba que carga el dashboard y las tres vistas.
- Añade el enlace del Space al README de GitHub junto al del dashboard de Azure.

## Por qué merece la pena
HF Spaces aparece en búsquedas de "remote sensing dashboard" y "tourism analytics" y es un escaparate
técnico internacional complementario al despliegue institucional en Azure.
