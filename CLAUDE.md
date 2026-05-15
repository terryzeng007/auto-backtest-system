# CLAUDE.md — Auto Backtest

## Project
- **Path:** E:\opencode_project\auto-backtest-system
- **Python:** D:\Git_Project\python3.11\python.exe
- **Venv:** .venv
- **GitHub:** terryzeng007/auto-backtest-system

## Commands
- Install: `.venv\Scripts\activate && pip install -r requirements.txt`
- Run: `.venv\Scripts\activate && python main.py`
- Test: `.venv\Scripts\activate && python -m pytest tests/ -v`

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

## Architecture
- Backend: Flask API (app/)
- Desktop: Streamlit frontend (frontend/)
- Mobile: H5 Flask+ECharts (h5/)
- Data: Tushare (primary), AKShare (future)
- AI: 火山引擎 API (glm-5.1), >3s fallback to rule engine
