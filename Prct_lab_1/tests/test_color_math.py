import unittest
from model import color_math as cm


class TestColorMath(unittest.TestCase):
    def test_red_lab(self):
        x, y, z = cm.rgb_to_xyz(255, 0, 0, "D65")
        L, a, b = cm.xyz_to_lab(x, y, z, "D65")
        self.assertAlmostEqual(L, 53.24, delta=0.5)
        self.assertAlmostEqual(a, 80.09, delta=0.5)
        self.assertAlmostEqual(b, 67.20, delta=0.5)

    def test_white_xyz(self):
        x, y, z = cm.rgb_to_xyz(255, 255, 255, "D65")
        self.assertAlmostEqual(x, 95.05, delta=0.5)
        self.assertAlmostEqual(y, 100.0, delta=0.5)
        self.assertAlmostEqual(z, 108.9, delta=0.5)

    def test_roundtrip_hsv(self):
        h, s, v = 200.0, 0.5, 0.8
        r, g, b = cm.hsv_to_rgb(h, s, v)
        h2, s2, v2 = cm.rgb_to_hsv(r, g, b)
        self.assertAlmostEqual(h, h2, delta=1.0)
        self.assertAlmostEqual(s, s2, delta=0.01)
        self.assertAlmostEqual(v, v2, delta=0.01)

    def test_clipping(self):
        r, g, b, clipped = cm.xyz_to_rgb(150, 20, 20, "D65", "clipping")
        self.assertTrue(clipped)

    def test_scaling(self):
        r, g, b, clipped = cm.xyz_to_rgb(150, 20, 20, "D65", "scaling")
        self.assertTrue(clipped)
        self.assertTrue(0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255)


if __name__ == "__main__":
    unittest.main()