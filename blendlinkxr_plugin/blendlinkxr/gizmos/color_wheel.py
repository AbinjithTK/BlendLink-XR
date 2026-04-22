# SPDX-License-Identifier: GPL-2.0-or-later

"""HSV color wheel gizmo for GP color picking in VR.

Renders a circular HSV wheel using a custom fragment shader.
The user points at the wheel with the laser and clicks to pick a color.
Hue varies around the circumference, saturation from center to edge.
A brightness bar sits to the right.

The picked color is stored in settings["gp.active_color"].
"""

import bpy
import math

import gpu
from gpu_extras.batch import batch_for_shader

from bl_xr import root, xr_session, Node, Bounds
from bl_xr.ui.components import Mesh
from bl_xr.consts import VEC_ZERO, VEC_ONE, WHITE
from bl_xr.utils import apply_haptic_feedback

from mathutils import Vector, Quaternion

from ..settings_manager import settings
from ..utils import log

WHEEL_RADIUS = 0.03  # meters in local space
WHEEL_SEGMENTS = 64
BRIGHTNESS_BAR_WIDTH = 0.008
BRIGHTNESS_BAR_HEIGHT = WHEEL_RADIUS * 2

_wheel_node = None
_wheel_shader = None
_wheel_batch = None
_bar_batch = None
_is_picking = False


def _hsv_to_rgb(h, s, v):
    """Convert HSV (0-1 range) to RGB."""
    if s == 0:
        return (v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return (v, t, p)
    elif i == 1:
        return (q, v, p)
    elif i == 2:
        return (p, v, t)
    elif i == 3:
        return (p, q, v)
    elif i == 4:
        return (t, p, v)
    else:
        return (v, p, q)


def _build_wheel_mesh():
    """Build a disc mesh with per-vertex HSV colors for the color wheel."""
    verts = []
    colors = []
    indices = []

    brightness = settings.get("gp.color_brightness", 1.0)

    # Center vertex (white at full brightness)
    verts.append((0, 0, 0))
    colors.append((brightness, brightness, brightness, 1.0))

    # Ring vertices
    for i in range(WHEEL_SEGMENTS):
        angle = 2.0 * math.pi * i / WHEEL_SEGMENTS
        x = WHEEL_RADIUS * math.cos(angle)
        y = WHEEL_RADIUS * math.sin(angle)
        verts.append((x, y, 0))

        hue = i / WHEEL_SEGMENTS
        r, g, b = _hsv_to_rgb(hue, 1.0, brightness)
        colors.append((r, g, b, 1.0))

    # Triangle fan
    for i in range(WHEEL_SEGMENTS):
        next_i = (i % WHEEL_SEGMENTS) + 1
        next_next = ((i + 1) % WHEEL_SEGMENTS) + 1
        indices.append((0, next_i, next_next))

    return verts, colors, indices


def _build_brightness_bar():
    """Build a vertical brightness bar mesh next to the wheel."""
    steps = 16
    verts = []
    colors = []
    indices = []

    x_offset = WHEEL_RADIUS + 0.008
    bar_w = BRIGHTNESS_BAR_WIDTH
    bar_h = BRIGHTNESS_BAR_HEIGHT

    for i in range(steps + 1):
        t = i / steps
        y = -WHEEL_RADIUS + t * bar_h
        brightness = t

        verts.append((x_offset, y, 0))
        verts.append((x_offset + bar_w, y, 0))
        colors.append((brightness, brightness, brightness, 1.0))
        colors.append((brightness, brightness, brightness, 1.0))

    for i in range(steps):
        base = i * 2
        indices.append((base, base + 1, base + 2))
        indices.append((base + 1, base + 3, base + 2))

    return verts, colors, indices


def _build_batches():
    """Build GPU batches for the wheel and brightness bar."""
    global _wheel_batch, _bar_batch, _wheel_shader

    if bpy.app.background:
        return

    # Use vertex color shader
    try:
        shader_name = "SMOOTH_COLOR" if bpy.app.version >= (4, 0, 0) else "3D_SMOOTH_COLOR"
        _wheel_shader = gpu.shader.from_builtin(shader_name)
    except Exception:
        _wheel_shader = gpu.shader.from_builtin("SMOOTH_COLOR")

    # Wheel
    w_verts, w_colors, w_indices = _build_wheel_mesh()
    _wheel_batch = batch_for_shader(
        _wheel_shader, 'TRIS',
        {"pos": w_verts, "color": w_colors},
        indices=w_indices,
    )

    # Brightness bar
    b_verts, b_colors, b_indices = _build_brightness_bar()
    _bar_batch = batch_for_shader(
        _wheel_shader, 'TRIS',
        {"pos": b_verts, "color": b_colors},
        indices=b_indices,
    )


def _rebuild_wheel():
    """Rebuild the wheel when brightness changes."""
    global _wheel_batch
    if _wheel_shader is None:
        return

    w_verts, w_colors, w_indices = _build_wheel_mesh()
    _wheel_batch = batch_for_shader(
        _wheel_shader, 'TRIS',
        {"pos": w_verts, "color": w_colors},
        indices=w_indices,
    )


class ColorWheelNode(Node):
    """Node that renders the HSV color wheel."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.style["fixed_scale"] = True
        self.intersects = None

        # Dummy mesh so the renderer doesn't skip us
        # (we override draw() so this is never actually rendered)
        self._has_custom_draw = True

    @property
    def bounds_local(self):
        r = WHEEL_RADIUS + BRIGHTNESS_BAR_WIDTH + 0.01
        return Bounds(Vector((-r, -r, 0)), Vector((r, r, 0)))

    def draw(self):
        """Custom draw the color wheel and brightness bar."""
        if _wheel_shader is None or _wheel_batch is None:
            _build_batches()

        if _wheel_shader is None or _wheel_batch is None:
            return

        _wheel_shader.bind()
        _wheel_batch.draw(_wheel_shader)

        if _bar_batch is not None:
            _bar_batch.draw(_wheel_shader)

    def update(self):
        """Position the wheel relative to the alt controller."""
        # Positioned to the right of the main menu
        pass  # Position is set by the parent in main_menu.py


def _pick_color_from_position(local_pos):
    """Convert a local-space position on the wheel to an HSV color."""
    x, y = local_pos.x, local_pos.y

    # Check if on brightness bar
    bar_x_start = WHEEL_RADIUS + 0.008
    bar_x_end = bar_x_start + BRIGHTNESS_BAR_WIDTH
    if bar_x_start <= x <= bar_x_end:
        t = (y + WHEEL_RADIUS) / BRIGHTNESS_BAR_HEIGHT
        t = max(0.0, min(1.0, t))
        settings["gp.color_brightness"] = t
        _rebuild_wheel()
        # Update the current color with new brightness
        _update_color_with_brightness()
        return True

    # Check if on wheel
    dist = math.sqrt(x * x + y * y)
    if dist > WHEEL_RADIUS:
        return False

    # Compute hue and saturation
    hue = (math.atan2(y, x) / (2.0 * math.pi)) % 1.0
    saturation = dist / WHEEL_RADIUS

    brightness = settings.get("gp.color_brightness", 1.0)
    r, g, b = _hsv_to_rgb(hue, saturation, brightness)

    settings["gp.active_color"] = (r, g, b, 1.0)
    settings["gp.last_hue"] = hue
    settings["gp.last_saturation"] = saturation
    return True


def _update_color_with_brightness():
    """Recompute the active color using stored hue/sat + new brightness."""
    hue = settings.get("gp.last_hue", 0.0)
    sat = settings.get("gp.last_saturation", 0.0)
    brightness = settings.get("gp.color_brightness", 1.0)
    r, g, b = _hsv_to_rgb(hue, sat, brightness)
    settings["gp.active_color"] = (r, g, b, 1.0)


def on_wheel_pointer_press(self, event_name, event):
    """Handle pointer press on the color wheel."""
    global _is_picking

    if event.position is None:
        return

    # Convert world hit position to wheel local space
    try:
        wheel = root.q("#color_wheel")
        if wheel is None:
            return

        local_pos = wheel.world_to_local_point(event.position)
        if _pick_color_from_position(local_pos):
            _is_picking = True
            apply_haptic_feedback(hand="main", type="TINY_LIGHT")
    except Exception as e:
        log.error("[ColorWheel] Pick error: {}".format(e))


def on_wheel_pointer_end(self, event_name, event):
    global _is_picking
    _is_picking = False


# Pre-create the node at module import time (Critical Rule #1)
color_wheel = ColorWheelNode(id="color_wheel")


def enable_gizmo():
    root.append_child(color_wheel)
    _build_batches()

    root.add_event_listener("pointer_main_press_start", on_wheel_pointer_press)
    root.add_event_listener("pointer_main_press_press", on_wheel_pointer_press)
    root.add_event_listener("pointer_main_press_end", on_wheel_pointer_end)


def disable_gizmo():
    root.remove_child(color_wheel)

    root.remove_event_listener("pointer_main_press_start", on_wheel_pointer_press)
    root.remove_event_listener("pointer_main_press_press", on_wheel_pointer_press)
    root.remove_event_listener("pointer_main_press_end", on_wheel_pointer_end)
