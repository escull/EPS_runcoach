"""Dashboard page: estimated 5k vs goal, fitness/fatigue/form, weekly
distance and load, and aerobic efficiency - recomputed from the database
each time the page is shown.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from eps_runcoach.charts.dashboard_charts import (
    aerobic_efficiency_chart,
    fitness_fatigue_form_chart,
    weekly_distance_chart,
    weekly_load_chart,
)
from eps_runcoach.core import db, metrics
from eps_runcoach.core import settings as core_settings
from eps_runcoach.ui_tk.formatting import format_duration


def _parse_date(start_time: str) -> date:
    return datetime.fromisoformat(start_time).date()


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

        max_hr = float(max_hr_raw)
        resting_hr = float(resting_hr_raw)
        goal_raw = core_settings.get_setting(conn, core_settings.GOAL_5K_SECONDS_KEY)
        goal_seconds = float(goal_raw) if goal_raw else core_settings.DEFAULT_GOAL_5K_SECONDS

        session_loads: list[tuple[date, float]] = []
        run_sessions_for_estimate: list[tuple[date, float, float]] = []
        weekly_distance: dict[date, float] = {}
        weekly_run_load: dict[date, float] = {}
        weekly_other_load: dict[date, float] = {}
        aerobic_points: list[tuple[date, float]] = []

        for session in sessions:
            session_date = _parse_date(session["start_time"])
            note = db.get_note(conn, session["id"])
            rpe = note["rpe"] if note else None

            trimp_value = metrics.trimp(session["avg_heart_rate"], session["duration_s"], resting_hr, max_hr)
            srpe_value = metrics.srpe_load(rpe, session["duration_s"])
            load = metrics.combined_session_load(trimp_value, srpe_value)
            if load is not None:
                session_loads.append((session_date, load))

            week_start = session_date - timedelta(days=session_date.weekday())
            if session["session_type"] == "run":
                weekly_distance[week_start] = weekly_distance.get(week_start, 0.0) + (session["distance_km"] or 0.0)
                if load is not None:
                    weekly_run_load[week_start] = weekly_run_load.get(week_start, 0.0) + load
            elif load is not None:
                weekly_other_load[week_start] = weekly_other_load.get(week_start, 0.0) + load

            if session["session_type"] == "run" and session["distance_km"] and session["duration_s"]:
                run_sessions_for_estimate.append((session_date, session["distance_km"], session["duration_s"]))

                samples = db.get_samples(conn, session["id"])
                heart_rates = [s["heart_rate"] for s in samples]
                speeds = [s["speed_m_s"] for s in samples]
                pace = metrics.aerobic_efficiency_pace(heart_rates, speeds, resting_hr, max_hr)
                if pace is not None:
                    aerobic_points.append((session_date, pace))

        self._render_5k_estimate(run_sessions_for_estimate, goal_seconds)
        self._render_fitness_fatigue_form(session_loads)
        self._render_weekly_distance(weekly_distance)
        self._render_weekly_load(weekly_run_load, weekly_other_load)
        self._render_aerobic_efficiency(aerobic_points)

    def _render_5k_estimate(self, runs: list[tuple[date, float, float]], goal_seconds: float) -> None:
        estimate_seconds = metrics.estimate_5k_seconds(runs, as_of=date.today())

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

    def _add_chart(self, figure, caption: str) -> None:
        block = tb.Frame(self.content_frame)
        block.pack(fill="both", padx=16, pady=(0, 16))

        canvas = FigureCanvasTkAgg(figure, master=block)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        tb.Label(block, text=caption, bootstyle="secondary", wraplength=800, justify="left").pack(
            anchor="w", pady=(4, 0)
        )

    def _render_fitness_fatigue_form(self, session_loads: list[tuple[date, float]]) -> None:
        dates, fitness, fatigue, form = metrics.fitness_fatigue_form(session_loads)
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
        points.sort(key=lambda point: point[0])
        dates = [point[0] for point in points]
        paces = [point[1] for point in points]
        figure = aerobic_efficiency_chart(dates, paces)
        self._add_chart(
            figure,
            "Pace at a fixed easy heart rate over time - a faster pace at the same "
            "effort means better aerobic fitness.",
        )
