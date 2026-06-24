"""
Genera docs/SNTO_Whitepaper_2026_Karahrodi.html (listo para imprimir como PDF).
Uso: python scripts/make_whitepaper_pdf.py
Luego: abrir el HTML en Chrome/Edge → Ctrl+P → Guardar como PDF → Sin márgenes del navegador.
Requiere: markdown  (pip install markdown)
"""
import re
from pathlib import Path
import markdown as md_lib

ROOT = Path(__file__).parent.parent
SRC  = ROOT / "WHITEPAPER_SNTO_Architecture_Blueprint.md"
OUT  = ROOT / "docs" / "SNTO_Whitepaper_2026_Karahrodi.html"

raw = SRC.read_text(encoding="utf-8")

# Convertir a HTML con extensiones estándar
body_html = md_lib.markdown(
    raw,
    extensions=["tables", "fenced_code", "toc", "attr_list"],
)

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="author" content="Soroush Karahrodi">
<meta name="description" content="SNTO — Smart Nature Tourism Observatory: Architecture Blueprint and Technical Whitepaper">
<title>SNTO Whitepaper 2026 · Karahrodi</title>
<style>
/* ── Fuentes ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..600&family=Source+Code+Pro:wght@400;600&display=swap');

:root {{
  --blue:   #1a4f9c;
  --mid:    #2d6ab4;
  --light:  #e8f0fc;
  --text:   #1a2332;
  --meta:   #6b7c93;
  --rule:   #c8d6e8;
  --code-bg:#f3f6fb;
  --accent: #0f4c8a;
}}

/* ── Base ────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html {{ font-size: 10.5pt; }}

body {{
  font-family: 'Source Serif 4', Georgia, serif;
  color: var(--text);
  background: #fff;
  line-height: 1.65;
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 40px 80px;
}}

/* ── Cover (printed as first page) ──────────────────────── */
.cover {{
  text-align: center;
  padding: 60px 0 40px;
  border-bottom: 2.5px solid var(--blue);
  margin-bottom: 48px;
  page-break-after: always;
}}
.cover h1 {{
  font-size: 26pt;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}}
.cover .subtitle {{
  font-size: 13pt;
  color: var(--mid);
  font-weight: 300;
  margin-bottom: 24px;
}}
.cover .meta {{
  font-size: 10pt;
  color: var(--meta);
  line-height: 1.8;
}}
.cover .doi {{
  display: inline-block;
  margin-top: 16px;
  padding: 5px 14px;
  background: var(--light);
  border-radius: 4px;
  font-size: 9pt;
  color: var(--blue);
  font-family: 'Source Code Pro', monospace;
}}

/* ── Headings ────────────────────────────────────────────── */
h1, h2, h3, h4, h5 {{
  font-family: 'Source Serif 4', Georgia, serif;
  color: var(--accent);
  margin-top: 1.8em;
  margin-bottom: 0.4em;
  line-height: 1.2;
  page-break-after: avoid;
}}
h1 {{ font-size: 18pt; border-bottom: 1.5px solid var(--rule); padding-bottom: 6px; }}
h2 {{ font-size: 14pt; color: var(--blue); }}
h3 {{ font-size: 12pt; color: #2a5298; }}
h4 {{ font-size: 10.5pt; font-style: italic; color: #3a6abf; }}

/* ── Body text ───────────────────────────────────────────── */
p {{ margin: 0.7em 0; text-align: justify; hyphens: auto; }}

/* ── Tables ──────────────────────────────────────────────── */
table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 9pt;
  margin: 1.2em 0;
  page-break-inside: avoid;
}}
th {{
  background: var(--blue);
  color: #fff;
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
}}
td {{ padding: 5px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
tr:nth-child(even) td {{ background: var(--light); }}

/* ── Code ────────────────────────────────────────────────── */
pre {{
  background: var(--code-bg);
  border-left: 3px solid var(--mid);
  border-radius: 3px;
  padding: 12px 16px;
  font-size: 8.5pt;
  font-family: 'Source Code Pro', 'Courier New', monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  margin: 1em 0;
  page-break-inside: avoid;
}}
code {{
  font-family: 'Source Code Pro', 'Courier New', monospace;
  font-size: 0.88em;
  background: var(--code-bg);
  padding: 1px 4px;
  border-radius: 2px;
}}
pre code {{ background: none; padding: 0; font-size: inherit; }}

/* ── Blockquote ──────────────────────────────────────────── */
blockquote {{
  border-left: 3px solid var(--mid);
  margin: 1em 0;
  padding: 8px 16px;
  background: var(--light);
  border-radius: 0 4px 4px 0;
  font-style: italic;
  color: #2a4a7a;
}}

/* ── Lists ───────────────────────────────────────────────── */
ul, ol {{ padding-left: 1.8em; margin: 0.6em 0; }}
li {{ margin: 0.25em 0; }}

/* ── Links ───────────────────────────────────────────────── */
a {{ color: var(--blue); text-decoration: none; }}

/* ── Footer strip ────────────────────────────────────────── */
.doc-footer {{
  margin-top: 60px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
  font-size: 8pt;
  color: var(--meta);
  text-align: center;
  line-height: 1.8;
}}

/* ═══════════════════════════════════════════════════════════
   PRINT STYLES — lo que realmente sale en el PDF
   ═══════════════════════════════════════════════════════════ */
@media print {{
  html {{ font-size: 10pt; }}
  body {{ max-width: 100%; padding: 0; margin: 0; }}

  @page {{
    size: A4;
    margin: 18mm 20mm 18mm 20mm;
    @bottom-center {{
      content: "Pág. " counter(page) "  ·  DOI: 10.5281/zenodo.20818270";
      font-size: 7.5pt;
      color: #8a9bb0;
    }}
  }}

  .cover {{ padding: 40px 0 30px; }}
  h1, h2, h3 {{ page-break-after: avoid; }}
  pre, table, blockquote {{ page-break-inside: avoid; }}
  a {{ color: inherit; text-decoration: none; }}
  .doc-footer {{ display: none; }}

  /* Print hint bar */
  .print-hint {{ display: none; }}
}}

/* ── Print hint (screen only) ────────────────────────────── */
.print-hint {{
  position: fixed;
  top: 0; left: 0; right: 0;
  background: #1a4f9c;
  color: #fff;
  text-align: center;
  padding: 10px;
  font-size: 12px;
  z-index: 999;
  font-family: system-ui, sans-serif;
}}
.print-hint kbd {{
  background: rgba(255,255,255,0.25);
  padding: 2px 7px;
  border-radius: 3px;
  font-family: inherit;
}}
</style>
</head>
<body>

<div class="print-hint">
  Para guardar como PDF: <kbd>Ctrl+P</kbd> → Destino: <strong>Guardar como PDF</strong>
  → Márgenes: Ninguno → Activar "Gráficos de fondo" → Guardar
</div>

<div class="cover">
  <h1>SNTO — Smart Nature Tourism Observatory</h1>
  <div class="subtitle">Architecture Blueprint &amp; Technical Whitepaper</div>
  <div class="meta">
    Soroush Karahrodi<br>
    Universidad Complutense de Madrid (UCM)<br>
    Supervisión: Carmen Mínguez · Susana Ramírez García (REGENERA)<br>
    Junio 2026
  </div>
  <div class="doi">DOI: 10.5281/zenodo.20818270</div>
</div>

{body_html}

<div class="doc-footer">
  SNTO — Smart Nature Tourism Observatory &nbsp;·&nbsp;
  DOI: <a href="https://doi.org/10.5281/zenodo.20818270">10.5281/zenodo.20818270</a> &nbsp;·&nbsp;
  <a href="https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory">GitHub</a> &nbsp;·&nbsp;
  Licencia de uso académico — Universidad Complutense de Madrid, 2026
</div>

</body>
</html>
"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK  {OUT}")
print()
print("Siguiente paso:")
print("  1. Abre el archivo en Chrome o Edge")
print("  2. Ctrl+P → Destino: 'Guardar como PDF'")
print("  3. Márgenes: Ninguno | Activar 'Gráficos de fondo'")
print("  4. Guardar como: SNTO_Whitepaper_2026_Karahrodi.pdf")
