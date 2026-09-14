from tkinter import ttk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from eps_runcoach.charts.body_chart import weight_chart
from eps_runcoach.core import db
from eps_runcoach.core.formatting import format_date
from eps_runcoach.ui_tk.pages.log_weight import LogWeightDialog

COLUMNS = [
    ("date", "Date", 110),
    ("weight", "Weight (kg)", 100),
]


class BodyPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._canvas_widget = None
        self._toolbar_frame = None

        header = tb.Frame(self)
        header.pack(fill="x", padx=16, pady=(16, 8))
        tb.Label(header, text="Body", font=("Segoe UI", 16, "bold")).pack(side="left")
        tb.Button(header, text="Log weight", command=self._open_log_weight, bootstyle="primary").pack(side="right")

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
        rows = db.get_all_body_metrics(self.app.conn)
        self._render_chart(rows)
        self._render_table(rows)

    def _render_chart(self, rows) -> None:
        if self._canvas_widget is not None:
            self._canvas_widget.destroy()
        if self._toolbar_frame is not None:
            self._toolbar_frame.destroy()

        figure = weight_chart(rows)
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
        for row in reversed(rows):  # newest first
            self.tree.insert(
                "",
                "end",
                values=(
                    format_date(row["recorded_date"]),
                    row["weight_kg"] if row["weight_kg"] is not None else "-",
                ),
            )

    def _open_log_weight(self) -> None:
        LogWeightDialog(self.app, on_done=self.refresh)
