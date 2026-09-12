# EPS RunCoach — project brief

## What this is
A private, single-user Windows desktop app that helps me (a recreational runner) get my 5k under 25 minutes. It imports sessions recorded on my Suunto 9 Baro (FIT files exported from the Suunto app on my Pixel 8 and dropped into an inbox folder on my PC), tracks runs and strength sessions, captures my notes on how sessions felt, calculates training metrics, and uses an AI coach to review each session and advise on the next.

This is a desktop prototype. It will later be ported to web and/or mobile (Streamlit, Kivy), so the architecture rules below matter more than polish.

## About me as a developer
I'm a beginner with a bit of scripting experience. I'm building this by vibe coding.
- After each change, explain what you did in plain English, in a few sentences.
- Plan before writing code for anything bigger than a small fix, and wait for my OK.
- Work in small steps I can test. Tell me exactly how to test each step.
- Ask before adding a new dependency, and tell me why it's needed.
- When I say "commit", commit with a clear, descriptive message.

## Tech stack
- Python 3.14 from python.org (system Python, NOT uv-managed — we need its Tcl/Tk). Dependencies managed with uv (`uv add`, `uv run`). Never use pip directly.
- UI: tkinter + ttk, with a modern theme (sv-ttk or ttkbootstrap — to be decided in Phase 3).
- Charts: matplotlib, embedded with FigureCanvasTkAgg + NavigationToolbar2Tk.
- Maths: numpy; pandas where it genuinely simplifies time-series work.
- Storage: SQLite via the built-in sqlite3 module. Database at data/eps_runcoach.db.
- FIT parsing: fitdecode — pure-Python, simple API, easier to work with than Garmin's official FIT SDK for a beginner-driven project.
- AI coach: behind a provider interface. First provider: Gemini via `google-genai` (free tier, Flash model). Key from `.env` via python-dotenv. Model name lives in settings, not code.
- Tests: pytest, for core code.
- Launch: `uv run python -m eps_runcoach`. Later packaged with PyInstaller.

## Architecture — the most important rule
Three layers, dependencies point downwards only:
```
eps_runcoach/ui_tk/   → may import charts and core
eps_runcoach/charts/  → may import core; returns matplotlib Figure objects; no tkinter
eps_runcoach/core/    → NO tkinter, NO matplotlib, NO UI code of any kind
```
Core must be reusable unchanged in a future Streamlit or Kivy app. If a feature seems to need UI code in core, stop and ask me.

## Structure
```
eps_runcoach/
  __main__.py          # entry point: python -m runcoach
  core/
    fit_import.py      # FIT parsing, GPS stripping, sport classification
    db.py              # ALL SQL lives here; schema + migrations
    importer.py        # inbox/folder import, dedupe by file hash, backups
    metrics.py         # zones, TRIMP, sRPE, fitness/fatigue/form, 5k estimate
    settings.py        # read/write user settings
    coach/
      base.py          # provider interface
      gemini.py        # Gemini provider
      context.py       # builds the compact training summary sent to the AI
      system_prompt.md # coach instructions (editable by me)
  charts/              # functions returning matplotlib Figures
  ui_tk/               # windows, pages, dialogs
scripts/               # command-line utilities
tests/
data/                  # database + backups — NEVER commit
sample_data/           # my FIT files — NEVER commit
```

## Tkinter rules
- Never block the main thread. Imports and AI calls run in background threads; pass results back via a queue polled with `after()`. Never touch widgets from a background thread.
- Enable per-monitor DPI awareness at startup on Windows.
- Build charts with `matplotlib.figure.Figure`, never `pyplot`. Destroy old canvases when switching views.
- Keep widgets readable at normal laptop sizes; avoid fixed pixel sizes where possible.

## Non-negotiable rules
- **Privacy:** Discard all GPS coordinates on import; never store them. Never send raw files, GPS, or personal identifiers to the AI — only summarised stats and my notes.
- **Secrets:** The API key lives only in `.env`, which is git-ignored. Never hard-code or print it. The Settings page may offer a field for it, but it must write straight through to `.env` (via python-dotenv) — never into the SQLite database. Never encrypt or hash it: this is a single-user local app, hashing would break authentication (the raw key must be sent to the API), and the real risk (accidentally committing it to git) is already handled by `.gitignore`. Check before any push that no secrets, `data/` or `sample_data/` are included.
- **Data safety:** Back up the database before imports and migrations. Never delete my data without asking.
- **Safety in coaching:** The coach must be conservative about pain and injury, never advise pushing through pain, and suggest a physio for persistent or worsening niggles.
- **Units and language:** Kilometres, min/km pace, UK English, dates as DD/MM/YYYY.
- **Resilience:** Handle bad or unusual FIT files, missing internet and AI rate-limit errors with friendly messages rather than crashes.

## Domain notes
- Goal pace for sub-25 5k: 5:00/km.
- Strength sessions from the Suunto have duration and heart rate only; sets and reps are not available. Use my RPE and focus tag (legs / upper / full body / core) to judge their impact, especially leg sessions within 48 hours of hard runs.
- Heart-rate load tends to underestimate strength work, so session-RPE load (RPE × minutes) is used alongside TRIMP.
- Fitness = 42-day exponentially weighted load; fatigue = 7-day; form = fitness − fatigue.

## Current status
Phase 1 — project setup and reading FIT files. (Update this line as phases are completed.)
