from .standards import (
    MATRICES_RGB_TO_XYZ,
    MATRICES_XYZ_TO_RGB,
    WHITE_POINTS,
)


def hsv_to_rgb(h, s, v):
    h = h % 360.0
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c

    if   h < 60:  rp, gp, bp = c, x, 0
    elif h < 120: rp, gp, bp = x, c, 0
    elif h < 180: rp, gp, bp = 0, c, x
    elif h < 240: rp, gp, bp = 0, x, c
    elif h < 300: rp, gp, bp = x, 0, c
    else:         rp, gp, bp = c, 0, x

    return (
        int(round((rp + m) * 255)),
        int(round((gp + m) * 255)),
        int(round((bp + m) * 255)),
    )


def rgb_to_hsv(r, g, b):
    rp, gp, bp = r / 255.0, g / 255.0, b / 255.0
    cmax, cmin = max(rp, gp, bp), min(rp, gp, bp)
    d = cmax - cmin

    if d == 0:
        h = 0.0
    elif cmax == rp:
        h = 60 * (((gp - bp) / d) % 6)
    elif cmax == gp:
        h = 60 * ((bp - rp) / d + 2)
    else:
        h = 60 * ((rp - gp) / d + 4)

    s = 0.0 if cmax == 0 else d / cmax
    v = cmax
    return h % 360.0, s, v


def _srgb_to_linear(c):
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1 / 2.4)) - 0.055


def rgb_to_xyz(r, g, b, standard="D65"):
    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)

    m = MATRICES_RGB_TO_XYZ[standard]
    x = (m[0][0] * rl + m[0][1] * gl + m[0][2] * bl) * 100
    y = (m[1][0] * rl + m[1][1] * gl + m[1][2] * bl) * 100
    z = (m[2][0] * rl + m[2][1] * gl + m[2][2] * bl) * 100
    return x, y, z


def xyz_to_rgb(x, y, z, standard="D65", strategy="clipping"):
    m = MATRICES_XYZ_TO_RGB[standard]
    xl, yl, zl = x / 100.0, y / 100.0, z / 100.0

    rl = m[0][0] * xl + m[0][1] * yl + m[0][2] * zl
    gl = m[1][0] * xl + m[1][1] * yl + m[1][2] * zl
    bl = m[2][0] * xl + m[2][1] * yl + m[2][2] * zl

    was_clipped = False

    if strategy == "scaling":
        lo = min(rl, gl, bl, 0.0)
        hi = max(rl, gl, bl, 1.0)
        if lo < 0 or hi > 1:
            span = hi - lo
            if span > 0:
                rl = (rl - lo) / span
                gl = (gl - lo) / span
                bl = (bl - lo) / span
            was_clipped = True

    def to_byte(c):
        nonlocal was_clipped
        c = _linear_to_srgb(c)
        c255 = c * 255.0
        if c255 < 0 or c255 > 255:
            was_clipped = True
        return int(round(max(0.0, min(255.0, c255))))

    return to_byte(rl), to_byte(gl), to_byte(bl), was_clipped


def _f(t):
    delta = 6 / 29
    if t > delta ** 3:
        return t ** (1 / 3)
    return t / (3 * delta ** 2) + 4 / 29


def _f_inv(t):
    delta = 6 / 29
    if t > delta:
        return t ** 3
    return 3 * delta ** 2 * (t - 4 / 29)


def xyz_to_lab(x, y, z, standard="D65"):
    xn, yn, zn = WHITE_POINTS[standard]
    fx = _f(x / xn)
    fy = _f(y / yn)
    fz = _f(z / zn)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def lab_to_xyz(L, a, b, standard="D65"):
    xn, yn, zn = WHITE_POINTS[standard]
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    x = xn * _f_inv(fx)
    y = yn * _f_inv(fy)
    z = zn * _f_inv(fz)
    return x, y, z