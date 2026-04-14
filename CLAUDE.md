# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PunkRecords (班克记录) is a "thinking second brain" project that connects LLMs with personal Wiki, allowing scattered notes and inspirations to converge, collide, and be reborn. The project is currently in its initial setup phase.

## Project Structure

- `README.md` - Project introduction (Chinese)
- `docs/ui_design.md` - **UI/product design spec (source of truth)**; all UI-related decisions must be recorded and updated there
- `docs/api-outline.md` - **Backend API requirements** for frontend integration (update when contracts change)
- `docs/backlog.md` - **Planned-for-implementation** backlog (eligible for scheduling)
- `docs/function_plan.md` - **Discussion / tentative ideas only**; **not** a commitment to build; move items to `backlog.md` once approved for implementation
- `frontend/` - **Vite + React + TypeScript** web UI (`npm run dev` in `frontend/`)
- `src/api/` - **FastAPI** HTTP service (`poetry run punkrecords serve` or `punkrecords-serve`)
- `docs/arch/` - Architecture documentation and diagrams
  - `docs/arch/punkrecords_arch.png` - System architecture diagram
  - `docs/arch/PunkRecords_Arch.md` - Architecture notes (Markdown)

## Current State

Python package with CLI, graph/vault/agent modules, and a **FastAPI** HTTP API. Web UI lives under `frontend/`.

## Common Commands

- `poetry run pytest` — run tests
- `poetry run punkrecords serve --port 8765` — start API server
- `cd frontend && npm run dev` — Vite dev server (set `VITE_API_BASE_URL` to talk to the API)

## UI design

When changing or implementing user-facing behavior, layouts, or copy: read and update `docs/ui_design.md` in the same change. Do not leave UI decisions only in issues or chat.

## Planning and completion tracking

- `docs/function_plan.md` remains discussion-only. Items there are not implementation commitments.
- When an item is approved for implementation, move/record it in `docs/backlog.md`.
- When an implemented item reaches completed status, **always** append a completion record in `docs/backlog.md` (status/date/source section), so backlog is the canonical history of completed planned work.

## Architecture

The high-level architecture is documented in `docs/arch/punkrecords_arch.png` (and `docs/arch/PunkRecords_Arch.md`). Refer to these when understanding the intended system design.

The vision: Connect LLM with personal Wiki to create a knowledge warehouse that externalizes and augments human thinking, serving as a second brain that can "think" by processing and connecting ideas.
