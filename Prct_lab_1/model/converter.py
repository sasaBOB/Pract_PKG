from . import color_math as cm


class ColorConverter:
    def __init__(self, standard="D65", strategy="clipping"):
        self.standard = standard
        self.strategy = strategy

    def hsv_to_lab(self, h, s, v):
        r, g, b = cm.hsv_to_rgb(h, s, v)
        x, y, z = cm.rgb_to_xyz(r, g, b, self.standard)
        return cm.xyz_to_lab(x, y, z, self.standard)

    def lab_to_hsv(self, L, a, b):
        x, y, z = cm.lab_to_xyz(L, a, b, self.standard)
        r, g, bl, clipped = cm.xyz_to_rgb(x, y, z, self.standard, self.strategy)
        h, s, v = cm.rgb_to_hsv(r, g, bl)
        return h, s, v, r, g, bl, clipped

    def hsv_to_xyz(self, h, s, v):
        r, g, b = cm.hsv_to_rgb(h, s, v)
        return cm.rgb_to_xyz(r, g, b, self.standard)

    def xyz_to_hsv(self, x, y, z):
        r, g, b, clipped = cm.xyz_to_rgb(x, y, z, self.standard, self.strategy)
        h, s, v = cm.rgb_to_hsv(r, g, b)
        return h, s, v, r, g, b, clipped

    def xyz_to_lab(self, x, y, z):
        return cm.xyz_to_lab(x, y, z, self.standard)

    def lab_to_xyz(self, L, a, b):
        return cm.lab_to_xyz(L, a, b, self.standard)