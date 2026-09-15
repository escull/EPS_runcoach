import sqlite3
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from eps_runcoach.charts.session_charts import heart_rate_chart, pace_chart
from eps_runcoach.core import db, metrics
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.fit_import import SAMPLE_INTERVAL_S
from eps_runcoach.core.formatting import (
    format_date,
    format_distance,
    format_duration,
    format_hr,
    format_pace,
    format_recovery_time,
    format_training_effect,
    format_vo2_max,
)
from eps_runcoach.ui_tk.pages.correct_split_distance import CorrectSplitDistanceDialog
from eps_runcoach.ui_tk.pages.how_did_it_go import HowDidItGoDialog

SESSION_TYPES = ["run", "strength", "other"]


class SessionDetailWindow(tb.Toplevel):
    def __init__(self, app, session_id: int):
        super().__init__(title="Session detail", size=(900, 700))
        self.app = app
        self.session_id = session_id

        # Everything below (header, splits, two charts) is taller than fits
        # on a typical laptop screen, so it all lives inside a scrollable
        # canvas rather than forcing a very tall fixed window.
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        body = tb.Frame(canvas)
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_window, width=e.width))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        session = db.get_session(app.conn, session_id)

        self._build_header(body, session)
        self._build_how_did_it_go_section(body)
        self._build_advice_section(body)

        self.data_frame = tb.Frame(body)
        self.data_frame.pack(fill="both", expand=True)
        self._render_data_section()

    def _build_header(self, parent: tb.Frame, session: sqlite3.Row) -> None:
        header = tb.Frame(parent)
        header.pack(fill="x", padx=16, pady=16)

        sport_text = f"{session['sport']} ({session['sub_sport']})" if session["sub_sport"] else session["sport"]
        tb.Label(header, text=sport_text, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        tb.Label(header, text=format_date(session["start_time"])).grid(row=0, column=1, sticky="w", padx=16)

        stats = (
            f"Duration: {format_duration(session['duration_s'])}   "
            f"Distance: {format_distance(session['distance_km'])}   "
            f"Pace: {format_pace(session['avg_pace_min_per_km'])}   "
            f"Avg HR: {format_hr(session['avg_heart_rate'])}   "
            f"Max HR: {format_hr(session['max_heart_rate'])}"
        )
        tb.Label(header, text=stats).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        next_row = 2
        has_hrm_stats = any(
            session[key] is not None
            for key in ("estimated_vo2_max", "recovery_time_s", "total_training_effect")
        )
        if has_hrm_stats:
            hrm_stats = (
                f"Est. VO2 max: {format_vo2_max(session['estimated_vo2_max'])}   "
                f"Recovery: {format_recovery_time(session['recovery_time_s'])}   "
                f"Training effect: {format_training_effect(session['total_training_effect'])}"
            )
            tb.Label(header, text=hrm_stats, bootstyle="secondary").grid(
                row=next_row, column=0, columnspan=2, sticky="w", pady=(4, 0)
            )
            next_row += 1

        type_row = tb.Frame(header)
        type_row.grid(row=next_row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        tb.Label(type_row, text="Session type:").pack(side="left")
        self.type_var = tk.StringVar(value=session["session_type"])
        combo = tb.Combobox(type_row, textvariable=self.type_var, values=SESSION_TYPES, state="readonly", width=12)
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", self._on_type_changed)

    def _on_type_changed(self, _event) -> None:
        db.update_session_type(self.app.conn, self.session_id, self.type_var.get())
        sessions_page = self.app.pages.get("Sessions")
        if sessions_page is not None:
            sessions_page.refresh()

    def _build_how_did_it_go_section(self, parent: tb.Frame) -> None:
        self.how_did_it_go_frame = tb.Frame(parent)
        self.how_did_it_go_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._render_how_did_it_go()

    def _render_how_did_it_go(self) -> None:
        for widget in self.how_did_it_go_frame.winfo_children():
            widget.destroy()

        note = db.get_note(self.app.conn, self.session_id)
        niggles = db.get_niggles_for_session(self.app.conn, self.session_id)

        tb.Label(self.how_did_it_go_frame, text="How did it go?", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        parts = []
        if note and note["rpe"] is not None:
            parts.append(f"RPE {note['rpe']}/10")
        if note and note["focus_tag"]:
            parts.append(f"Focus: {note['focus_tag']}")
        if note and note["note_text"]:
            parts.append(f'"{note["note_text"]}"')
        if niggles:
            niggle_descriptions = []
            for niggle in niggles:
                side = niggle["side"]
                side_text = f" ({side})" if side else ""
                niggle_descriptions.append(f"{niggle['location']}{side_text} {niggle['severity']}/10")
            parts.append(f"Niggles: {', '.join(niggle_descriptions)}")
        summary_text = "   ".join(parts) if parts else "Not logged yet."

        tb.Label(self.how_did_it_go_frame, text=summary_text, wraplength=700, justify="left").grid(
            row=1, column=0, sticky="w", pady=(4, 4)
        )

        button_text = "Edit" if (note is not None or niggles) else "How did it go?"
        tb.Button(
            self.how_did_it_go_frame, text=button_text, command=self._open_how_did_it_go, bootstyle="secondary"
        ).grid(row=2, column=0, sticky="w")

    def _open_how_did_it_go(self) -> None:
        HowDidItGoDialog(self.app, self.session_id, on_done=self._render_how_did_it_go)

    def _build_advice_section(self, parent: tb.Frame) -> None:
        self.advice_frame = tb.Frame(parent)
        self.advice_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._render_advice()

    def _render_advice(self) -> None:
        if not self.winfo_exists():
            return
        for widget in self.advice_frame.winfo_children():
            widget.destroy()

        review = db.get_latest_ai_review_for_session(self.app.conn, self.session_id)

        tb.Label(self.advice_frame, text="Coach's advice", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        if review is None:
            tb.Label(self.advice_frame, text="No advice yet.").pack(anchor="w", pady=(4, 4))
        else:
            tb.Label(self.advice_frame, text=format_date(review["created_at"]), bootstyle="secondary").pack(
                anchor="w"
            )
            tb.Label(self.advice_frame, text=review["review_text"], wraplength=800, justify="left").pack(
                anchor="w", pady=(4, 4)
            )

        self.regenerate_button = tb.Button(
            self.advice_frame, text="Regenerate", command=self._request_advice, bootstyle="secondary"
        )
        self.regenerate_button.pack(anchor="w")

    def _request_advice(self) -> None:
        self.regenerate_button.configure(state="disabled", text="Generating...")
        self.app.request_coaching(self.session_id, on_done=self._render_advice)

    def _render_data_section(self) -> None:
        for widget in self.data_frame.winfo_children():
            widget.destroy()

        splits = db.get_splits(self.app.conn, self.session_id)
        samples = db.get_samples(self.app.conn, self.session_id)

        self._build_splits_table(self.data_frame, splits)
        self._build_zones_section(self.data_frame, samples)
        self._build_charts(self.data_frame, samples)

    def _build_splits_table(self, parent: tb.Frame, splits: list[sqlite3.Row]) -> None:
        columns = ("split", "distance", "duration", "pace", "avg_hr")
        headings = {"split": "Split", "distance": "Distance", "duration": "Duration", "pace": "Pace", "avg_hr": "Avg HR"}

        tree = ttk.Treeview(parent, columns=columns, show="headings", height=min(len(splits), 8) or 1)
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=100, anchor="center")

        for split in splits:
            tree.insert(
                "",
                "end",
                values=(
                    split["split_index"],
                    format_distance(split["distance_km"]),
                    format_duration(split["duration_s"]),
                    format_pace(split["avg_pace_min_per_km"]),
                    format_hr(split["avg_heart_rate"]),
                ),
            )
        tree.pack(fill="x", padx=16, pady=(0, 8))

        if splits:
            tb.Button(
                parent,
                text="Correct a split's distance...",
                command=lambda: self._open_correct_split_distance(splits),
                bootstyle="secondary",
            ).pack(anchor="w", padx=16, pady=(0, 16))

    def _open_correct_split_distance(self, splits: list[sqlite3.Row]) -> None:
        CorrectSplitDistanceDialog(self.app, self.session_id, splits, on_done=self._render_data_section)

    def _build_zones_section(self, parent: tb.Frame, samples: list[sqlite3.Row]) -> None:
        max_hr_raw = core_settings.get_setting(self.app.conn, core_settings.MAX_HEART_RATE_KEY)
        resting_hr_raw = core_settings.get_setting(self.app.conn, core_settings.RESTING_HEART_RATE_KEY)
        if not max_hr_raw or not resting_hr_raw or not samples:
            return

        heart_rates = [sample["heart_rate"] for sample in samples]
        zone_seconds = metrics.time_in_zones(
            heart_rates, SAMPLE_INTERVAL_S, float(resting_hr_raw), float(max_hr_raw)
        )
        if sum(zone_seconds) == 0:
            return

        frame = tb.Frame(parent)
        frame.pack(fill="x", padx=16, pady=(0, 16))
        tb.Label(frame, text="Time in zones", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        zones_row = tb.Frame(frame)
        zones_row.pack(anchor="w", pady=(4, 0))
        for zone_index, seconds in enumerate(zone_seconds, start=1):
            tb.Label(zones_row, text=f"Z{zone_index}: {format_duration(seconds)}").pack(side="left", padx=(0, 16))

    def _build_charts(self, parent: tb.Frame, samples: list[sqlite3.Row]) -> None:
        charts_frame = tb.Frame(parent)
        charts_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        for chart_fn in (pace_chart, heart_rate_chart):
            figure = chart_fn(samples)
            canvas = FigureCanvasTkAgg(figure, master=charts_frame)
            canvas.draw()

            toolbar_frame = tb.Frame(charts_frame)
            toolbar_frame.pack(fill="x")
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()

            canvas.get_tk_widget().pack(fill="both", expand=True, pady=(0, 12))
