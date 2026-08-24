"""VIS-001 — Madrid Visual Counting Benchmark.

An isolated, preregistered feasibility experiment. It answers one narrow
question: can an off-the-shelf foundation object detector, with **zero** local
fine-tuning, count ``person`` / ``bicycle`` / ``car`` / ``bus`` reliably enough
on real public Madrid traffic-camera imagery to justify building a Visual
Evidence Layer?

It is not an SNTO feature. Nothing here is imported by ``src/``, ``app.py``,
``/api/v2`` or the mobile client, and nothing here writes to the SNTO database.

Importing this package pulls in the standard library only. The heavy computer
vision stack (``rfdetr``, ``torch``, ``supervision``) is imported lazily inside
:mod:`vis001.inference`, so the repository's normal test suite runs without it.
"""

from __future__ import annotations

__all__ = ["config"]
