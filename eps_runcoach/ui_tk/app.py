"""Main application window: a sidebar that swaps between pages."""

from __future__ import annotations

from pathlib import Path

import ttkbootstrap as tb

from eps_runcoach.core import db
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

    def _on_close(self) -> None:
        self.conn.close()
        self.destroy()


def run() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run()
