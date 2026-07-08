# Performance

## Purpose
Summarize performance concerns and future performance requirements.

## Background
Performance risk is currently tied to the Streamlit dashboard surface, large charts/maps, and repeated computation or file reads.

## Current State
The repository uses caching and PyDeck for improved map rendering, but does not yet define performance budgets, load tests, or operational metrics.

## Evidence
The repository audit noted PyDeck adoption and Streamlit caching as positives, while the CTO review identified missing load tests, observability, and performance budgets.

## Recommendations
Performance should be evaluated by workflow: executive overview load time, asset list filtering, map render, report export, and analysis job duration.

## Next Steps
Define baseline budgets before v2.0 product hardening.

## Related Documents
- [Scalability](scalability.md)
- [Dashboard Review](../ux/dashboard-review.md)

