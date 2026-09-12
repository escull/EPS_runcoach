import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import ttkbootstrap as tb

from eps_runcoach.core import db
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.importer import ImportSummary, import_files, import_folder


class ImportPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._queue: queue.Queue = queue.Queue()

        tb.Label(self, text="Import", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        button_row = tb.Frame(self)
        button_row.pack(anchor="w", padx=16, pady=8)

        self.choose_button = tb.Button(
            button_row, text="Choose files...", command=self._choose_files, bootstyle="primary"
        )
        self.choose_button.pack(side="left", padx=(0, 8))

        self.inbox_button = tb.Button(
            button_row, text="Import from inbox", command=self._import_from_inbox, bootstyle="primary"
        )
        self.inbox_button.pack(side="left")

        self.progress = tb.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=8)

        self.result_text = tk.Text(self, height=15, width=80, state="disabled")
        self.result_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=[("FIT files", "*.fit")])
        if not paths:
            return
        self._start_import(lambda conn: import_files([Path(p) for p in paths], conn))

    def _import_from_inbox(self) -> None:
        inbox = core_settings.get_setting(self.app.conn, core_settings.INBOX_FOLDER_KEY)
        if not inbox:
            messagebox.showwarning("No inbox folder set", "Set an inbox folder on the Settings page first.")
            return
        self._start_import(lambda conn: import_folder(inbox, conn))

    def _start_import(self, work) -> None:
        self.choose_button.configure(state="disabled")
        self.inbox_button.configure(state="disabled")
        self.progress.start(10)
        self._set_result_text("Importing...")

        def run() -> None:
            conn = db.get_connection(self.app.db_path)
            try:
                summary = work(conn)
            except Exception as exc:  # noqa: BLE001 - must never crash the UI thread
                summary = ImportSummary(failed=[("(import batch)", str(exc))])
            finally:
                conn.close()
            self._queue.put(summary)

        threading.Thread(target=run, daemon=True).start()
        self.after(100, self._poll_queue)

    def _poll_queue(self) -> None:
        try:
            summary = self._queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_queue)
            return

        self.progress.stop()
        self.progress["value"] = 0
        self.choose_button.configure(state="normal")
        self.inbox_button.configure(state="normal")
        self._show_summary(summary)

        sessions_page = self.app.pages.get("Sessions")
        if sessions_page is not None:
            sessions_page.refresh()

    def _show_summary(self, summary: ImportSummary) -> None:
        lines = [f"Imported ({len(summary.imported)}):"]
        lines += [f"  + {name}" for name in summary.imported]
        lines.append(f"Skipped ({len(summary.skipped)}):")
        lines += [f"  - {name}: {reason}" for name, reason in summary.skipped]
        lines.append(f"Failed ({len(summary.failed)}):")
        lines += [f"  ! {name}: {reason}" for name, reason in summary.failed]
        self._set_result_text("\n".join(lines))

    def _set_result_text(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")
