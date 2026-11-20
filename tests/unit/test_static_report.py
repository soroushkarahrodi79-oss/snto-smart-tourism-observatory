# ruff: noqa: E501
"""Guards for the zero-cost static snapshot (site/index.html)."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "site" / "index.html").read_text(encoding="utf-8")


def test_static_report_is_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_static_report.py"), "--check"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout


def test_no_external_resources():
    assert not re.search(r"<script|<link|<img|@import|url\(", HTML, re.I)
    urls = set(re.findall(r"https?://[^\"'<) ]+", HTML))
    assert urls <= {
        "http://www.w3.org/2000/svg",
        "https://doi.org/10.5281/zenodo.20818269",
        "https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory",
    }


def test_evidence_caveats_present_and_no_overclaim():
    for needle in ("Sin validación de campo", "no</strong> es presión", "L2", "Copernicus"):
        assert needle in HTML
    assert not re.search(r"regenerativ|validado\b", HTML, re.I)
    assert "Azure" not in HTML


def test_all_assets_rendered():
    assert HTML.count("<tr>") == 22  # header + 21 assets
    assert HTML.count("<polygon") + HTML.count("<circle") == 21
