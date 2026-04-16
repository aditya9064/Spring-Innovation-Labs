# Workers

This folder is for ingestion, normalization, geospatial resolution, and publishing jobs.

Starter job stubs:

- `jobs/ingest.py`: narrow normalization helper for live-event rows
- `jobs/publish_live.py`: helper for turning normalized events into feed rows
- `jobs/ingest_live.py`: normalize live-event rows into a stable shape
- `jobs/build_tract_package.py`: package tract-level score payloads for API use

Keep worker output aligned to `data_samples/` until the contracts are intentionally changed.
