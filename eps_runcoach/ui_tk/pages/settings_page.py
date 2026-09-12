import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as tb

from eps_runcoach.core import settings as core_settings


class SettingsPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tb.Label(self, text="Settings", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        row = tb.Frame(self)
        row.pack(fill="x", padx=16, pady=8)

        tb.Label(row, text="Inbox folder:").pack(side="left")
        self.inbox_var = tk.StringVar()
        tb.Entry(row, textvariable=self.inbox_var, width=50).pack(side="left", padx=8, fill="x", expand=True)
        tb.Button(row, text="Browse...", command=self._browse, bootstyle="secondary").pack(side="left", padx=4)
        tb.Button(row, text="Save", command=self._save, bootstyle="primary").pack(side="left", padx=4)

        self.status_label = tb.Label(self, text="")
        self.status_label.pack(anchor="w", padx=16)

        tb.Label(
            self,
            text="More settings (max heart rate, resting heart rate, 5k goal) arrive in Phase 5.",
            bootstyle="secondary",
        ).pack(anchor="w", padx=16, pady=8)

    def on_show(self) -> None:
        current = core_settings.get_setting(self.app.conn, core_settings.INBOX_FOLDER_KEY, default="")
        self.inbox_var.set(current)
        self.status_label.configure(text="")

    def _browse(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.inbox_var.set(folder)

    def _save(self) -> None:
        core_settings.set_setting(self.app.conn, core_settings.INBOX_FOLDER_KEY, self.inbox_var.get())
        self.status_label.configure(text="Saved.")
