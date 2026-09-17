from model.converter import ColorConverter
from model import color_math as cm


class ColorViewModel:
    def __init__(self, standard="D65", strategy="clipping"):
        self.converter = ColorConverter(standard, strategy)
        self._h = 0.0
        self._s = 1.0
        self._v = 1.0
        self._last_warning = ""

    @property
    def warning(self):
        return self._last_warning

    def set_standard(self, standard):
        self.converter.standard = standard

    def set_strategy(self, strategy):
        self.converter.strategy = strategy

    def set_from_hsv(self, h, s, v):
        self._h = float(h) % 360.0
        self._s = max(0.0, min(1.0, float(s)))
        self._v = max(0.0, min(1.0, float(v)))
        self._last_warning = ""

    def set_from_xyz(self, x, y, z):
        r, g, b, clipped = cm.xyz_to_rgb(x, y, z, self.converter.standard,
                                         self.converter.strategy)
        h, s, v = cm.rgb_to_hsv(r, g, b)
        self._h, self._s, self._v = h, s, v
        if clipped:
            name = "масштабирование" if self.converter.strategy == "scaling" else "обрезка"
            self._last_warning = f"XYZ выходит за пределы sRGB — выполнена {name}"
        else:
            self._last_warning = ""

    def set_from_lab(self, L, a, b):
        x, y, z = cm.lab_to_xyz(L, a, b, self.converter.standard)
        r, g, bl, clipped = cm.xyz_to_rgb(x, y, z, self.converter.standard,
                                          self.converter.strategy)
        h, s, v = cm.rgb_to_hsv(r, g, bl)
        self._h, self._s, self._v = h, s, v
        if clipped:
            name = "масштабирование" if self.converter.strategy == "scaling" else "обрезка"
            self._last_warning = f"LAB выходит за пределы sRGB — выполнена {name}"
        else:
            self._last_warning = ""

    def get_all(self):
        h, s, v = self._h, self._s, self._v
        r, g, b = cm.hsv_to_rgb(h, s, v)
        x, y, z = cm.rgb_to_xyz(r, g, b, self.converter.standard)
        L, a, bb = cm.xyz_to_lab(x, y, z, self.converter.standard)
        return {
            "hsv": (h, s, v),
            "xyz": (x, y, z),
            "lab": (L, a, bb),
            "rgb": (r, g, b),
            "warning": self._last_warning,
        }