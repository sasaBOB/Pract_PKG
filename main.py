from viewmodel.color_viewmodel import ColorViewModel
from view.main_window import MainWindow


if __name__ == "__main__":
    vm = ColorViewModel(standard="D65", strategy="clipping")
    app = MainWindow(vm)
    app.mainloop()