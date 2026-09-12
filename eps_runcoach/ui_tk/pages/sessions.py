from tkinter import ttk

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core.formatting import format_date, format_distance, format_duration, format_hr, format_pace

COLUMNS = [
    ("date", "Date", 90),
    ("type", "Type", 80),
    ("duration", "Duration", 80),
    ("distance", "Distance", 80),
    ("pace", "Pace", 90),
    ("avg_hr", "Avg HR", 70),
]

SORT_FIELDS = {
    "date": "start_time",
    "type": "session_type",
    "duration": "duration_s",
    "distance": "distance_km",
    "pace": "avg_pace_min_per_km",
    "avg_hr": "avg_heart_rate",
}


class SessionsPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._sort_reverse: dict[str, bool] = {}
        self._rows_by_id: dict[str, dict] = {}

        tb.Label(self, text="Sessions", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        tree_frame = tb.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.tree = ttk.Treeview(tree_frame, columns=[c[0] for c in COLUMNS], show="headings")
        for key, label, width in COLUMNS:
            self.tree.heading(key, text=label, command=lambda k=key: self._sort_by(k))
            self.tree.column(key, width=width, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._rows_by_id.clear()

        for row in db.get_all_sessions(self.app.conn):
            iid = str(row["id"])
            self._rows_by_id[iid] = dict(row)
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    format_date(row["start_time"]),
                    row["session_type"],
                    format_duration(row["duration_s"]),
                    format_distance(row["distance_km"]),
                    format_pace(row["avg_pace_min_per_km"]),
                    format_hr(row["avg_heart_rate"]),
                ),
            )

    def _on_double_click(self, event) -> None:
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.app.open_session_detail(int(item_id))

    def _sort_by(self, key: str) -> None:
        field = SORT_FIELDS[key]
        reverse = self._sort_reverse.get(key, False)

        rows = list(self._rows_by_id.items())
        rows.sort(key=lambda item: (item[1][field] is None, item[1][field]), reverse=reverse)
        self._sort_reverse[key] = not reverse

        for index, (iid, _) in enumerate(rows):
            self.tree.move(iid, "", index)
