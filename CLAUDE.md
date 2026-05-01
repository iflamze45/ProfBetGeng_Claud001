# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProfBetGeng (PBG) is a SportyBet → Bet9ja ticket converter with AI-driven risk analysis. The core pipeline: parse raw SportyBet selections → normalize to an internal `InternalTicket` → convert to a `ConvertedTicket` for Bet9ja → optionally run `TicketPulse` risk analysis via Claude API.

## Commands

All commands run from the repo root unless noted.

```bash
# Run in: Claude Code Terminal
cd "/Users/alexanderanthony/Backend Services/apis/ProfBetGeng_Claud001"

# Install dependencies
pip install -r requirements.txt

# Start backend dev server
uvicorn backend.main:app --reload --port 8000

# Run all tests
python -m pytest backend/tests/ -v

# Run a single test file
python -m pytest backend/tests/test_pbg.py -v

# Run a single test
python -m pytest backend/tests/test_pbg.py::TestSpotybetParser::test_parse_1x2 -v

# Run tests with asyncio mode
python -m pytest backend/tests/test_ticket_pulse.py -v --asyncio-mode=auto

## ❗ Mandatory Agent Verification Protocol
**AGENTS:** Before claiming "Success" or "Task Complete", you MUST run the following checks. Do not skip this! The user has requested strict verification to avoid regressions:
1. `cd "/Users/alexanderanthony/Backend Services/apis/ProfBetGeng_Claud001" && /usr/local/bin/python3 -m pytest backend/tests/ -v`
2. `cd "/Users/alexanderanthony/Landing Page Sites/tools/profbetgeng-app" && export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 && npx vite build`

If either command fails, YOU MUST FIX the syntax/test failure before responding to the user.

Frontend (scaffold only):
```bash
cd frontend && npm install && npm run dev
```

## Architecture

### Data Flow

```
SportybetTicket (raw input)
  → SportybetAdapter.parse()       → InternalTicket + warnings
    → Bet9jaConverter.convert()    → ConvertedTicket
      → TicketPulseService.analyse() → RiskReport (optional, AI-powered)
```

### Backend Module Map

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app factory (`create_app()`), CORS, router mount |
| `backend/routes.py` | All API endpoints; module-level `parser` and `converter` singletons |
| `backend/models.py` | All Pydantic schemas and dataclasses — single source of truth for types |
| `backend/config.py` | `Settings` via `pydantic-settings`, loaded from `backend/.env`, cached with `@lru_cache` |
| `backend/batch.py` | Batch request/response schemas; batch logic lives in `routes.py` |
| `backend/services/sportybet_parser.py` | `SportybetAdapter` — market mapping, AH quarter-ball split, confidence scoring |
| `backend/services/converter.py` | `Bet9jaConverter` — market registry, pick normalization table |
| `backend/services/ticket_pulse.py` | `TicketPulseService` (Claude API) + `_heuristic_score` fallback; `MockTicketPulseService` for tests |
| `backend/services/auth.py` | `APIKeyService` (Supabase) + `MockAPIKeyService`; `require_api_key` FastAPI dependency |
| `backend/services/storage.py` | `SupabaseStorageService` + `MockStorageService` |

### Key Design Patterns

**Protocol + Mock pairs**: Every service has a `Protocol` interface, a production implementation (Supabase/Claude), and a `Mock*` implementation injected during tests. Routes use `Depends()` with getter functions so mocks can be patched.

**Auth flow**: `require_api_key` extracts the `X-API-Key` header. When `auth_enabled=True`, the route then validates via the injected auth service. `dev_bypass` short-circuits validation when `auth_enabled=False`.

**TicketPulse fallback**: `TicketPulseService.analyse()` calls Claude API; on timeout, HTTP error, or JSON parse failure it silently falls back to `_heuristic_score()` and sets `source="heuristic_fallback"`.

**Batch**: `POST /api/v1/convert-batch` runs up to 20 tickets concurrently via `asyncio.gather`. Individual failures are captured per-index; the batch never aborts. Gated by `batch_enabled` flag in settings.

**Response Intelligence (M2 Step 3)**: `/api/v1/convert` returns a composite `analysis` object with `pulse` (TicketPulseService RiskReport) and `metrics` (RiskEngine hardened metrics), plus a `sentiment` field from SentimentAnalysisService. All gated by `include_analysis` flag. `/api/v1/analyse` and `/api/v1/analyse/stream` are standalone analysis endpoints.

## M2 Milestone Status

| Step | Name | Status |
|------|------|--------|
| 1 | Adapter Architecture | ✅ Complete |
| 2 | Parser Depth Expansion | ✅ Complete |
| 3 | Response Intelligence | ✅ Complete — 117/117 tests passing (2026-04-30) |

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| POST | `/api/v1/convert` | X-API-Key | Single ticket conversion + optional analysis |
| POST | `/api/v1/analyse` | X-API-Key | Risk analysis of a pre-converted ticket |
| GET | `/api/v1/history` | X-API-Key | Conversion history for the key |
| POST | `/api/v1/keys` | None | Generate a new API key |
| POST | `/api/v1/convert-batch` | X-API-Key | Batch convert up to 10 tickets |

### Environment Variables (`backend/.env`)

```
AUTH_ENABLED=true
BATCH_ENABLED=false
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
ANTHROPIC_API_KEY=
```

### Test Structure

Tests use `fastapi.testclient.TestClient`. `conftest.py` patches `sys.path`. The test suite has three import styles — `from ..models import` (relative, used in `test_pbg.py`) and `from backend.models import` (absolute, used in `test_ticket_pulse.py`) — both work because `conftest.py` adds the repo root to `sys.path`.

Batch tests (`test_batch.py`) use `unittest.mock.patch` to mock `get_settings`, `parser`, `converter`, `get_storage_service`, `get_pulse_service`, and `require_api_key` at the `backend.routes` namespace.

### Supabase Tables (production)

- `api_keys`: `key_hash`, `label`, `owner`, `created_at`, `is_active`
- `conversions`: `api_key`, `source_booking_code`, `source_platform`, `target_platform`, `selections_count`, `converted_count`, `skipped_count`, `created_at`
