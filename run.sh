#!/usr/bin/env bash
# Instala dependencias y arranca el chat (mismo comando que usa Render)
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
