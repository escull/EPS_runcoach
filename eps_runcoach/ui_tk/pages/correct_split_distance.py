"""Modal dialog for correcting one split's recorded distance, for treadmill
sessions where the device's own distance estimate was badly off and only
the session-level total was corrected afterwards.
"""

from __future__ import annotations

import sqlite3
import tkinter as tk
from typing import Callable

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core.formatting import format_distance


class CorrectSplitDistanceDialog(tb.Toplevel):
    def __init__(
        self,
        app,
        session_id: int,
        splits: list[sqlite3.Row],
        on_done: Callable[[], None] | None = None,
    ):
        super().__init__(title="Correct a split's distance", size=(420, 220))
        self.app = app
        self.session_id = session_id
        self.splits = [s for s in splits if s["distance_km"]]
        self.on_done = on_done

        tb.Label(self, text="Correct a split's distance", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=16, pady=(16, 8)
        )

        split_row = tb.Frame(self)
        split_row.pack(fill="x", padx=16, pady=4)
        tb.Label(split_row, text="Split:", width=14, anchor="w").pack(side="left")
        split_labels = [f"{s['split_index']} - currently {format_distance(s['distance_km'])}" for s in self.splits]
        self.split_var = tk.StringVar(value=split_labels[0] if split_labels else "")
        tb.Combobox(
            split_row, textvariable=self.split_var, values=split_labels, state="readonly", width=28
        ).pack(side="left", padx=8)

        distance_row = tb.Frame(self)
        distance_row.pack(fill="x", padx=16, pady=4)
        tb.Label(distance_row, text="True distance (km):", width=14, anchor="w").pack(side="left")
        self.distance_var = tk.StringVar()
        tb.Entry(distance_row, textvariable=self.distance_var, width=10).pack(side="left", padx=8)

        self.status_label = tb.Label(self, text="", bootstyle="danger")
        self.status_label.pack(anchor="w", padx=16, pady=(4, 0))

        button_row = tb.Frame(self)
        button_row.pack(fill="x", padx=16, pady=16, side="bottom")
        tb.Button(button_row, text="Cancel", command=self.destroy, bootstyle="secondary").pack(side="right", padx=4)
        tb.Button(button_row, text="Save", command=self._save, bootstyle="primary").pack(side="right", padx=4)

        self.grab_set()  # modal: blocks the rest of the app until this closes

    def _save(self) -> None:
        if not self.splits:
            self.status_label.configure(text="No splits with a recorded distance to correct.")
            return

        selected_index = self.split_var.get().split(" - ")[0]
        try:
            split_index = int(selected_index)
        except ValueError:
            self.status_label.configure(text="Choose a split.")
            return

        try:
            new_distance_km = float(self.distance_var.get())
        except ValueError:
            self.status_label.configure(text="True distance must be a number.")
            return
        if new_distance_km <= 0:
            self.status_label.configure(text="True distance must be greater than zero.")
            return

        try:
            db.correct_split_distance(self.app.conn, self.session_id, split_index, new_distance_km)
        except ValueError as exc:
            self.status_label.configure(text=str(exc))
            return

        self.destroy()
        if self.on_done is not None:
            self.on_done()
