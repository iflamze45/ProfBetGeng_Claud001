#!/bin/bash
set -e
BASE="/Users/alexanderanthony/Backend Services/apis/ProfBetGeng_Claud001"
source "$BASE/venv/bin/activate"
cd "$BASE"
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
