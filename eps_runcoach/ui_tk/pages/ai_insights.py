"""AI Insights page: manually request a holistic coach review covering
everything since it was last consulted, plus a history of past reviews.
Nothing here triggers automatically - that's the point (bulk-importing
old sessions shouldn't spam requests one per session).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core.formatting import format_date


class AIInsightsPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Scrollable, same pattern as the Dashboard/Session detail views -
        # a review plus history can easily be taller than a laptop screen.
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        body = tb.Frame(canvas)
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_window, width=e.width))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        tb.Label(body, text="AI Insights", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        tb.Label(
            body,
            text="Ask the coach for a review covering everything since it last checked in - "
            "not tied to any single session.",
            bootstyle="secondary",
            wraplength=800,
            justify="left",
        ).pack(anchor="w", padx=16)

        self.last_consulted_label = tb.Label(body, text="", bootstyle="secondary")
        self.last_consulted_label.pack(anchor="w", padx=16, pady=(8, 0))

        self.get_insights_button = tb.Button(
            body, text="Get coach's insights", command=self._request_insights, bootstyle="primary"
        )
        self.get_insights_button.pack(anchor="w", padx=16, pady=8)

        tb.Label(body, text="Latest", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(8, 0))
        self.latest_frame = tb.Frame(body)
        self.latest_frame.pack(fill="x", padx=16, pady=(4, 16))

        tb.Label(body, text="History", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(8, 0))
        self.history_frame = tb.Frame(body)
        self.history_frame.pack(fill="x", padx=16, pady=(4, 16))

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        reviews = db.get_all_ai_reviews(self.app.conn)

        if reviews:
            self.last_consulted_label.configure(text=f"Last consulted: {format_date(reviews[0]['created_at'])}")
        else:
            self.last_consulted_label.configure(text="Last consulted: never")

        for widget in self.latest_frame.winfo_children():
            widget.destroy()
        if reviews:
            tb.Label(self.latest_frame, text=format_date(reviews[0]["created_at"]), bootstyle="secondary").pack(
                anchor="w"
            )
            tb.Label(self.latest_frame, text=reviews[0]["review_text"], wraplength=800, justify="left").pack(
                anchor="w", pady=(4, 0)
            )
        else:
            tb.Label(self.latest_frame, text="No insights yet.").pack(anchor="w")

        for widget in self.history_frame.winfo_children():
            widget.destroy()
        older_reviews = reviews[1:]
        if not older_reviews:
            tb.Label(self.history_frame, text="No earlier check-ins.").pack(anchor="w")
        else:
            for review in older_reviews:
                entry = tb.Frame(self.history_frame)
                entry.pack(fill="x", pady=(0, 12))
                tb.Label(entry, text=format_date(review["created_at"]), bootstyle="secondary").pack(anchor="w")
                tb.Label(entry, text=review["review_text"], wraplength=800, justify="left").pack(anchor="w")

    def _request_insights(self) -> None:
        self.get_insights_button.configure(state="disabled", text="Generating...")
        self.app.request_insights(on_done=self._on_insights_done)

    def _on_insights_done(self) -> None:
        if not self.winfo_exists():
            return
        self.get_insights_button.configure(state="normal", text="Get coach's insights")
        self.refresh()
