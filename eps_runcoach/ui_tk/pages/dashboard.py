"""Dashboard page: estimated 5k vs goal, fitness/fatigue/form, weekly
distance and load, aerobic efficiency, and the coach's latest advice -
recomputed from the database each time the page is shown.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from eps_runcoach.charts.dashboard_charts import (
    aerobic_efficiency_chart,
    fitness_fatigue_form_chart,
    weekly_distance_chart,
    weekly_load_chart,
)
from eps_runcoach.core import db, training_data
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.formatting import format_date, format_duration


class DashboardPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Scrollable, same pattern as the session detail view - the stat
        # line plus four charts is taller than comfortably fits a laptop
        # screen.
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

        tb.Label(body, text="Dashboard", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        self.content_frame = tb.Frame(body)
        self.content_frame.pack(fill="both", expand=True)

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        conn = self.app.conn
        max_hr_raw = core_settings.get_setting(conn, core_settings.MAX_HEART_RATE_KEY)
        resting_hr_raw = core_settings.get_setting(conn, core_settings.RESTING_HEART_RATE_KEY)

        if not max_hr_raw or not resting_hr_raw:
            tb.Label(
                self.content_frame,
                text="Set your max and resting heart rate on the Settings page to see training metrics.",
            ).pack(anchor="w", padx=16, pady=16)
            return

        sessions = db.get_all_sessions(conn)
        if not sessions:
            tb.Label(self.content_frame, text="Import some sessions to see your dashboard.").pack(
                anchor="w", padx=16, pady=16
            )
            return

        goal_raw = core_settings.get_setting(conn, core_settings.GOAL_5K_SECONDS_KEY)
        goal_seconds = float(goal_raw) if goal_raw else core_settings.DEFAULT_GOAL_5K_SECONDS

        snapshot = training_data.build_snapshot(conn, float(resting_hr_raw), float(max_hr_raw))

        self._render_5k_estimate(snapshot.estimate_5k_seconds, goal_seconds)
        self._render_latest_advice()
        self._render_fitness_fatigue_form(snapshot.dates, snapshot.fitness, snapshot.fatigue, snapshot.form)
        self._render_weekly_distance(snapshot.weekly_distance)
        self._render_weekly_load(snapshot.weekly_run_load, snapshot.weekly_other_load)
        self._render_aerobic_efficiency(snapshot.aerobic_points)

    def _render_5k_estimate(self, estimate_seconds: float | None, goal_seconds: float) -> None:
        frame = tb.Frame(self.content_frame)
        frame.pack(fill="x", padx=16, pady=(0, 16))

        if estimate_seconds is None:
            text = f"Estimated 5k: not enough recent data.   Goal: {format_duration(goal_seconds)}"
        else:
            comparison = "under goal" if estimate_seconds < goal_seconds else "over goal"
            text = (
                f"Estimated 5k: {format_duration(estimate_seconds)}   "
                f"Goal: {format_duration(goal_seconds)}   ({comparison})"
            )
        tb.Label(frame, text=text, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tb.Label(
            frame,
            text="Estimated from your fastest recent run (last 28 days), scaled to 5k using Riegel's formula.",
            bootstyle="secondary",
        ).pack(anchor="w")

    def _render_latest_advice(self) -> None:
        review = db.get_latest_ai_review(self.app.conn)

        frame = tb.Frame(self.content_frame)
        frame.pack(fill="x", padx=16, pady=(0, 16))
        tb.Label(frame, text="Latest advice", font=("Segoe UI", 13, "bold")).pack(anchor="w")

        if review is None:
            tb.Label(frame, text="No coaching advice yet - save a \"How did it go?\" entry to request some.").pack(
                anchor="w"
            )
            return

        tb.Label(frame, text=format_date(review["created_at"]), bootstyle="secondary").pack(anchor="w")
        tb.Label(frame, text=review["review_text"], wraplength=800, justify="left").pack(anchor="w", pady=(4, 0))

    def _add_chart(self, figure, caption: str) -> None:
        block = tb.Frame(self.content_frame)
        block.pack(fill="both", padx=16, pady=(0, 16))

        canvas = FigureCanvasTkAgg(figure, master=block)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        tb.Label(block, text=caption, bootstyle="secondary", wraplength=800, justify="left").pack(
            anchor="w", pady=(4, 0)
        )

    def _render_fitness_fatigue_form(self, dates: list[date], fitness, fatigue, form) -> None:
        figure = fitness_fatigue_form_chart(dates, fitness, fatigue, form)
        self._add_chart(
            figure,
            "Fitness builds slowly with consistent training; fatigue rises and falls faster; "
            "form is high when you're fresh and low when you're carrying fatigue.",
        )

    def _render_weekly_distance(self, weekly_distance: dict[date, float]) -> None:
        weeks = sorted(weekly_distance)
        distances = [weekly_distance[w] for w in weeks]
        figure = weekly_distance_chart(weeks, distances)
        self._add_chart(figure, "Total kilometres run each week.")

    def _render_weekly_load(self, weekly_run_load: dict[date, float], weekly_other_load: dict[date, float]) -> None:
        weeks = sorted(set(weekly_run_load) | set(weekly_other_load))
        run_loads = [weekly_run_load.get(w, 0.0) for w in weeks]
        other_loads = [weekly_other_load.get(w, 0.0) for w in weeks]
        figure = weekly_load_chart(weeks, run_loads, other_loads)
        self._add_chart(figure, "Combined training stress from running and strength/other sessions each week.")

    def _render_aerobic_efficiency(self, points: list[tuple[date, float]]) -> None:
        dates = [point[0] for point in points]
        paces = [point[1] for point in points]
        figure = aerobic_efficiency_chart(dates, paces)
        self._add_chart(
            figure,
            "Pace at a fixed easy heart rate over time - a faster pace at the same "
            "effort means better aerobic fitness.",
        )
