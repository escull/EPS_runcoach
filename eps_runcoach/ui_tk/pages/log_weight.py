"""Modal dialog for logging a single body weight entry, not tied to any
training session.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import Callable

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core.formatting import parse_ddmmyyyy_to_iso_date


class LogWeightDialog(tb.Toplevel):
    def __init__(self, app, on_done: Callable[[], None] | None = None):
        super().__init__(title="Log weight", size=(380, 280))
        self.app = app
        self.on_done = on_done

        tb.Label(self, text="Log weight", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        date_row = tb.Frame(self)
        date_row.pack(fill="x", padx=16, pady=4)
        tb.Label(date_row, text="Date (DD/MM/YYYY):", width=18, anchor="w").pack(side="left")
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        tb.Entry(date_row, textvariable=self.date_var, width=12).pack(side="left", padx=8)

        weight_row = tb.Frame(self)
        weight_row.pack(fill="x", padx=16, pady=4)
        tb.Label(weight_row, text="Weight (kg):", width=18, anchor="w").pack(side="left")
        self.weight_var = tk.StringVar()
        tb.Entry(weight_row, textvariable=self.weight_var, width=8).pack(side="left", padx=8)

        self.status_label = tb.Label(self, text="", bootstyle="danger")
        self.status_label.pack(anchor="w", padx=16, pady=(4, 0))

        button_row = tb.Frame(self)
        button_row.pack(fill="x", padx=16, pady=16, side="bottom")
        tb.Button(button_row, text="Cancel", command=self.destroy, bootstyle="secondary").pack(side="right", padx=4)
        tb.Button(button_row, text="Save", command=self._save, bootstyle="primary").pack(side="right", padx=4)

        self.grab_set()  # modal: blocks the rest of the app until this closes

    def _save(self) -> None:
        recorded_date = parse_ddmmyyyy_to_iso_date(self.date_var.get())
        if recorded_date is None:
            self.status_label.configure(text='Date must be in "DD/MM/YYYY" format.')
            return

        try:
            weight_kg = float(self.weight_var.get())
        except ValueError:
            self.status_label.configure(text="Weight must be a number.")
            return

        db.insert_body_metric(self.app.conn, recorded_date, weight_kg)
        self.destroy()
        if self.on_done is not None:
            self.on_done()
