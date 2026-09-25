import tkinter as tk
from tkinter import ttk, colorchooser

from model.color_math import rgb_to_hsv


BG_MAIN   = "#2b2b2b"
BG_BLOCK  = "#3a3a3a"
BG_SCALE  = "#1e1e1e"
FG_TEXT   = "#e0e0e0"
FG_ACCENT = "#f0c040"


class MainWindow(tk.Tk):
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        self.title("ЛР1 — HSV ↔ XYZ ↔ LAB (вариант 9)")
        self.geometry("820x640")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)

        self._updating = False

        self._setup_style()
        self._build()
        self._refresh()

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG_MAIN)
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT)
        style.configure("TButton", background=BG_BLOCK, foreground=FG_TEXT)
        style.map("TButton", background=[("active", "#4a4a4a")])

        style.configure("TEntry",
                        fieldbackground=BG_SCALE,
                        foreground=FG_TEXT,
                        insertcolor=FG_TEXT)

        style.configure("TLabelframe",
                        background=BG_BLOCK,
                        bordercolor="#555555",
                        relief="solid")
        style.configure("TLabelframe.Label",
                        background=BG_BLOCK,
                        foreground=FG_ACCENT,
                        font=("Segoe UI", 10, "bold"))

        style.configure("Block.TLabel",
                        background=BG_BLOCK,
                        foreground=FG_TEXT)

    def _build(self):
        prev = ttk.Frame(self, padding=6)
        prev.pack(fill="x", padx=10, pady=(10, 6))
        self.preview = tk.Canvas(prev, width=620, height=70,
                                 bg="#ff0000", highlightthickness=0)
        self.preview.pack(side="left", fill="x", expand=True)
        ttk.Button(prev, text="Палитра…", command=self._pick_color).pack(side="left", padx=6)

        self.hsv_vars = self._make_block(
            "HSV", "hsv",
            [("H", 0, 359.99, 0.5, "wrap"),
             ("S", 0, 1, 0.01, "clamp"),
             ("V", 0, 1, 0.01, "clamp")],
            self._on_hsv)

        self.xyz_vars = self._make_block(
            "XYZ", "xyz",
            [("X", 0, 95.05, 0.01, "clamp"),
             ("Y", 0, 100, 0.01, "clamp"),
             ("Z", 0, 108.9, 0.01, "clamp")],
            self._on_xyz)

        self.lab_vars = self._make_block(
            "LAB", "lab",
            [("L", 0, 100, 0.01, "clamp"),
             ("a", -128, 127, 0.01, "clamp"),
             ("b", -128, 127, 0.01, "clamp")],
            self._on_lab)

        self.warn_label = ttk.Label(self, text="", foreground="#ff6b6b")
        self.warn_label.pack(pady=6)

    def _make_block(self, title, model_name, fields, callback):
        f = ttk.LabelFrame(self, text=title, padding=8)
        f.pack(fill="x", padx=10, pady=4)
        vars_ = []
        for i, (name, lo, hi, step, mode) in enumerate(fields):
            ttk.Label(f, text=name, width=3, style="Block.TLabel")\
                .grid(row=i, column=0, sticky="w")

            scale = tk.Scale(
                f, from_=lo, to=hi, resolution=step,
                orient="horizontal",
                bg=BG_BLOCK, fg=FG_TEXT,
                troughcolor=BG_SCALE,
                activebackground=FG_ACCENT,
                highlightthickness=0, bd=0,
                showvalue=False,
                command=lambda val, idx=i: self._on_scale_move(idx, float(val), callback),
            )
            scale.grid(row=i, column=1, sticky="ew", padx=4, pady=2)

            entry_var = tk.StringVar()
            entry = ttk.Entry(f, textvariable=entry_var, width=10)
            entry.grid(row=i, column=2)

            def commit(event, idx=i, v=entry_var, cb=callback, c=lo, h=hi, m=mode):
                self._commit_entry(idx, v, cb, c, h, m)
            entry.bind("<Return>", commit)

            f.columnconfigure(1, weight=1)
            vars_.append({
                "scale": scale,
                "entry": entry_var,
                "lo": lo, "hi": hi,
                "model": model_name,
                "index": i,
            })
        return vars_

    def _commit_entry(self, idx, entry_var, callback, lo, hi, mode):
        text = entry_var.get().strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            self._refresh()
            return

        if mode == "wrap":
            value = value % 360.0
        else:
            value = max(lo, min(hi, value))

        callback(idx, value)
        self._refresh()

    def _on_scale_move(self, idx, val, callback):
        if self._updating:
            return
        callback(idx, val)

    def _on_hsv(self, idx, value):
        values = [self._get_value(self.hsv_vars[i]) for i in range(3)]
        values[idx] = value
        self.vm.set_from_hsv(*values)
        self._refresh(skip="hsv")

    def _on_xyz(self, idx, value):
        values = [self._get_value(self.xyz_vars[i]) for i in range(3)]
        values[idx] = value
        self.vm.set_from_xyz(*values)
        self._refresh(skip="xyz")

    def _on_lab(self, idx, value):
        values = [self._get_value(self.lab_vars[i]) for i in range(3)]
        values[idx] = value
        self.vm.set_from_lab(*values)
        self._refresh(skip="lab")

    @staticmethod
    def _get_value(var_dict):
        try:
            return float(var_dict["entry"].get().replace(",", "."))
        except ValueError:
            return 0.0

    def _pick_color(self):
        result = colorchooser.askcolor()
        if result is None or result[0] is None:
            return
        r, g, b = [int(c) for c in result[0]]
        h, s, v = rgb_to_hsv(r, g, b)
        self.vm.set_from_hsv(h, s, v)
        self._refresh()

    def _refresh(self, skip=None):
        self._updating = True
        try:
            d = self.vm.get_all()
            h, s, v = d["hsv"]
            x, y, z = d["xyz"]
            L, a, b = d["lab"]
            r, g, bl = d["rgb"]

            if skip != "hsv":
                self._set_block(self.hsv_vars, (h, s, v))
            if skip != "xyz":
                self._set_block(self.xyz_vars, (x, y, z))
            if skip != "lab":
                self._set_block(self.lab_vars, (L, a, b))

            self.preview.configure(bg=f"#{r:02x}{g:02x}{bl:02x}")
            self.warn_label.configure(text=d["warning"])
        finally:
            self._updating = False

    @staticmethod
    def _set_block(vars_, values):
        for var, val in zip(vars_, values):
            lo = var["lo"]
            hi = var["hi"]
            safe = max(lo, min(hi, float(val)))
            var["entry"].set(f"{float(val):.2f}")
            var["scale"].set(safe)