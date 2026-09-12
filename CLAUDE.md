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
- UI: tkinter + ttk with ttkbootstrap (`bootstrap-light` theme) — chosen over sv-ttk, which looked stalled (no commits in over a year) when compared in Phase 3.
- Charts: matplotlib, embedded with FigureCanvasTkAgg + NavigationToolbar2Tk.
- Maths: numpy; pandas where it genuinely simplifies time-series work (not needed yet — a plain EWMA loop covered fitness/fatigue/form).
- Storage: SQLite via the built-in sqlite3 module. Database at `data/eps_runcoach.db` in dev, `%APPDATA%\EPS RunCoach\eps_runcoach.db` when packaged (see Packaging below).
- FIT parsing: fitdecode — pure-Python, simple API, easier to work with than Garmin's official FIT SDK for a beginner-driven project.
- AI coach: behind a provider interface. First provider: Gemini via `google-genai` (currently `gemini-3.8-flash`, the free-tier model as of Sep 2026). Key lives in `.env`, editable from the Settings page. Model name lives in settings, not code.
- Tests: pytest, for core code.
- Launch (dev): `uv run python -m eps_runcoach`.
- Launch (packaged): the desktop shortcut, or `dist\EPS_RunCoach\EPS_RunCoach.exe` directly.

## Packaging
- Built with PyInstaller from `eps_runcoach.spec` (onedir, not onefile — starts faster and is more reliable with the numpy/matplotlib stack; a desktop shortcut to the exe inside the output folder works the same either way).
- Rebuild with: `uv run pyinstaller eps_runcoach.spec --noconfirm`. Output goes to `dist/EPS_RunCoach/`. Safe to re-run any time — I expect to rebuild this regularly as the app changes, and the data location below is stable across rebuilds.
- `core/app_paths.py` detects `sys.frozen` (set by PyInstaller) to decide where data lives: the project's `data/` folder in dev, or `%APPDATA%\EPS RunCoach\` when packaged (database, `.env`, and backups all follow from there). Never hardcode a data path elsewhere — always go through `app_paths`.
- The desktop shortcut ("EPS RunCoach.lnk") points at `dist\EPS_RunCoach\EPS_RunCoach.exe` — it doesn't need recreating after a rebuild, since the exe's path and name don't change.
- App icon: `assets/icon.ico` (also `assets/icon.png`) — currently a generated placeholder (blue circle, "R"), swap the file for a real logo whenever there is one; no code changes needed elsewhere.

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
  __main__.py           # entry point: python -m eps_runcoach (launches the UI)
  core/
    app_paths.py        # dev vs packaged data/.env/resource locations (sys.frozen)
    fit_import.py       # FIT parsing, GPS stripping, sport classification
    db.py                # ALL SQL lives here; schema + migrations
    importer.py         # inbox/folder import, dedupe by file hash, backups
    metrics.py           # zones, TRIMP, sRPE, fitness/fatigue/form, 5k estimate
    training_data.py    # aggregates sessions into a TrainingSnapshot (Dashboard + coach share this)
    settings.py         # read/write user settings
    formatting.py       # date/duration/pace display helpers (core, not ui_tk - the coach needs them too)
    export.py           # export every table to CSV
    coach/
      base.py          # provider interface + CoachError types
      gemini.py        # Gemini provider
      api_key.py       # reads/writes the API key in .env
      context.py       # builds the compact training summary sent to the AI
      request.py       # orchestrates a coaching request: context -> provider -> save
      system_prompt.md # coach instructions (editable by me)
  charts/              # functions returning matplotlib Figures
  ui_tk/               # windows, pages, dialogs (app.py + pages/)
scripts/               # command-line utilities
tests/
assets/                # icon.ico / icon.png - bundled into the packaged exe
eps_runcoach.spec      # PyInstaller build config
data/                  # dev-only database + backups — NEVER commit
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
Phase 7 complete — packaged as a Windows app (PyInstaller, desktop shortcut, AppData storage, app icon, back up now, export to CSV). All Build Plan phases done; remaining work is the "Nice-to-haves" list and the per-lap distance calibration note above.
