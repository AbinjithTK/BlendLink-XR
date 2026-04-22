# SPDX-License-Identifier: GPL-2.0-or-later

"""GP v3 freehand drawing tool with brush support."""

import bpy
import time

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
from .gp_brushes import (
    get_active_brush, get_active_color,
    apply_pressure, apply_opacity, apply_jitter, get_min_spacing,
)

_curr_drawing = None
_curr_stroke_index = None
_curr_point_count = 0
_prev_point_pos = None
_stroke_start_time = 0.0


def on_gp_stroke_start(_, event_name, event):
    global _curr_drawing, _curr_stroke_index, _curr_point_count
    global _prev_point_pos, _stroke_start_time

    disable_bounds_check()

    try:
        gp_obj = get_or_create_gp_object()
        drawing = get_active_drawing(gp_obj)
        if drawing is None:
            return

        brush = get_active_brush()
        color = get_active_color()

        _curr_drawing = drawing
        _stroke_start_time = time.time()

        world_pos = Vector(event.position)
        local_pos = world_to_local(gp_obj, world_pos)

        raw_pressure = get_pressure(event.value)
        radius = apply_pressure(brush, raw_pressure)
        opacity = apply_opacity(brush, raw_pressure)
        local_pos = apply_jitter(brush, local_pos)

        # Get or create material for active color
        mat_index = get_or_create_color_material(gp_obj, color)

        num_existing = len(drawing.strokes)
        drawing.add_strokes(sizes=[1])
        _curr_stroke_index = num_existing
        _curr_point_count = 1

        stroke = drawing.strokes[_curr_stroke_index]
        pt = stroke.points[0]
        pt.position = local_pos
        pt.radius = radius
        pt.opacity = opacity

        stroke.material_index = mat_index
        stroke.start_cap = 1
        stroke.end_cap = 1
        stroke.softness = brush["softness"]

        _prev_point_pos = world_pos
        apply_haptic_feedback(hand="main", type="TINY_LIGHT")

    except Exception as e:
        log.error("[GP Draw] Start error: {}".format(e))
        _curr_drawing = None
        _curr_stroke_index = None


def on_gp_stroke(_, event_name, event):
    global _curr_point_count, _prev_point_pos

    if _curr_drawing is None or _curr_stroke_index is None:
        return

    try:
        gp_obj = get_or_create_gp_object()
        brush = get_active_brush()
        world_pos = Vector(event.position)

        if _prev_point_pos is not None:
            dist = (world_pos - _prev_point_pos).length
            min_dist = get_min_spacing(brush) * xr_session.viewer_scale
            if dist < min_dist:
                return

        local_pos = world_to_local(gp_obj, world_pos)
        local_pos = apply_jitter(brush, local_pos)

        raw_pressure = get_pressure(event.value)
        radius = apply_pressure(brush, raw_pressure)
        opacity = apply_opacity(brush, raw_pressure)

        stroke = _curr_drawing.strokes[_curr_stroke_index]
        new_points = stroke.add_points(1)
        pt = new_points[0]
        pt.position = local_pos
        pt.radius = radius
        pt.opacity = opacity
        pt.delta_time = time.time() - _stroke_start_time

        _curr_point_count += 1
        _prev_point_pos = world_pos

    except Exception as e:
        log.error("[GP Draw] Stroke error: {}".format(e))


def on_gp_stroke_end(_, event_name, event):
    global _curr_drawing, _curr_stroke_index, _curr_point_count, _prev_point_pos

    enable_bounds_check()

    if _curr_drawing is None or _curr_stroke_index is None:
        return

    try:
        stroke = _curr_drawing.strokes[_curr_stroke_index]
        num_points = len(stroke.points)

        if num_points < 2:
            try:
                _curr_drawing.remove_strokes(indices=[_curr_stroke_index])
            except Exception:
                pass
        else:
            bpy.ops.ed.undo_push(message="GP stroke")
            apply_haptic_feedback(hand="main", type="TINY_STRONG")

    except Exception as e:
        log.error("[GP Draw] End error: {}".format(e))

    _curr_drawing = None
    _curr_stroke_index = None
    _curr_point_count = 0
    _prev_point_pos = None


def enable_tool():
    root.add_event_listener("trigger_main_start", on_gp_stroke_start)
    root.add_event_listener("trigger_main_press", on_gp_stroke)
    root.add_event_listener("trigger_main_end", on_gp_stroke_end)
    try:
        get_or_create_gp_object()
    except Exception:
        pass


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_gp_stroke_start)
    root.remove_event_listener("trigger_main_press", on_gp_stroke)
    root.remove_event_listener("trigger_main_end", on_gp_stroke_end)
