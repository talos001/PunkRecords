# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PunkRecords (班克记录) is a "thinking second brain" project that connects LLMs with personal Wiki, allowing scattered notes and inspirations to converge, collide, and be reborn. The project is currently in its initial setup phase.

## Project Structure

- `README.md` - Project introduction (Chinese)
- `docs/ui_design.md` - **UI/product design spec (source of truth)**; all UI-related decisions must be recorded and updated there
- `docs/api-outline.md` - **Backend API requirements** for frontend integration (update when contracts change)
- `frontend/` - **Vite + React + TypeScript** web UI (`npm run dev` in `frontend/`)
- `src/api/` - **FastAPI** HTTP service (`poetry run punkrecords serve` or `punkrecords-serve`)
- `arch/` - Architecture documentation and diagrams
  - `punkrecords-architecture.png` - System architecture diagram

## Current State

Python package with CLI, graph/vault/agent modules, and a **FastAPI** HTTP API. Web UI lives under `frontend/`.

## Common Commands

- `poetry run pytest` — run tests
- `poetry run punkrecords serve --port 8765` — start API server
- `cd frontend && npm run dev` — Vite dev server (set `VITE_API_BASE_URL` to talk to the API)

## UI design

When changing or implementing user-facing behavior, layouts, or copy: read and update `docs/ui_design.md` in the same change. Do not leave UI decisions only in issues or chat.

## Architecture

The high-level architecture is documented in `arch/punkrecords-architecture.png`. Always refer to this diagram when understanding the intended system design.

The vision: Connect LLM with personal Wiki to create a knowledge warehouse that externalizes and augments human thinking, serving as a second brain that can "think" by processing and connecting ideas.
