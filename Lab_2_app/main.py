import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from image_metadata import read_image_info, SUPPORTED


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Чтение информации из графических файлов")
        self.root.geometry("1050x600")
        self.folder = ""
        self.results = []

        top = tk.Frame(root, padx=10, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Папка с изображениями:").pack(side="left")
        self.path_entry = tk.Entry(top, width=55)
        self.path_entry.pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(top, text="Выбрать", command=self.choose_folder).pack(side="left", padx=3)
        tk.Button(top, text="Сканировать", command=self.scan_folder).pack(side="left", padx=3)
        tk.Button(top, text="Сохранить CSV", command=self.save_csv).pack(side="left", padx=3)

        columns = ("name", "format", "size", "resolution", "depth", "compression", "file_size", "status")
        self.table = ttk.Treeview(root, columns=columns, show="headings")
        names = {
            "name": "Имя файла", "format": "Формат", "size": "Размер, px",
            "resolution": "Разрешение", "depth": "Глубина цвета",
            "compression": "Сжатие", "file_size": "Размер файла", "status": "Статус"
        }
        widths = {"name": 180, "format": 70, "size": 100, "resolution": 110,
                  "depth": 120, "compression": 150, "file_size": 100, "status": 150}
        for col in columns:
            self.table.heading(col, text=names[col])
            self.table.column(col, width=widths[col], anchor="w")

        scroll = ttk.Scrollbar(root, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

        self.status = tk.Label(root, text="Выберите папку и нажмите «Сканировать»", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            self.folder = folder
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def scan_folder(self):
        folder = self.path_entry.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning("Внимание", "Сначала выберите существующую папку.")
            return

        self.folder = folder
        self.results = []
        self.table.delete(*self.table.get_children())
        files = []

        try:
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and os.path.splitext(name)[1].lower() in SUPPORTED:
                    files.append(path)
        except OSError as error:
            messagebox.showerror("Ошибка", str(error))
            return

        for path in files:
            try:
                info = read_image_info(path)
                self.results.append(info)
                values = (info.filename, info.format, info.dimensions, info.resolution,
                          info.color_depth, info.compression, info.file_size, info.status)
            except Exception as error:
                values = (os.path.basename(path), "Неизвестно", "—", "—", "—", "—",
                          str(os.path.getsize(path)), "Ошибка чтения")
            self.table.insert("", tk.END, values=values)

        self.status.config(text="Найдено файлов: {}. Обработка завершена.".format(len(files)))
        if not files:
            messagebox.showinfo("Результат", "В выбранной папке нет поддерживаемых изображений.")

    def save_csv(self):
        if not self.results:
            messagebox.showinfo("Нет данных", "Сначала просканируйте папку.")
            return

        filename = filedialog.asksaveasfilename(
            title="Сохранить результаты", defaultextension=".csv",
            filetypes=[("CSV-файл", "*.csv")], initialfile="results.csv"
        )
        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(["Имя файла", "Путь", "Формат", "Размер изображения",
                                 "Разрешение", "Глубина цвета", "Сжатие", "Размер файла", "Статус"])
                for info in self.results:
                    writer.writerow([info.filename, info.path, info.format, info.dimensions,
                                     info.resolution, info.color_depth, info.compression,
                                     info.file_size, info.status])
            messagebox.showinfo("Готово", "Результаты сохранены.")
        except OSError as error:
            messagebox.showerror("Ошибка сохранения", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
