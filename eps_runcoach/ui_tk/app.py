"""Main application window: a sidebar that swaps between pages."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core.coach.base import CoachError
from eps_runcoach.core.coach.request import request_review
from eps_runcoach.ui_tk.pages.dashboard import DashboardPage
from eps_runcoach.ui_tk.pages.import_page import ImportPage
from eps_runcoach.ui_tk.pages.niggles import NigglesPage
from eps_runcoach.ui_tk.pages.session_detail import SessionDetailWindow
from eps_runcoach.ui_tk.pages.sessions import SessionsPage
from eps_runcoach.ui_tk.pages.settings_page import SettingsPage

PAGES = [
    ("Dashboard", DashboardPage),
    ("Sessions", SessionsPage),
    ("Import", ImportPage),
    ("Niggles", NigglesPage),
    ("Settings", SettingsPage),
]


class App(tb.Window):
    def __init__(self, db_path: str | Path = db.DEFAULT_DB_PATH):
        super().__init__(
            title="EPS RunCoach",
            themename="bootstrap-light",
            size=(1100, 700),
            on_close=self._on_close,
        )
        self.db_path = Path(db_path)
        self.conn = db.get_connection(self.db_path)
        self.pages: dict[str, tb.Frame] = {}

        self._build_layout()
        self.show_page("Sessions")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        sidebar = tb.Frame(self, bootstyle="secondary")
        sidebar.grid(row=0, column=0, sticky="ns")

        content = tb.Frame(self)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        for name, page_cls in PAGES:
            page = page_cls(content, app=self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

        for name, _ in PAGES:
            tb.Button(
                sidebar,
                text=name,
                bootstyle="secondary",
                width=14,
                command=lambda n=name: self.show_page(n),
            ).pack(fill="x", padx=8, pady=(8, 0))

    def show_page(self, name: str) -> None:
        page = self.pages[name]
        page.tkraise()
        if hasattr(page, "on_show"):
            page.on_show()

    def open_session_detail(self, session_id: int) -> None:
        SessionDetailWindow(app=self, session_id=session_id)

    def request_coaching(self, session_id: int, on_done: Callable[[], None] | None = None) -> None:
        """Ask the AI coach to review a session, in a background thread
        using its own database connection (sqlite3 connections aren't
        safe to share across threads). Errors show as a friendly popup
        rather than crashing; nothing is saved if the request fails.
        """
        result_queue: queue.Queue = queue.Queue()

        def run() -> None:
            conn = db.get_connection(self.db_path)
            try:
                request_review(conn, session_id)
                result_queue.put(None)
            except CoachError as exc:
                result_queue.put(exc)
            finally:
                conn.close()

        threading.Thread(target=run, daemon=True).start()
        self._poll_coaching_result(result_queue, on_done)

    def _poll_coaching_result(self, result_queue: queue.Queue, on_done: Callable[[], None] | None) -> None:
        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            self.after(200, lambda: self._poll_coaching_result(result_queue, on_done))
            return

        if isinstance(result, CoachError):
            messagebox.showwarning("Coach unavailable", str(result))
        if on_done is not None:
            on_done()

    def _on_close(self) -> None:
        self.conn.close()
        self.destroy()


def run() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run()
