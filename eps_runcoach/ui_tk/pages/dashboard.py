import ttkbootstrap as tb


class DashboardPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tb.Label(
            self,
            text="Dashboard\n\nComing in Phase 5: fitness/fatigue/form, 5k estimate, weekly totals.",
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")
