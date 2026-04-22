# SPDX-License-Identifier: GPL-2.0-or-later

"""GP brush presets — controls how stroke points are generated.

Each brush is a dict of parameters that modify the drawing behavior:
- base_radius: base stroke width
- pressure_curve: how pressure maps to radius ("linear", "square", "sqrt")
- opacity: base opacity (0-1)
- opacity_pressure: whether pressure affects opacity
- softness: stroke edge softness (0-1)
- jitter: random position offset per point (0 = none)
- spacing: minimum distance between points (multiplier of base)
- color: RGBA tuple or None (uses active material)

The active brush is stored in settings["gp.active_brush"].
"""

import random
from mathutils import Vector

from ..settings_manager import settings

# --- Brush Presets ---

BRUSHES = {
    "pencil": {
        "name": "Pencil",
        "base_radius": 0.003,
        "pressure_curve": "linear",
        "opacity": 1.0,
        "opacity_pressure": True,
        "softness": 0.0,
        "jitter": 0.0001,
        "spacing": 1.0,
    },
    "ink_pen": {
        "name": "Ink Pen",
        "base_radius": 0.004,
        "pressure_curve": "square",
        "opacity": 1.0,
        "opacity_pressure": False,
        "softness": 0.0,
        "jitter": 0.0,
        "spacing": 0.8,
    },
    "ink_rough": {
        "name": "Ink Rough",
        "base_radius": 0.005,
        "pressure_curve": "linear",
        "opacity": 0.9,
        "opacity_pressure": True,
        "softness": 0.1,
        "jitter": 0.0004,
        "spacing": 0.7,
    },
    "marker_bold": {
        "name": "Marker Bold",
        "base_radius": 0.012,
        "pressure_curve": "sqrt",
        "opacity": 0.8,
        "opacity_pressure": False,
        "softness": 0.2,
        "jitter": 0.0,
        "spacing": 0.5,
    },
    "marker_chisel": {
        "name": "Marker Chisel",
        "base_radius": 0.008,
        "pressure_curve": "linear",
        "opacity": 0.85,
        "opacity_pressure": False,
        "softness": 0.05,
        "jitter": 0.0,
        "spacing": 0.6,
    },
    "airbrush": {
        "name": "Airbrush",
        "base_radius": 0.015,
        "pressure_curve": "sqrt",
        "opacity": 0.3,
        "opacity_pressure": True,
        "softness": 0.8,
        "jitter": 0.001,
        "spacing": 0.4,
    },
    "dot": {
        "name": "Dot",
        "base_radius": 0.002,
        "pressure_curve": "linear",
        "opacity": 1.0,
        "opacity_pressure": False,
        "softness": 0.0,
        "jitter": 0.0,
        "spacing": 2.0,
    },
}

# --- Color Presets ---

COLORS = {
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "red": (0.8, 0.1, 0.1, 1.0),
    "orange": (0.9, 0.5, 0.1, 1.0),
    "yellow": (0.9, 0.9, 0.1, 1.0),
    "green": (0.1, 0.7, 0.2, 1.0),
    "blue": (0.1, 0.3, 0.9, 1.0),
    "purple": (0.6, 0.1, 0.8, 1.0),
    "brown": (0.4, 0.25, 0.1, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0),
}


def get_active_brush():
    """Get the active brush preset dict."""
    name = settings.get("gp.active_brush", "pencil")
    return BRUSHES.get(name, BRUSHES["pencil"])


def get_active_color():
    """Get the active stroke color as RGBA tuple."""
    return settings.get("gp.active_color", (0.0, 0.0, 0.0, 1.0))


def apply_pressure(brush, raw_pressure):
    """Apply the brush's pressure curve to get the final radius."""
    curve = brush["pressure_curve"]
    base = brush["base_radius"]

    p = max(raw_pressure, 0.05)  # minimum so strokes are visible

    if curve == "linear":
        return base * p
    elif curve == "square":
        return base * (p * p)
    elif curve == "sqrt":
        return base * (p ** 0.5)
    return base * p


def apply_opacity(brush, raw_pressure):
    """Get the opacity for a point based on brush settings."""
    if brush["opacity_pressure"]:
        return brush["opacity"] * max(raw_pressure, 0.1)
    return brush["opacity"]


def apply_jitter(brush, position):
    """Apply random jitter to a position."""
    j = brush["jitter"]
    if j <= 0:
        return position

    return Vector((
        position.x + random.uniform(-j, j),
        position.y + random.uniform(-j, j),
        position.z + random.uniform(-j, j),
    ))


def get_min_spacing(brush):
    """Get the minimum point spacing for this brush."""
    return 0.003 * brush["spacing"]
