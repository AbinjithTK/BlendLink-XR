# SPDX-License-Identifier: GPL-2.0-or-later

"""GP v3 straight line tool — draws a line between press and release."""

import bpy

from bl_xr import root, xr_session
from bl_xr.utils import apply_haptic_feedback
from mathutils import Vector

from ..settings_manager import settings
from ..utils import log
from ..utils import enable_bounds_check, disable_bounds_check
from .gp_utils import (
    get_or_create_gp_object, get_active_drawing,
    world_to_local, get_pressure, get_or_create_color_material,
)

DEFAULT_RADIUS = 0.005
NUM_LINE_POINTS = 20  # interpolated points for smooth line

_start_pos = None
_start_world = None


def on_gp_line_start(_, event_name, event):
    global _start_pos, _start_world

    disable_bounds_check()

    _start_world = Vector(event.position)
    try:
        gp_obj = get_or_create_gp_object()
        _start_pos = world_to_local(gp_obj, _start_world)
        apply_haptic_feedback(hand="main", type="TINY_LIGHT")
    except Exception as e:
        log.error("[GP Line] Start error: {}".format(e))
        _start_pos = None


def on_gp_line_end(_, event_name, event):
    global _start_pos, _start_world

    enable_bounds_check()

    if _start_pos is None:
        return

    try:
        gp_obj = get_or_create_gp_object()
        drawing = get_active_drawing(gp_obj)
        if drawing is None:
            return

        end_world = Vector(event.position)
        end_pos = world_to_local(gp_obj, end_world)

        # Skip if too short
        if (_start_world - end_world).length < 0.002 * xr_session.viewer_scale:
            _start_pos = None
            return

        pressure = get_pressure(event.value)
        radius = DEFAULT_RADIUS * pressure

        # Create stroke with interpolated points
        from .gp_brushes import get_active_color
        color = get_active_color()
        mat_index = get_or_create_color_material(gp_obj, color)

        drawing.add_strokes(sizes=[NUM_LINE_POINTS])
        stroke = drawing.strokes[-1]
        stroke.material_index = mat_index
        stroke.start_cap = 1
        stroke.end_cap = 1

        for i in range(NUM_LINE_POINTS):
            t = i / (NUM_LINE_POINTS - 1)
            pt = stroke.points[i]
            pt.position = _start_pos.lerp(end_pos, t)
            pt.radius = radius
            pt.opacity = 1.0

        bpy.ops.ed.undo_push(message="GP line")
        apply_haptic_feedback(hand="main", type="TINY_STRONG")

    except Exception as e:
        log.error("[GP Line] End error: {}".format(e))

    _start_pos = None
    _start_world = None


def enable_tool():
    root.add_event_listener("trigger_main_start", on_gp_line_start)
    root.add_event_listener("trigger_main_end", on_gp_line_end)
    try:
        get_or_create_gp_object()
    except Exception:
        pass


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_gp_line_start)
    root.remove_event_listener("trigger_main_end", on_gp_line_end)
