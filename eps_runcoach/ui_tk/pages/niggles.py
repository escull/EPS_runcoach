from tkinter import ttk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from eps_runcoach.charts.niggles_chart import niggle_severity_chart
from eps_runcoach.core import db
from eps_runcoach.ui_tk.formatting import format_date

COLUMNS = [
    ("date", "Date", 90),
    ("location", "Location", 90),
    ("side", "Side", 60),
    ("severity", "Severity", 70),
]


class NigglesPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._canvas_widget = None
        self._toolbar_frame = None

        tb.Label(self, text="Niggles", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        self.chart_frame = tb.Frame(self)
        self.chart_frame.pack(fill="both", padx=16, pady=(0, 8))

        tree_frame = tb.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.tree = ttk.Treeview(tree_frame, columns=[c[0] for c in COLUMNS], show="headings", height=8)
        for key, label, width in COLUMNS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        rows = db.get_all_niggles_with_dates(self.app.conn)
        self._render_chart(rows)
        self._render_table(rows)

    def _render_chart(self, rows) -> None:
        if self._canvas_widget is not None:
            self._canvas_widget.destroy()
        if self._toolbar_frame is not None:
            self._toolbar_frame.destroy()

        figure = niggle_severity_chart(rows)
        canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
        canvas.draw()

        self._toolbar_frame = tb.Frame(self.chart_frame)
        self._toolbar_frame.pack(fill="x")
        toolbar = NavigationToolbar2Tk(canvas, self._toolbar_frame)
        toolbar.update()

        self._canvas_widget = canvas.get_tk_widget()
        self._canvas_widget.pack(fill="both", expand=True)

    def _render_table(self, rows) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    format_date(row["session_start_time"]),
                    row["location"],
                    row["side"] or "-",
                    row["severity"],
                ),
            )
