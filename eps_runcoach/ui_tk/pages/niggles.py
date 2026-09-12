import ttkbootstrap as tb


class NigglesPage(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tb.Label(
            self,
            text="Niggles\n\nComing in Phase 4: how sessions felt, RPE, and niggle tracking.",
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")
