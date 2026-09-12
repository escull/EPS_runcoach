# RunCoach: Cloud Plan (PARKED — reference for a future web port)

*A personal, AI-assisted training app for a sub-25 minute 5k, built by vibe coding on Windows.*

---

## 1. What we're building

RunCoach is a private web app that you open in a browser on your Windows PC or your Pixel 8, from anywhere. After a session, you export the FIT file from the Suunto app, upload it to RunCoach from your phone, add a quick note about how it felt, and get two things back: a short review of the session and advice for your next one.

Behind the scenes, the app reads every run and gym session your Suunto 9 Baro records, works out how hard each one was, tracks your fitness and fatigue over time, and watches your progress towards the goal. The AI coach only interprets those numbers; the app does the maths itself, which makes the advice more reliable and keeps the free AI allowance going a long way.

### Your profile, as captured in the interview

| Item | Answer |
|---|---|
| Current 5k | 25–30 minutes |
| Goal | Sub-25 (5:00 per km or faster), no deadline |
| Other training | Strength / gym, recorded on the Suunto (duration and heart rate only) |
| Devices | Windows PC and Pixel 8, equally |
| Access | From anywhere |
| Coding experience | A bit of scripting and tinkering |
| AI | Start with Gemini's free tier; Claude available as an alternative |
| AI jobs | Review each session and advise on the next, taking your notes into account |
| Current niggles | Sore ankle; a stitch during a run (note unfinished — see open questions) |

---

## 2. Key decisions and why

**A web app, not a native Android app.** One codebase works on your PC and your phone. Native Android development would mean Android Studio, Kotlin and a much steeper learning curve for no real gain here.

**Python with Streamlit.** Python is the easiest language to vibe code in and has mature libraries for reading FIT files and crunching data. Streamlit turns Python scripts into web pages with charts, upload buttons and forms, without you having to write HTML or JavaScript. It works acceptably in a phone browser, and you can add it to your Pixel's home screen so it opens like an app.

**Streamlit Community Cloud for hosting (free).** It deploys straight from a GitHub repository. Free accounts get one private app, which is exactly what you need, since only you should see your health data. The trade-offs: about 1 GB of memory (plenty for one person), and the app goes to sleep after 12 hours without visitors. Waking it takes one tap and a short wait, which is fine for an after-run check-in.

**Neon for the database (free).** Community Cloud doesn't keep files between restarts, so your training history must live in a proper database. Neon's free Postgres tier gives 0.5 GB of storage, which is years of training for one person if we store sensibly. Unlike Supabase's free tier, it doesn't pause your project after a week of inactivity, so a holiday won't break the app. While developing on your PC, the app uses a simple local database file (SQLite) instead, and switching between the two is a one-line setting.

**Gemini's free tier for the AI coach, swappable later.** A free API key from Google AI Studio needs no credit card. The free tier is limited to Gemini's Flash models, which are more than capable of this job. Google may use free-tier inputs and outputs to improve its models, so RunCoach will only ever send summarised numbers and your notes, never raw files, GPS data or your name. The AI code will sit behind a simple "provider" switch so moving to Claude, or a paid Gemini tier, is a small change.

**No GPS stored at all.** For a 5k-focused coach, routes add little, and a track that starts and ends at your front door reveals where you live. RunCoach will discard GPS coordinates on import. Distance, pace, heart rate, cadence and altitude are all still available without them.

**Claude Code as your vibe-coding tool.** You describe what you want in plain English; it writes the code, runs it, and fixes errors. It runs natively on Windows and needs a paid Claude plan (Pro or above). If you only have the free Claude plan, Google's Gemini CLI is a free alternative that works in a similar way; the prompts in this plan work with either.

### Running costs

Everything above is free: GitHub, Streamlit Community Cloud, Neon, and the Gemini API free tier. The only possible cost is the Claude subscription for Claude Code, if you use that rather than Gemini CLI. Free tiers do change, so treat this as correct as of September 2026.

---

## 3. How it fits together

```
 Suunto 9 Baro ──sync──> Suunto app (Pixel)
                              │  export .fit
                              ▼
     Phone or PC browser ──upload + notes──> RunCoach (Streamlit, private app)
                                                 │                │
                              stores parsed data │                │ sends summary only
                                                 ▼                ▼
                                          Neon Postgres      Gemini API
                                     (sessions, splits,    (session review +
                                      notes, AI replies)    next-session advice)
```

While you build on your PC, the same app runs locally with a SQLite file instead of Neon, and you view it at `http://localhost:8501`.

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

Reopen PowerShell, then tell Git who you are (use the email you'll use for GitHub):

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

### Step 2: VS Code (code editor)

You won't write much code by hand, but you'll want to see the files, review what the AI changed, and edit your notes files.

```powershell
winget install --id Microsoft.VisualStudioCode -e
```

Open VS Code, go to the Extensions panel (the four-squares icon on the left) and install the **Python** extension by Microsoft. If you're using Claude Code, also install the **Claude Code** extension, which lets you see its changes side by side in the editor.

### Step 3: uv (Python and package manager)

Rather than installing Python the traditional way, we'll use `uv`. It installs the right Python version for you, keeps each project's libraries separate, and avoids most of the PATH and "virtual environment" confusion that trips people up on Windows.

```powershell
winget install --id astral-sh.uv -e
```

Reopen PowerShell, then:

```powershell
uv --version
uv python install 3.12
```

We use Python 3.12 because it is well supported by every library this project needs and by Streamlit Community Cloud.

### Step 4: GitHub account and GitHub CLI

Your code will live in a **private** GitHub repository. Streamlit Community Cloud deploys from there, and it doubles as an off-site backup.

Create a free account at github.com if you don't have one, then install the GitHub command-line tool and log in:

```powershell
winget install --id GitHub.cli -e
```

Reopen PowerShell, then:

```powershell
gh auth login
```

Choose GitHub.com, HTTPS, and "Login with a web browser", then follow the prompts.

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

Now copy the `CLAUDE.md` file that came with this plan into `C:\dev\runcoach`. It's a project brief that your AI tool reads at the start of every session, so it always knows the goal, the tech choices and the rules. (If you use Gemini CLI, make a copy of it named `GEMINI.md`.)

Open the folder in VS Code with:

```powershell
code .
```

### Step 7: Get some FIT files onto your PC

In the Suunto app on your Pixel, export the FIT files for a handful of recent sessions: ideally three or four runs of different types (easy, hard, a 5k effort if you have one) and two gym sessions. Grab the JSON export for one run as well, so we can see what extra detail it contains.

The easiest way to move them is to save them to Google Drive from the phone's share menu, then download them on your PC into `C:\dev\runcoach\sample_data`. These files contain GPS tracks, so the project is set up to never upload that folder to GitHub.

### Step 8: Gemini API key (needed from Phase 5)

Go to Google AI Studio (aistudio.google.com), sign in, and choose "Get API key". Treat the key like a password: never paste it into chat, code files or GitHub. In Phase 5 you'll put it in a secrets file that stays on your PC.

One important gotcha: **don't enable billing on the Google project that holds this key.** On the Gemini API, turning on billing removes the free tier for that project entirely, and every request becomes chargeable.

### Step 9: Check everything

```powershell
git --version
uv --version
gh --version
claude --version    # or: gemini --version
```

Four version numbers means you're ready to start building.

---
## 5. How to vibe code this safely

A few habits make the difference between a project that grows steadily and one that collapses into a tangle you can't fix.

**Work in small, testable steps.** Each phase below is split into a starter prompt and a clear "done when" check. Don't ask for a whole phase in one go if it feels big; ask for the first part, check it works, then continue.

**Ask for a plan before code.** For anything non-trivial, start with "Plan this first and explain it to me before writing code." In Claude Code, pressing Shift+Tab switches to Plan Mode, which does exactly that. Reading the plan is how you catch misunderstandings cheaply.

**Commit every time something works.** Just say "commit this with a clear message." If a later change goes wrong, you can say "undo everything since the last commit" and you're back to safety.

**Test with your own data.** Your FIT files are the real test. If a chart looks wrong, say so specifically: "The pace on my 12 September run shows 9:40/km, but it was about 5:40/km."

**Ask it to explain.** You'll learn fast if you regularly ask, "Explain what you just changed in plain English." The project brief already asks it to do this, but a nudge helps.

**Paste errors whole.** If something breaks, copy the entire red error message into the chat rather than describing it.

**Start fresh sessions per phase.** Long AI sessions get muddled. Begin each phase with a new session; the `CLAUDE.md` brief means it won't lose the big picture. At the end of each phase, ask it to update the "Current status" line at the bottom of `CLAUDE.md`.

**Keep secrets secret.** API keys and database passwords go in `.streamlit/secrets.toml` only, which is excluded from Git. If you ever accidentally commit a key, delete it in AI Studio and create a new one.

---

## 6. The build, phase by phase

Each phase ends with something you can use or see. Most take one or two evenings. Copy the starter prompts into your AI tool as written, and adjust as you go.

### Phase 1: Read your FIT files

**Goal:** Prove we can pull everything useful out of your Suunto files before building anything visual.

> Read CLAUDE.md. Set up this project with uv and Python 3.12, and create a .gitignore that excludes sample_data/, .streamlit/secrets.toml, any .db files and the virtual environment. Then write a script, scripts/inspect_fit.py, that takes a FIT file and prints: sport type, start time, duration, distance, average pace, average and max heart rate, cadence, and per-km splits. For non-running sessions, print duration and heart rate stats. Don't keep any GPS data. Run it on every file in sample_data/ and show me the results. Then tell me what other useful data is in these files that we aren't using yet, and what the JSON export contains that the FIT file doesn't.

**Done when:** The numbers the script prints match what the Suunto app shows for the same sessions, give or take rounding. Commit.

### Phase 2: A local app with your training history

**Goal:** A working Streamlit app on your PC where you can upload files and browse your sessions.

> Build the first version of the Streamlit app, following the structure in CLAUDE.md. I want: an upload page that accepts one or many FIT files at once, parses them with the Phase 1 code, skips duplicates, and saves them to a local SQLite database via SQLAlchemy (so we can switch to Postgres later just by changing DATABASE_URL); a sessions list, newest first, showing date, type, duration, distance, pace and average HR; and a session detail page with pace and heart-rate charts and a splits table. Classify sessions as run, strength or other, and let me correct the type if it's wrong. Make the layout work on a phone screen. Plan it first.

Run it with `uv run streamlit run app.py` and open `http://localhost:8501`. Upload all your sample files, then as much of your history as you like.

**Done when:** You can upload, browse and open every session, and the charts look right. Commit.

### Phase 3: Your notes and how sessions felt

**Goal:** Capture the context that numbers miss. This is what will make the coaching genuinely personal.

> Add a quick "how did it go?" form to each session, designed for thumbs on a phone: an effort rating from 1 to 10 (session RPE), an optional free-text note, and an optional pain/niggle entry with a body location (dropdown: ankle, knee, calf, shin, hip, back, other; plus left/right) and a severity from 0 to 10. For strength sessions, add a focus tag (legs, upper body, full body, core) and let me say whether it was easy, moderate or hard. After uploading, take me straight to this form. Add a "niggles" view showing how each pain location has trended over the last few weeks.

**Done when:** You've added notes to your recent sessions, including the sore ankle, and can see them on the niggles view. Commit.

### Phase 4: Training metrics and 5k progress

**Goal:** Turn raw sessions into the numbers that actually tell you whether you're getting fitter.

> Add a settings page for my max heart rate, resting heart rate and 5k goal (default: sub-25). Read max HR from the FIT files if it's stored there. Then add a metrics module (with pytest tests) that calculates, for every session: time in 5 heart-rate zones; a training load score from heart rate (Banister TRIMP); and session-RPE load (RPE × minutes) where I've given an RPE. From those, calculate daily fitness, fatigue and form using 42-day and 7-day exponentially weighted averages. For runs, also track pace at a fixed easy heart rate over time (aerobic efficiency) and estimate my current 5k time from recent best efforts. Build a dashboard page showing: estimated 5k vs goal, a fitness/fatigue/form chart, weekly running distance and total load (runs and gym stacked), and the aerobic efficiency trend. Explain each metric in one plain-English line on the page. Plan first.

**Done when:** The dashboard makes sense against how you've actually been feeling, and the 5k estimate is in a believable range. Commit.

A note on the metrics: they're estimates, not truths. Heart rate tends to underestimate how demanding strength work is, which is why the session-RPE load matters for your gym sessions.

### Phase 5: The AI coach

**Goal:** A review of each session and advice for the next one, based on your numbers, your notes and your goal.

First, create `.streamlit/secrets.toml` in the project folder and add your key (the AI can create the file; you paste the key in yourself):

```toml
GEMINI_API_KEY = "paste-your-key-here"
```

> Build the AI coach as a module with a simple provider interface, so we can swap between Gemini and Claude later. Implement the Gemini provider using the official google-genai library, reading the key from Streamlit secrets and the model name from config (use a current free-tier Flash model). Write a context builder that produces a compact text summary: my goal and settings; the last 4 weeks in weekly totals; every session from the last 10 days with key stats, RPE, notes and niggles; current fitness, fatigue and form; and the latest 5k estimate. Never include GPS, names or raw files. Write a coach system prompt (store it in its own file so I can edit it) with these rules: be concise and specific; review the latest session, then recommend the next session with type, duration and target pace or HR zone; consider gym work, especially leg sessions within 48 hours of hard runs; be conservative about injuries — if a niggle is 4/10 or worse or trending upward, recommend easy running, cross-training or rest rather than hard efforts, and suggest seeing a physio if it persists beyond a week or two; never suggest pushing through pain. Show the advice on the session page after I submit my notes, save it to the database, and add a "regenerate" button. Handle rate-limit errors gracefully with a friendly message. Plan first.

**Done when:** You get sensible, specific advice after each session that clearly reflects your notes. Read the coach's prompt file and tweak its tone to suit you. Commit.

It's worth trying the same session with Claude later to compare advice quality; the provider switch makes that easy.

### Phase 6: Go live on the internet

**Goal:** RunCoach available privately on your phone, anywhere.

1. **Create a Neon database.** Sign up at neon.com (free), create a project in a European region (London or Frankfurt, close to you), and copy its connection string.
2. **Switch and migrate.** Prompt:
   > Add the Neon connection string to .streamlit/secrets.toml as DATABASE_URL and make the app use it when present, falling back to local SQLite otherwise. Write a one-off script to copy all my existing data from the SQLite file into Neon, and verify the counts match.
3. **Push to GitHub.** Prompt: "Create a private GitHub repo called runcoach using gh and push this project. Double-check that no secrets or sample data are included before pushing."
4. **Deploy.** Sign in to share.streamlit.io with GitHub, choose "Create app", pick your runcoach repo, set the main file to `app.py`, and under Advanced settings choose Python 3.12 and paste the contents of your `secrets.toml` into the Secrets box. Deploy.
5. **Make it private.** In the app's settings, set it so only you can view it. Then open the link on your phone while logged out of Streamlit to confirm you're blocked.
6. **Add to your home screen.** Open the app in Chrome on your Pixel, tap the three-dot menu, and choose "Add to Home screen".

**Done when:** You can upload a FIT file from your phone after a run and get coaching back, away from home. Commit any final tweaks, which redeploy automatically.

### Phase 7: Nice-to-haves, in any order

Once the core is working, these are good next steps. Pick whichever appeals.

A weekly summary page, with a Monday-morning AI review of the previous week. Parsing the Suunto JSON exports, if Phase 1 shows they contain useful extras (Suunto's own recovery or feeling data, for example). A "race day" page with a pacing plan for your next 5k attempt. Personal bests and milestones, with a small celebration when you hit a new one. A simple "ask the coach" box for one-off questions about your training. Exporting all your data as a backup file. Adding Claude as a second AI provider and comparing the advice.

---

## 7. Troubleshooting quick reference

**"command not found" or "not recognised" after installing something:** Close PowerShell and open a new window. If it persists, restart the PC.

**PowerShell says running scripts is disabled:** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer Y, and try again.

**The app on Streamlit Cloud shows a sleeping page:** Tap the button to wake it. That's normal after 12 hours without visits.

**The AI coach says it's rate-limited:** You've hit the free Gemini limit for the moment. Wait a minute (or until tomorrow if it's the daily limit). For one person this should be rare.

**The AI made a mess of the code:** Say "undo everything since the last commit" and try again with a smaller, more specific request.

**Numbers look wrong:** Compare against the Suunto app for the same session and tell the AI exactly which value is off and by how much.

---

## 8. Open questions for later

These aren't needed to start, but the app will ask for some of them in Phase 4, so it's worth digging them out: your max heart rate and resting heart rate (check the Suunto app's settings, or your watch's HR zone settings); how many runs and gym sessions you typically do each week; and whether you have a recent timed 5k, parkrun or otherwise, to calibrate the estimate.

A final word on the ankle: RunCoach will track it and the coach will be cautious around it, but an app can't examine anything. If it's been sore for more than a week or two, is getting worse, or changes how you run, it's worth getting a physio to take a look.
