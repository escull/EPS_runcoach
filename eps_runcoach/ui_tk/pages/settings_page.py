import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.coach.api_key import get_api_key, set_api_key
from eps_runcoach.core.formatting import format_duration, parse_mmss_to_seconds


class SettingsPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tb.Label(self, text="Settings", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        inbox_row = tb.Frame(self)
        inbox_row.pack(fill="x", padx=16, pady=8)
        tb.Label(inbox_row, text="Inbox folder:", width=16, anchor="w").pack(side="left")
        self.inbox_var = tk.StringVar()
        tb.Entry(inbox_row, textvariable=self.inbox_var, width=50).pack(side="left", padx=8, fill="x", expand=True)
        tb.Button(inbox_row, text="Browse...", command=self._browse, bootstyle="secondary").pack(side="left", padx=4)

        max_hr_row = tb.Frame(self)
        max_hr_row.pack(fill="x", padx=16, pady=8)
        tb.Label(max_hr_row, text="Max heart rate:", width=16, anchor="w").pack(side="left")
        self.max_hr_var = tk.StringVar()
        tb.Spinbox(max_hr_row, from_=100, to=230, textvariable=self.max_hr_var, width=6).pack(side="left", padx=8)
        tb.Label(max_hr_row, text="bpm").pack(side="left")
        self.max_hr_hint_label = tb.Label(max_hr_row, text="", bootstyle="secondary")
        self.max_hr_hint_label.pack(side="left", padx=8)

        resting_hr_row = tb.Frame(self)
        resting_hr_row.pack(fill="x", padx=16, pady=8)
        tb.Label(resting_hr_row, text="Resting heart rate:", width=16, anchor="w").pack(side="left")
        self.resting_hr_var = tk.StringVar()
        tb.Spinbox(resting_hr_row, from_=30, to=100, textvariable=self.resting_hr_var, width=6).pack(
            side="left", padx=8
        )
        tb.Label(resting_hr_row, text="bpm").pack(side="left")

        goal_row = tb.Frame(self)
        goal_row.pack(fill="x", padx=16, pady=8)
        tb.Label(goal_row, text="5k goal (mm:ss):", width=16, anchor="w").pack(side="left")
        self.goal_var = tk.StringVar()
        tb.Entry(goal_row, textvariable=self.goal_var, width=10).pack(side="left", padx=8)

        ai_model_row = tb.Frame(self)
        ai_model_row.pack(fill="x", padx=16, pady=8)
        tb.Label(ai_model_row, text="AI coach model:", width=16, anchor="w").pack(side="left")
        self.ai_model_var = tk.StringVar()
        tb.Entry(ai_model_row, textvariable=self.ai_model_var, width=25).pack(side="left", padx=8)

        api_key_row = tb.Frame(self)
        api_key_row.pack(fill="x", padx=16, pady=8)
        tb.Label(api_key_row, text="Gemini API key:", width=16, anchor="w").pack(side="left")
        self.api_key_var = tk.StringVar()
        tb.Entry(api_key_row, textvariable=self.api_key_var, width=40, show="*").pack(side="left", padx=8)

        tb.Button(self, text="Save", command=self._save, bootstyle="primary").pack(anchor="w", padx=16, pady=(8, 0))

        self.status_label = tb.Label(self, text="")
        self.status_label.pack(anchor="w", padx=16, pady=(4, 0))

    def on_show(self) -> None:
        conn = self.app.conn
        self.inbox_var.set(core_settings.get_setting(conn, core_settings.INBOX_FOLDER_KEY, default=""))
        self.resting_hr_var.set(core_settings.get_setting(conn, core_settings.RESTING_HEART_RATE_KEY, default=""))

        max_hr = core_settings.get_setting(conn, core_settings.MAX_HEART_RATE_KEY)
        if max_hr is None:
            suggested = db.get_max_observed_heart_rate(conn)
            self.max_hr_var.set(str(suggested) if suggested else "")
            self.max_hr_hint_label.configure(
                text="(suggested from your data - edit if needed)" if suggested else ""
            )
        else:
            self.max_hr_var.set(max_hr)
            self.max_hr_hint_label.configure(text="")

        goal_seconds = core_settings.get_setting(conn, core_settings.GOAL_5K_SECONDS_KEY)
        goal_seconds = float(goal_seconds) if goal_seconds else core_settings.DEFAULT_GOAL_5K_SECONDS
        self.goal_var.set(format_duration(goal_seconds))

        self.ai_model_var.set(
            core_settings.get_setting(conn, core_settings.AI_MODEL_NAME_KEY, default=core_settings.DEFAULT_AI_MODEL_NAME)
        )

        self.api_key_var.set(get_api_key())

        self.status_label.configure(text="")

    def _browse(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.inbox_var.set(folder)

    def _save(self) -> None:
        goal_seconds = parse_mmss_to_seconds(self.goal_var.get())
        if goal_seconds is None:
            self.status_label.configure(text='5k goal must be in "mm:ss" format, e.g. 25:00.', bootstyle="danger")
            return

        conn = self.app.conn
        core_settings.set_setting(conn, core_settings.INBOX_FOLDER_KEY, self.inbox_var.get())
        core_settings.set_setting(conn, core_settings.MAX_HEART_RATE_KEY, self.max_hr_var.get())
        core_settings.set_setting(conn, core_settings.RESTING_HEART_RATE_KEY, self.resting_hr_var.get())
        core_settings.set_setting(conn, core_settings.GOAL_5K_SECONDS_KEY, str(goal_seconds))
        core_settings.set_setting(conn, core_settings.AI_MODEL_NAME_KEY, self.ai_model_var.get())
        set_api_key(self.api_key_var.get())
        self.status_label.configure(text="Saved.", bootstyle="default")
