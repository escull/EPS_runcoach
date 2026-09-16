# RunCoach: Build Plan (Desktop Edition)

*A personal, AI-assisted training app for a sub-25 minute 5k. Prototyped as a Windows desktop app in Python, built by vibe coding, and structured so it can be ported to Android, iOS or the web later.*

---

## 1. What we're building

RunCoach is a desktop app for your Windows PC. After a session, you send the FIT file from the Suunto app on your Pixel to your PC, click "Import", add a quick note about how it felt, and get a short review of the session plus advice for your next one.

Behind the scenes, the app reads every run and gym session your Suunto 9 Baro records, works out how hard each one was, tracks your fitness and fatigue over time, and watches your progress towards the goal. The AI coach only interprets those numbers; the app does the maths itself, which makes the advice more reliable and keeps the free AI allowance going a long way.

### Your profile, as captured in the interview

| Item | Answer |
|---|---|
| Current 5k | 25–30 minutes |
| Goal | Sub-25 (5:00 per km or faster), no deadline |
| Other training | Strength / gym, recorded on the Suunto (duration and heart rate only) |
| Platform | Windows desktop now; Android, iOS or web later |
| Coding experience | A bit of scripting and tinkering |
| AI | Gemini's free tier to start; Claude available as an alternative |
| AI jobs | Review each session and advise on the next, taking your notes into account |
| Current niggles | Sore ankle; occasional stitch |

---

## 2. Key decisions and why

**Python with Tkinter for the interface.** Tkinter comes built into the official Windows Python, so there's nothing extra to install and it's very well known to AI coding tools. Out of the box it looks a bit dated, so we'll add a modern theme on top (see Phase 3). It's still plain Tkinter underneath.

**matplotlib for charts, numpy (and pandas) for the maths.** matplotlib charts embed directly inside Tkinter windows, with zoom and pan built in. numpy handles the number crunching (heart-rate zones, training load, rolling averages), and pandas makes working with time-series data like splits and weekly totals much easier.

**SQLite for storage, via Python's built-in `sqlite3` module.** Your whole training history lives in one file on your PC. No server, no account, no setup. All database code sits in one module, so if you later move to a cloud database, only that module changes.

**A strict split between "core" and "UI".** This is the most important decision in the plan, because it's what makes porting possible later. A Tkinter interface can't be moved to Android or iOS; it will have to be rebuilt. But if the FIT reading, database, metrics and AI coach live in a `core` package that never imports anything from Tkinter, all of that carries over untouched, and only the relatively thin interface layer needs redoing. Charts sit in their own middle layer, since matplotlib works on any desktop or web backend.

**An "inbox" folder for getting files off your phone.** RunCoach watches a folder on your PC and imports any new FIT files it finds there, skipping ones it has already seen. You fill that folder however suits you. Google's **Quick Share** app for Windows lets you send files from the Pixel's share menu straight to your PC over Wi-Fi, with no cloud involved. A USB cable works too. If you don't mind a cloud hop, Google Drive for desktop can sync a phone folder to your PC automatically.

**The AI coach is the one online piece.** The Gemini API is called over the internet when you ask for coaching; everything else runs offline. A free API key from Google AI Studio needs no credit card. The free tier is limited to Gemini's Flash models, which are more than capable of this job. Google may use free-tier inputs and outputs to improve its models, so RunCoach will only ever send summarised numbers and your notes, never raw files, GPS data or your name. The AI code sits behind a simple "provider" switch so moving to Claude, or a paid Gemini tier, is a small change.

**No GPS stored at all.** For a 5k-focused coach, routes add little, and keeping them means holding a record of where you live. RunCoach discards GPS coordinates on import. Distance, pace, heart rate, cadence and altitude are all still available without them.

**Claude Code as your vibe-coding tool.** You describe what you want in plain English; it writes the code, runs it, and fixes errors. It runs natively on Windows and needs a paid Claude plan (Pro or above). If you only have the free Claude plan, Google's Gemini CLI is a free alternative that works in a similar way; the prompts in this plan work with either.

### Running costs

Nothing, apart from a Claude subscription if you choose Claude Code over Gemini CLI. The Gemini API free tier covers the coach; everything else is free, open-source software running on your own PC.

---

## 3. How it fits together

```
 Suunto 9 Baro ──sync──> Suunto app (Pixel)
                              │  export .fit
                              ▼  Quick Share / USB / Drive
                     Inbox folder on your PC
                              │
                              ▼
 ┌──────────────────── RunCoach (desktop app) ─────────────────────┐
 │                                                                  │
 │  ui_tk/    Tkinter windows, forms, tables   ◄── rebuilt when     │
 │     │                                          porting           │
 │  charts/   matplotlib figures              ◄── reusable on       │
 │     │                                          desktop and web   │
 │  core/     FIT import · SQLite · metrics   ◄── reusable          │
 │            AI coach · settings                 everywhere        │
 │                                                                  │
 └──────────────┬──────────────────────────────────────┬────────────┘
                ▼                                      ▼
        runcoach.db (SQLite)                  Gemini API (summary only)
```

The arrows only point downwards: the UI can use charts and core, charts can use core, but core never knows the UI exists.

---
## 4. Windows development environment setup

Allow about an hour. Every command below is typed into **PowerShell**. Open it by pressing the Windows key, typing `PowerShell`, and pressing Enter (Windows Terminal works too). You do not need to run it as Administrator. After installing each tool, **close PowerShell and open a fresh window** before using it; this is the fix for most "command not found" errors on Windows.

These steps use `winget`, Windows' built-in package installer. Check it's there first:

```powershell
winget --version
```

If that prints a version number, you're set. If not, install "App Installer" from the Microsoft Store.

### Step 1: Git (version control)

Git records every change to your code, so if the AI breaks something you can roll back to the last working version. This is the single most important safety net in vibe coding.

```powershell
winget install --id Git.Git -e
```

Reopen PowerShell, then tell Git who you are:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

### Step 2: VS Code (code editor)

You won't write much code by hand, but you'll want to see the files and review what the AI changed.

```powershell
winget install --id Microsoft.VisualStudioCode -e
```

Open VS Code, go to the Extensions panel (the four-squares icon on the left) and install the **Python** extension by Microsoft. If you're using Claude Code, also install the **Claude Code** extension, which shows its changes side by side in the editor.

### Step 3: Python 3.12 (the official installer)

For a Tkinter project, use the official Python from python.org rather than a third-party build. It comes with Tcl/Tk, the engine behind Tkinter, set up correctly. Some alternative Python builds have had problems finding Tcl/Tk on Windows, and that's an annoying thing to debug on day one.

```powershell
winget install --id Python.Python.3.12 -e
```

Reopen PowerShell and check Tkinter works:

```powershell
py -3.12 -m tkinter
```

A small window should appear saying "This is Tcl/Tk version 8.6" with a couple of buttons. Close it. If you see that, Tkinter is ready.

We use Python 3.12 because every library in this plan supports it well, and so does Kivy if you port to Android later.

### Step 4: uv (package manager)

`uv` keeps each project's libraries separate and makes installing them fast and painless. We'll tell it to use the official Python you just installed.

```powershell
winget install --id astral-sh.uv -e
```

Reopen PowerShell and check with `uv --version`.

### Step 5: Your AI coding tool

**Option A — Claude Code (needs Claude Pro or above):**

```powershell
irm https://claude.ai/install.ps1 | iex
```

Reopen PowerShell and run `claude`. A browser window opens for you to log in; this happens only once. Check it worked with `claude --version`. If Windows says `claude` isn't recognised, the installer will have printed a folder path; add that to your user PATH (search Windows for "Edit environment variables for your account") and reopen PowerShell.

If you'd rather avoid the terminal, the Claude Desktop app has a Code tab that does the same job with a friendlier interface.

**Option B — Gemini CLI (free with a Google account):** Gemini CLI needs Node.js first. Install it with `winget install --id OpenJS.NodeJS.LTS -e`, reopen PowerShell, then follow the install instructions on Google's Gemini CLI GitHub page (at the time of writing, `npm install -g @google/gemini-cli`, then run `gemini`).

### Step 6: Create the project folder

```powershell
mkdir C:\dev\runcoach
cd C:\dev\runcoach
git init
mkdir sample_data
```

Copy the `CLAUDE.md` file that came with this plan into `C:\dev\runcoach`. It's a project brief that your AI tool reads at the start of every session, so it always knows the goal, the architecture and the rules. (If you use Gemini CLI, make a copy of it named `GEMINI.md`.)

Open the folder in VS Code with:

```powershell
code .
```

### Step 7: Set up the phone-to-PC route

Pick one of these and test it with a single file:

**Quick Share (recommended, no cloud):** Install Google's Quick Share app for Windows, sign in with the same Google account as your Pixel, and set its save location to a folder such as `C:\RunCoachInbox`. On the Pixel, export a FIT file from the Suunto app, tap Share, then Quick Share, then your PC.

**USB cable:** Plug the Pixel in, choose "File transfer" on the phone's notification, and copy files from its Downloads folder.

**Google Drive for desktop:** Save exports to a Drive folder from the phone; Drive for desktop syncs it to your PC automatically.

Now export a handful of recent sessions and copy them into `C:\dev\runcoach\sample_data` for development: ideally three or four runs of different types (easy, hard, a 5k effort if you have one) and two gym sessions. Grab the JSON export for one run as well, so we can see what extra detail it contains. These files contain GPS tracks, so the project is set up to never commit that folder.

### Step 8: Gemini API key (needed from Phase 6)

Go to Google AI Studio (aistudio.google.com), sign in, and choose "Get API key". Treat the key like a password: never paste it into chat or code files. In Phase 6 you'll put it in a `.env` file that Git ignores.

One important gotcha: **don't enable billing on the Google project that holds this key.** On the Gemini API, turning on billing removes the free tier for that project entirely, and every request becomes chargeable.

### Step 9 (optional): Off-site backup with GitHub

Local Git protects you from bad code changes, but not from a dead hard drive. A free **private** GitHub repository gives you an off-site copy of your code (not your data; the database stays local). If you'd like this:

```powershell
winget install --id GitHub.cli -e
```

Reopen PowerShell, run `gh auth login`, and choose GitHub.com, HTTPS, and "Login with a web browser". Later, you can ask your AI tool to "create a private GitHub repo and push, checking no secrets or data are included first."

### Step 10: Check everything

```powershell
git --version
py -3.12 --version
uv --version
claude --version    # or: gemini --version
```

Four version numbers, plus the Tkinter test window from Step 3, means you're ready to build.

---
## 5. How to vibe code this safely

A few habits make the difference between a project that grows steadily and one that collapses into a tangle you can't fix.

**Work in small, testable steps.** Each phase below has a starter prompt and a clear "done when" check. If a phase feels big, ask for the first part, check it works, then continue.

**Ask for a plan before code.** For anything non-trivial, start with "Plan this first and explain it to me before writing code." In Claude Code, pressing Shift+Tab switches to Plan Mode, which does exactly that. Reading the plan is how you catch misunderstandings cheaply.

**Commit every time something works.** Just say "commit this with a clear message." If a later change goes wrong, you can say "undo everything since the last commit" and you're back to safety.

**Guard the core/UI split.** Every so often, ask: "Check that nothing in runcoach/core imports tkinter or matplotlib." AI tools take shortcuts under pressure, and this is the rule most likely to erode quietly.

**Test with your own data.** Your FIT files are the real test. If a chart looks wrong, say so specifically: "The pace on my 12 September run shows 9:40/km, but it was about 5:40/km."

**Ask it to explain.** You'll learn fast if you regularly ask, "Explain what you just changed in plain English."

**Paste errors whole.** If something breaks, copy the entire error message from the terminal into the chat rather than describing it.

**Start fresh sessions per phase.** Long AI sessions get muddled. Begin each phase with a new session; the `CLAUDE.md` brief means it won't lose the big picture. At the end of each phase, ask it to update the "Current status" line at the bottom of `CLAUDE.md`.

**Keep secrets secret.** The API key lives in `.env` only, which Git ignores. If you ever accidentally commit it, delete the key in AI Studio and create a new one.

---

## 6. The build, phase by phase

Each phase ends with something you can use or see. Most take one or two evenings. Copy the starter prompts into your AI tool as written, and adjust as you go.

### Phase 1: Project setup and reading your FIT files

**Goal:** A properly structured project, and proof that we can pull everything useful out of your Suunto files.

> Read CLAUDE.md. Set up this project with uv, configured to use the system Python 3.12 from python.org rather than a uv-managed Python, because we need its Tkinter. Create the package structure from CLAUDE.md with empty placeholder modules, and a .gitignore that excludes sample_data/, data/, .env and the virtual environment. Confirm Tkinter works inside the project environment. Then write runcoach/core/fit_import.py with a function that reads a FIT file and returns: sport type, start time, duration, distance, average pace, average and max heart rate, cadence, per-km splits, and a time series of distance, speed, heart rate, cadence and altitude. Discard all GPS. For non-running sessions, return duration and heart-rate data. Add a script, scripts/inspect_fit.py, that prints a summary for every file in sample_data/. Show me the results, then tell me what other useful data is in these files that we aren't using yet, and what the JSON export contains that the FIT file doesn't. Plan first.

**Done when:** The numbers the script prints match what the Suunto app shows for the same sessions, give or take rounding. Commit.

### Phase 2: The database and importer

**Goal:** Your whole training history stored safely in SQLite, with no user interface yet. Building this bit first, separately, keeps it clean and testable.

> Build runcoach/core/db.py using Python's built-in sqlite3 module. All SQL must live in this module; nothing else talks to the database directly. Store the database at data/runcoach.db. Create tables for sessions, splits, time-series samples (downsampled to one row every 5 seconds), notes, niggles, settings and AI reviews, plus a schema_version table and a simple migration mechanism so we can add columns later without losing data. Then write runcoach/core/importer.py: given a folder or a list of files, import any new FIT files, skipping duplicates by file hash, and return a summary of what was imported, skipped or failed (with reasons). Back up the database file automatically before each import, keeping the last 10 backups in data/backups/. Add scripts/import_folder.py to run an import from the command line, and pytest tests using a temporary database. Plan first.

Then import your sample files, and if you like, your full history.

**Done when:** The import script reports sensible results, running it twice imports nothing new the second time, and the tests pass. Commit.

### Phase 3: The desktop app shell

**Goal:** A real window you can click around: import files, browse sessions, and open a session with charts.

> Build the Tkinter app in runcoach/ui_tk/, launched with `uv run python -m runcoach`. First, recommend a modern theme for ttk (compare sv-ttk and ttkbootstrap, checking which is actively maintained) and wait for my choice. Then build a main window with a sidebar for Dashboard, Sessions, Import, Niggles and Settings (placeholders where needed). Make the app DPI-aware so text isn't blurry on Windows. The Import page should have a "Choose files…" button and an "Import from inbox" button that scans the inbox folder set in Settings; run imports in a background thread with a progress bar, so the window never freezes, and show the summary when done. The Sessions page should show a sortable table (ttk.Treeview) of date, type, duration, distance, pace and average HR, newest first. Double-clicking a session opens a detail view with a stats header, a splits table, and pace and heart-rate charts built by functions in runcoach/charts/ that return matplotlib Figure objects, embedded with FigureCanvasTkAgg and the matplotlib toolbar. Let me correct a session's type from a dropdown. Plan first.

**Done when:** You can import from your inbox folder, browse every session, and the charts look right. Commit.

### Phase 4: Your notes and how sessions felt

**Goal:** Capture the context that numbers miss. This is what will make the coaching genuinely personal.

> After an import, open a "How did it go?" dialog for each new session (with a "skip" button), which I can also reopen from the session detail view. Fields: an effort rating from 1 to 10 (session RPE), an optional free-text note, and optional niggle entries with body location (ankle, knee, calf, shin, hip, back, other), side (left/right) and severity from 0 to 10. For strength sessions, add a focus tag (legs, upper body, full body, core). Then build the Niggles page: a matplotlib chart of severity over time for each location, plus a list of recent entries. Keep all storage logic in core and all widgets in ui_tk. Plan first.

**Done when:** You've added notes to your recent sessions, including the sore ankle, and can see them charted on the Niggles page. Commit.

### Phase 5: Training metrics and the dashboard

**Goal:** Turn raw sessions into the numbers that actually tell you whether you're getting fitter.

> Add to the Settings page: max heart rate, resting heart rate, 5k goal (default: sub-25) and the inbox folder. Read max HR from the FIT files if it's stored there. Then build runcoach/core/metrics.py, using numpy, with pytest tests. For every session calculate: time in 5 heart-rate zones; a training load score from heart rate (Banister TRIMP); and session-RPE load (RPE × minutes) where I've given an RPE. From those, calculate daily fitness, fatigue and form using 42-day and 7-day exponentially weighted averages. For runs, also track pace at a fixed easy heart rate over time (aerobic efficiency) and estimate my current 5k time from recent best efforts. Build the Dashboard page with: estimated 5k versus goal, a fitness/fatigue/form chart, weekly running distance and total load (runs and gym stacked), and the aerobic efficiency trend. Add a one-line plain-English explanation under each chart. Plan first.

**Done when:** The dashboard makes sense against how you've actually been feeling, and the 5k estimate is in a believable range. Commit.

A note on the metrics: they're estimates, not truths. Heart rate tends to underestimate how demanding strength work is, which is why the session-RPE load matters for your gym sessions.

### Phase 6: The AI coach

**Goal:** A review of each session and advice for the next one, based on your numbers, your notes and your goal.

First, create a file called `.env` in the project folder containing your key (the AI can create the file; paste the key in yourself):

```
GEMINI_API_KEY=paste-your-key-here
```

> Build the AI coach in runcoach/core/coach/ with a simple provider interface, so we can swap between Gemini and Claude later. Implement the Gemini provider using the official google-genai library, loading the key from .env with python-dotenv and the model name from settings (use a current free-tier Flash model). Write a context builder that produces a compact text summary: my goal and settings; the last 4 weeks in weekly totals; every session from the last 10 days with key stats, RPE, notes and niggles; current fitness, fatigue and form; and the latest 5k estimate. Never include GPS, names or raw files. Write a coach system prompt in its own editable file with these rules: be concise and specific; review the latest session, then recommend the next session with type, duration and target pace or heart-rate zone; consider gym work, especially leg sessions within 48 hours of hard runs; be conservative about injuries — if a niggle is 4/10 or worse or trending upward, recommend easy running, cross-training or rest rather than hard efforts, and suggest seeing a physio if it persists beyond a week or two; never suggest pushing through pain. Request coaching automatically after I save the "How did it go?" dialog, in a background thread, and show it in the session detail view and as a "Latest advice" panel on the Dashboard. Save every response in the database, add a "Regenerate" button, and handle no-internet and rate-limit errors with friendly messages. Plan first.

**Done when:** You get sensible, specific advice after each session that clearly reflects your notes. Read the coach's prompt file and tweak its tone to suit you. Commit.

It's worth trying the same session with Claude later to compare advice quality; the provider switch makes that easy.

### Phase 7: Polish and a proper app

**Goal:** Something that feels like a finished app rather than a script you run from a terminal.

> Package RunCoach as a Windows app with PyInstaller so I can launch it from a desktop shortcut without a terminal. Keep the database and .env in a sensible user data location (such as %APPDATA%\RunCoach) when running as the packaged app, while development still uses the project's data folder. Add an app icon, a "Back up now" button in Settings, and an "Export all data to CSV" option. Plan first.

**Done when:** You double-click a desktop icon, RunCoach opens, and your data is all there. Commit.

### Nice-to-haves, in any order

A weekly summary page, with an AI review of the previous week. Parsing the Suunto JSON exports, if Phase 1 shows they contain useful extras. A "race day" page with a pacing plan for your next 5k or parkrun. Personal bests and milestones, with a small celebration when you hit a new one. Adding Claude as a second AI provider and comparing the advice.

**Per-lap distance calibration for treadmill/machine sessions.** The watch's own speed and per-record distance stream on a treadmill come from an uncalibrated accelerometer estimate, and can be well off (+15% to +27% seen in real files) - separately from `total_distance`, which gets manually corrected to match the console after the session (Phase 5 already fixed session-level pace to use `total_distance`/duration instead of the device's `avg_speed` because of this). Splits and the pace-over-time chart still use the uncorrected per-lap/per-record data. Once there are a few sessions with a lap pressed manually at each true 1km mark on the machine (FIT's `lap_trigger` field distinguishes `'manual'` presses from the watch's own `'distance'`-triggered auto-laps), each lap's samples could be rescaled using the true 1km distance vs. the watch's own recorded lap distance, fixing per-km splits and the pace chart too. Not worth building until there's real km-lapped data to validate it against.

---

## 7. The porting roadmap (for later)

You don't need any of this yet, but it explains why the structure matters.

When the desktop prototype has proven what's useful, the `core` package moves across to any new platform largely unchanged. The Tkinter interface does not; it gets rebuilt in whatever the new platform uses. That's why the plan keeps the UI thin and pushes every bit of logic down into core.

**Web or cloud (the earlier Streamlit plan).** This is probably the quickest route to using RunCoach on your phone. Streamlit is Python, it can reuse core and the matplotlib charts almost as-is, and switching SQLite for a hosted database means changing only `db.py`. The earlier version of this plan covers the hosting details.

**Android with Kivy.** Kivy is a Python framework that runs on Android and iOS, so core carries over. The interface needs rewriting in Kivy's own widgets. Packaging for Android is done with a tool called Buildozer, which runs on Linux; on Windows that means using WSL (a built-in Linux environment). numpy is supported on Android, but matplotlib there is awkward, so the charts may need redoing with a Kivy-native plotting approach. Budget real time for the packaging step; it's the fiddliest part.

**iOS.** Kivy apps can be built for iPhone, but that requires a Mac with Xcode, and keeping an app on your own phone long-term generally means a paid Apple developer account. If iOS matters, the web route above avoids all of that.

BeeWare is another Python-to-mobile option worth a look when the time comes; it produces apps with native-looking controls.

---

## 8. Troubleshooting quick reference

**"command not found" or "not recognised" after installing something:** Close PowerShell and open a new window. If it persists, restart the PC.

**PowerShell says running scripts is disabled:** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer Y, and try again.

**Error mentioning "Can't find a usable init.tcl":** The project is using a Python without working Tcl/Tk. Ask your AI tool to make the project use the python.org Python 3.12 instead, then rebuild the environment.

**The window freezes ("Not Responding") during an import or coaching request:** Some slow work is running on the main thread. Tell the AI: "The window freezes during X; move that work to a background thread and update the UI safely with after()."

**Blurry text:** The app isn't DPI-aware. Ask the AI to enable per-monitor DPI awareness at startup.

**Charts open in separate windows, or memory grows over time:** Tell the AI to build figures with `matplotlib.figure.Figure` rather than `pyplot`, and to clean up old chart canvases when switching views.

**The AI coach says it's rate-limited:** You've hit the free Gemini limit for the moment. Wait a minute (or until tomorrow if it's the daily limit). For one person this should be rare.

**The AI made a mess of the code:** Say "undo everything since the last commit" and try again with a smaller, more specific request.

**Numbers look wrong:** Compare against the Suunto app for the same session and tell the AI exactly which value is off and by how much.

---

## 9. Open questions for later

These aren't needed to start, but the app will ask for some in Phase 5, so it's worth digging them out: your max heart rate and resting heart rate (check the Suunto app or your watch's heart-rate zone settings); how many runs and gym sessions you typically do each week; and whether you have a recent timed 5k, parkrun or otherwise, to calibrate the estimate.

A final word on the ankle: RunCoach will track it and the coach will be cautious around it, but an app can't examine anything. If it's been sore for more than a week or two, is getting worse, or changes how you run, it's worth getting a physio to take a look.
