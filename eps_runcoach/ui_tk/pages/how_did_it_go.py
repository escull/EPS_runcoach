"""Modal dialog for capturing how a session felt: effort (RPE), a free-text
note, niggles, and - for strength sessions - a focus tag. Reused both right
after import and from the session detail view.
"""

from __future__ import annotations

import sqlite3
import tkinter as tk
from typing import Callable

import ttkbootstrap as tb

from eps_runcoach.core import db

NIGGLE_LOCATIONS = ["ankle", "knee", "calf", "shin", "hip", "back", "other"]
NIGGLE_SIDES = ["-", "left", "right"]
FOCUS_TAGS = ["legs", "upper body", "full body", "core"]


class HowDidItGoDialog(tb.Toplevel):
    def __init__(self, app, session_id: int, on_done: Callable[[], None] | None = None):
        super().__init__(title="How did it go?", size=(480, 640), resizable=(True, True))
        self.app = app
        self.session_id = session_id
        self.on_done = on_done

        session = db.get_session(app.conn, session_id)
        existing_note = db.get_note(app.conn, session_id)
        self._niggles: list[dict] = [
            {"location": row["location"], "side": row["side"], "severity": row["severity"]}
            for row in db.get_niggles_for_session(app.conn, session_id)
        ]

        self._build(session, existing_note)
        self.grab_set()  # modal: blocks the rest of the app until this closes

    def _build(self, session: sqlite3.Row, existing_note: sqlite3.Row | None) -> None:
        sport_text = f"{session['sport']} ({session['sub_sport']})" if session["sub_sport"] else session["sport"]
        tb.Label(self, text=sport_text, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 0))

        rpe_row = tb.Frame(self)
        rpe_row.pack(fill="x", padx=16, pady=(12, 0))
        tb.Label(rpe_row, text="Effort (RPE 1-10):").pack(side="left")
        initial_rpe = existing_note["rpe"] if existing_note and existing_note["rpe"] else 5
        self.rpe_var = tk.IntVar(value=initial_rpe)
        tb.Spinbox(rpe_row, from_=1, to=10, textvariable=self.rpe_var, width=5).pack(side="left", padx=8)

        tb.Label(self, text="Notes:").pack(anchor="w", padx=16, pady=(12, 0))
        self.note_text = tk.Text(self, height=4, width=50)
        self.note_text.pack(fill="x", padx=16)
        if existing_note and existing_note["note_text"]:
            self.note_text.insert("1.0", existing_note["note_text"])

        initial_focus = existing_note["focus_tag"] if existing_note and existing_note["focus_tag"] else FOCUS_TAGS[0]
        self.focus_var = tk.StringVar(value=initial_focus)
        self.show_focus_tag = session["session_type"] == "strength"
        if self.show_focus_tag:
            focus_row = tb.Frame(self)
            focus_row.pack(fill="x", padx=16, pady=(12, 0))
            tb.Label(focus_row, text="Focus:").pack(side="left")
            tb.Combobox(
                focus_row, textvariable=self.focus_var, values=FOCUS_TAGS, state="readonly", width=15
            ).pack(side="left", padx=8)

        tb.Label(self, text="Niggles", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 0))

        self.niggles_list = tk.Listbox(self, height=4)
        self.niggles_list.pack(fill="x", padx=16, pady=(4, 4))
        self._refresh_niggles_list()

        # Split across two rows rather than one wide strip - a single row of
        # location + side + severity + both buttons doesn't reliably fit the
        # dialog width once fonts/DPI scale up.
        fields_row = tb.Frame(self)
        fields_row.pack(fill="x", padx=16, pady=(0, 4))

        self.location_var = tk.StringVar(value=NIGGLE_LOCATIONS[0])
        tb.Combobox(
            fields_row, textvariable=self.location_var, values=NIGGLE_LOCATIONS, state="readonly", width=8
        ).pack(side="left")

        self.side_var = tk.StringVar(value=NIGGLE_SIDES[0])
        tb.Combobox(
            fields_row, textvariable=self.side_var, values=NIGGLE_SIDES, state="readonly", width=6
        ).pack(side="left", padx=4)

        self.severity_var = tk.IntVar(value=3)
        tb.Label(fields_row, text="Severity:").pack(side="left", padx=(8, 0))
        tb.Spinbox(fields_row, from_=0, to=10, textvariable=self.severity_var, width=4).pack(side="left", padx=4)

        buttons_row = tb.Frame(self)
        buttons_row.pack(fill="x", padx=16, pady=(0, 8))
        tb.Button(buttons_row, text="Add niggle", command=self._add_niggle, bootstyle="secondary").pack(
            side="left", padx=(0, 4)
        )
        tb.Button(buttons_row, text="Remove selected", command=self._remove_selected_niggle, bootstyle="secondary").pack(
            side="left"
        )

        button_row = tb.Frame(self)
        button_row.pack(fill="x", padx=16, pady=16, side="bottom")
        tb.Button(button_row, text="Skip", command=self._skip, bootstyle="secondary").pack(side="right", padx=4)
        tb.Button(button_row, text="Save", command=self._save, bootstyle="primary").pack(side="right", padx=4)

    def _refresh_niggles_list(self) -> None:
        self.niggles_list.delete(0, "end")
        for niggle in self._niggles:
            side_text = f" ({niggle['side']})" if niggle["side"] else ""
            self.niggles_list.insert("end", f"{niggle['location']}{side_text} - severity {niggle['severity']}")

    def _add_niggle(self) -> None:
        side = self.side_var.get()
        self._niggles.append(
            {
                "location": self.location_var.get(),
                "side": None if side == "-" else side,
                "severity": self.severity_var.get(),
            }
        )
        self._refresh_niggles_list()

    def _remove_selected_niggle(self) -> None:
        selection = self.niggles_list.curselection()
        if not selection:
            return
        del self._niggles[selection[0]]
        self._refresh_niggles_list()

    def _save(self) -> None:
        note_text = self.note_text.get("1.0", "end").strip() or None
        focus_tag = self.focus_var.get() if self.show_focus_tag else None
        db.upsert_note(self.app.conn, self.session_id, rpe=self.rpe_var.get(), note_text=note_text, focus_tag=focus_tag)

        db.delete_niggles_for_session(self.app.conn, self.session_id)
        for niggle in self._niggles:
            db.insert_niggle(
                self.app.conn,
                self.session_id,
                location=niggle["location"],
                side=niggle["side"],
                severity=niggle["severity"],
            )

        self.app.request_coaching(self.session_id)
        self._close()

    def _skip(self) -> None:
        self._close()

    def _close(self) -> None:
        self.destroy()
        if self.on_done is not None:
            self.on_done()
