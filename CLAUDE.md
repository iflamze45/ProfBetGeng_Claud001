# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProfBetGeng (Claud001) is a SportyBet to Bet9ja ticket converter with AI-driven risk analysis. The platform takes betting tickets from SportyBet, converts them to equivalent Bet9ja tickets, and provides AI-powered risk assessment.

## Repository Structure

Monorepo with two top-level directories:

- **`backend/`** — Python API server (framework TBD, scaffold only)
- **`frontend/`** — React (JSX) web application (build tooling TBD, scaffold only)

## Current State

This project is in initial scaffold phase. All source files are empty placeholders. The following needs to be set up before development can begin:

### Backend (`backend/`)
- Choose and install Python web framework (FastAPI recommended for async + auto-docs)
- Set up `requirements.txt` or `pyproject.toml` with dependencies
- Implement `main.py` (app entry point), `routes.py` (API endpoints), `models.py` (data schemas)
- Configure `services/` for business logic (ticket conversion, AI risk analysis)
- Set up `prompts/` with AI prompt templates for risk analysis
- Add test framework (pytest) in `tests/`
- Populate `backend/.env` with required environment variables

### Frontend (`frontend/`)
- Initialize with Vite + React (run `npm create vite@latest` or set up manually)
- Create `package.json` with scripts and dependencies
- Build out `src/components/`, `src/pages/`, `src/services/`
- Set up `index.html` as the Vite entry point

## Architecture

```
backend/
├── main.py          # App entry point and server config
├── routes.py        # API endpoint definitions
├── models.py        # Data models / schemas
├── models/          # Extended model definitions
├── services/        # Business logic (conversion engine, AI analysis)
├── prompts/         # AI prompt templates for risk analysis
├── tests/           # Test suite
└── .env             # Environment variables (not committed)

frontend/
├── index.html       # HTML entry point
├── public/          # Static assets
└── src/
    ├── App.jsx      # Root React component
    ├── components/  # Reusable UI components
    ├── pages/       # Route-level page components
    └── services/    # API client layer
```

## Commands

No build tooling is configured yet. Once set up, expected commands:

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt    # Install dependencies
python main.py                      # Run dev server
pytest tests/                       # Run all tests
pytest tests/test_file.py::test_name  # Run single test
```

### Frontend (React)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start dev server
npm run build        # Production build
npm test             # Run tests
```

## Key Domain Concepts

- **Ticket conversion**: Mapping bet selections from SportyBet's format/odds to Bet9ja equivalents
- **Risk analysis**: AI-powered assessment of converted tickets (confidence, odds comparison, potential discrepancies)
- **Booking codes**: Both platforms use booking codes that encode bet selections; the converter must parse and re-encode between formats
