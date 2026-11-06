import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os

# ------------------------------------------------------------
# МОРФОЛОГИЧЕСКАЯ ОБРАБОТКА ИЗОБРАЖЕНИЙ
# Все операции реализованы вручную через массивы и циклы.
# ------------------------------------------------------------

def make_structure(shape, size):
    """Создание структурирующего элемента."""
    size = max(3, int(size))
    if size % 2 == 0:
        size += 1
    r = size // 2
    yy, xx = np.mgrid[-r:r+1, -r:r+1]
    if shape == "Крест":
        return (xx == 0) | (yy == 0)
    if shape == "Круг":
        return xx * xx + yy * yy <= r * r
    return np.ones((size, size), dtype=bool)


def shift_index(index, limit, mode):
    if mode == "Clamp":
        return min(max(index, 0), limit - 1)
    # Reflect: зеркальное отражение без повторения крайнего пикселя
    if limit == 1:
        return 0
    while index < 0 or index >= limit:
        if index < 0:
            index = -index
        if index >= limit:
            index = 2 * limit - 2 - index
    return index


def morphology_gray(src, structure, operation, border="Reflect"):
    """Ручная эрозия/дилатация для полутонового изображения."""
    h, w = src.shape
    kh, kw = structure.shape
    cy, cx = kh // 2, kw // 2
    out = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            values = []
            for sy in range(kh):
                for sx in range(kw):
                    if structure[sy, sx]:
                        yy = shift_index(y + sy - cy, h, border)
                        xx = shift_index(x + sx - cx, w, border)
                        values.append(int(src[yy, xx]))
            if operation == "Эрозия":
                out[y, x] = min(values)
            else:
                out[y, x] = max(values)
    return out


def apply_morphology(image, operation, structure, border):
    """Операции над каждым каналом RGB либо одним каналом яркости."""
    src = np.asarray(image)
    if src.ndim == 2:
        channels = [src]
    else:
        channels = [src[:, :, c] for c in range(src.shape[2])]

    result_channels = []
    for channel in channels:
        if operation == "Эрозия":
            result = morphology_gray(channel, structure, "Эрозия", border)
        elif operation == "Дилатация":
            result = morphology_gray(channel, structure, "Дилатация", border)
        elif operation == "Открытие":
            temp = morphology_gray(channel, structure, "Эрозия", border)
            result = morphology_gray(temp, structure, "Дилатация", border)
        elif operation == "Закрытие":
            temp = morphology_gray(channel, structure, "Дилатация", border)
            result = morphology_gray(temp, structure, "Эрозия", border)
        elif operation == "Морфологический градиент":
            dil = morphology_gray(channel, structure, "Дилатация", border)
            ero = morphology_gray(channel, structure, "Эрозия", border)
            result = np.clip(dil.astype(np.int16) - ero.astype(np.int16), 0, 255).astype(np.uint8)
        elif operation == "Top-Hat":
            ero = morphology_gray(channel, structure, "Эрозия", border)
            opened = morphology_gray(ero, structure, "Дилатация", border)
            result = np.clip(channel.astype(np.int16) - opened.astype(np.int16), 0, 255).astype(np.uint8)
        elif operation == "Black-Hat":
            dil = morphology_gray(channel, structure, "Дилатация", border)
            closed = morphology_gray(dil, structure, "Эрозия", border)
            result = np.clip(closed.astype(np.int16) - channel.astype(np.int16), 0, 255).astype(np.uint8)
        result_channels.append(result)

    if len(result_channels) == 1:
        return Image.fromarray(result_channels[0], mode="L")
    return Image.fromarray(np.stack(result_channels, axis=2), mode="RGB")


class MorphologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №3 — Морфологическая обработка")
        self.root.geometry("1100x720")
        self.original = None
        self.result = None
        self.tk_original = None
        self.tk_result = None

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Открыть изображение", command=self.open_image).pack(side="left", padx=4)
        ttk.Button(top, text="Сохранить результат", command=self.save_result).pack(side="left", padx=4)

        settings = ttk.LabelFrame(root, text="Параметры обработки", padding=8)
        settings.pack(fill="x", padx=8, pady=4)

        ttk.Label(settings, text="Операция:").grid(row=0, column=0, sticky="w")
        self.operation = tk.StringVar(value="Эрозия")
        operations = ["Эрозия", "Дилатация", "Открытие", "Закрытие",
                      "Морфологический градиент", "Top-Hat", "Black-Hat"]
        ttk.Combobox(settings, textvariable=self.operation, values=operations,
                     state="readonly", width=28).grid(row=0, column=1, padx=6)

        ttk.Label(settings, text="Структурный элемент:").grid(row=0, column=2, sticky="w")
        self.shape = tk.StringVar(value="Квадрат")
        ttk.Combobox(settings, textvariable=self.shape,
                     values=["Квадрат", "Крест", "Круг"],
                     state="readonly", width=12).grid(row=0, column=3, padx=6)

        ttk.Label(settings, text="Размер:").grid(row=0, column=4, sticky="w")
        self.size = tk.IntVar(value=3)
        ttk.Spinbox(settings, from_=3, to=15, increment=2, textvariable=self.size,
                    width=5).grid(row=0, column=5, padx=5)

        ttk.Label(settings, text="Обработка краёв:").grid(row=1, column=0, sticky="w", pady=7)
        self.border = tk.StringVar(value="Reflect")
        ttk.Combobox(settings, textvariable=self.border, values=["Reflect", "Clamp"],
                     state="readonly", width=12).grid(row=1, column=1, sticky="w", padx=6)
        ttk.Button(settings, text="Применить", command=self.process).grid(row=1, column=3, padx=6)

        panels = ttk.Frame(root, padding=8)
        panels.pack(fill="both", expand=True)
        left = ttk.LabelFrame(panels, text="Исходное изображение", padding=5)
        left.pack(side="left", fill="both", expand=True, padx=5)
        right = ttk.LabelFrame(panels, text="Результат", padding=5)
        right.pack(side="left", fill="both", expand=True, padx=5)
        self.original_label = ttk.Label(left, text="Откройте изображение")
        self.original_label.pack(expand=True)
        self.result_label = ttk.Label(right, text="Здесь появится результат")
        self.result_label.pack(expand=True)

        self.status = tk.StringVar(value="Готово. Выберите изображение.")
        ttk.Label(root, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def show_image(self, image, label, which):
        preview = image.copy()
        preview.thumbnail((500, 500))
        photo = ImageTk.PhotoImage(preview)
        label.configure(image=photo, text="")
        if which == "original":
            self.tk_original = photo
        else:
            self.tk_result = photo

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                       ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            self.original = Image.open(path).convert("RGB")
            self.result = None
            self.show_image(self.original, self.original_label, "original")
            self.result_label.configure(image="", text="Здесь появится результат")
            self.status.set(f"Загружено: {os.path.basename(path)} ({self.original.width}×{self.original.height})")
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть изображение:\n{exc}")

    def process(self):
        if self.original is None:
            messagebox.showwarning("Нет изображения", "Сначала откройте изображение.")
            return
        try:
            size = int(self.size.get())
            if size < 3:
                raise ValueError("Размер должен быть не меньше 3.")
            structure = make_structure(self.shape.get(), size)
            self.result = apply_morphology(self.original, self.operation.get(),
                                           structure, self.border.get())
            self.show_image(self.result, self.result_label, "result")
            self.status.set(f"Выполнено: {self.operation.get()}, элемент {self.shape.get()}, {structure.shape[0]}×{structure.shape[1]}, край: {self.border.get()}")
        except Exception as exc:
            messagebox.showerror("Ошибка обработки", str(exc))

    def save_result(self):
        if self.result is None:
            messagebox.showwarning("Нет результата", "Сначала выполните обработку.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            try:
                self.result.save(path)
                self.status.set(f"Результат сохранён: {path}")
            except Exception as exc:
                messagebox.showerror("Ошибка сохранения", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = MorphologyApp(root)
    root.mainloop()
