# CrimeScope Build Repo

This repository is the implementation workspace for the CrimeScope build.

The planning and rubric documents stay in the parent workspace:

- `/Volumes/External Sabrent ssd/Spring-Innovation-Labs/docs`

This repo exists for code, contracts, infrastructure, and sample payloads only.

## Target Build

- City: `Chicago`
- Geography: `census tract`
- Primary persona: `insurer`
- Interface: `2D map-first dashboard + report surface`
- Core rule: verified historical scoring stays separate from governed live signals

## Starter Layout

- `frontend/`: Next.js UI scaffold
- `backend/`: FastAPI API scaffold
- `workers/`: ingestion and packaging job stubs
- `infra/`: local Postgres/PostGIS + Redis
- `data_samples/`: starter JSON contracts
- `docs/`: repo-local implementation notes
- `tests/`: lightweight scaffold checks
- `.env.example`: local environment variable template
- `Makefile`: basic dev and verification shortcuts
- `AGENTS.md`: repo-level workflow for Antigravity and other coding agents

## Immediate Next Steps

1. Freeze contract fields in `data_samples/`.
2. Connect backend routes to real tables instead of sample JSON.
3. Let Squads A and B work in parallel from the agreed contracts.
4. Merge into shared frontend work after payload shapes stop moving.

## Local Helpers

- Copy `.env.example` to `.env` when you start wiring local services.
- `make verify-samples` checks the starter contracts.
- `make backend-dev` starts the API once backend dependencies are installed.
- `make frontend-dev` starts the frontend once frontend dependencies are installed.
- `docs/ANTIGRAVITY_AGENT_PROMPT.md` has a copy-paste prompt for custom agent setup.
