# SPDX-License-Identifier: GPL-2.0-or-later

"""GP v3 stroke smoother — smooths stroke points near the cursor."""

import bpy

from bl_xr import root, xr_session
from bl_xr.utils import apply_haptic_feedback
from mathutils import Vector

from ..settings_manager import settings
from ..utils import log
from ..utils import enable_bounds_check, disable_bounds_check
from .gp_utils import get_gp_object, get_active_drawing, world_to_local

_is_smoothing = False
_smoothed_any = False


def _smooth_strokes_near_cursor(drawing, gp_obj, world_pos, radius, factor=0.5):
    """Smooth points within radius of world_pos by averaging neighbors."""
    local_pos = world_to_local(gp_obj, world_pos)
    local_radius = radius / max(gp_obj.matrix_world.to_scale())

    smoothed = False
    for stroke in drawing.strokes:
        points = stroke.points
        n = len(points)
        if n < 3:
            continue

        for i in range(1, n - 1):
            pt = points[i]
            dist = (Vector(pt.position) - local_pos).length
            if dist < local_radius:
                prev_pos = Vector(points[i - 1].position)
                next_pos = Vector(points[i + 1].position)
                curr_pos = Vector(pt.position)
                avg = (prev_pos + next_pos) / 2.0
                new_pos = curr_pos.lerp(avg, factor)
                pt.position = new_pos

                # Also smooth radius
                prev_r = points[i - 1].radius
                next_r = points[i + 1].radius
                pt.radius = pt.radius * (1 - factor) + (prev_r + next_r) / 2.0 * factor

                smoothed = True

    return smoothed


def on_gp_smooth_start(_, event_name, event):
    global _is_smoothing, _smoothed_any

    disable_bounds_check()
    _is_smoothing = True
    _smoothed_any = False


def on_gp_smooth(_, event_name, event):
    global _smoothed_any

    if not _is_smoothing:
        return

    try:
        gp_obj = get_gp_object()
        if gp_obj is None:
            return

        drawing = get_active_drawing(gp_obj)
        if drawing is None or len(drawing.strokes) == 0:
            return

        world_pos = Vector(event.position)
        cursor_size = settings.get("gp.default_cursor_size", 0.01)
        smooth_radius = cursor_size * xr_session.viewer_scale * 3.0  # wider than cursor

        if _smooth_strokes_near_cursor(drawing, gp_obj, world_pos, smooth_radius, factor=0.3):
            _smoothed_any = True

    except Exception as e:
        log.error("[GP Smooth] Error: {}".format(e))


def on_gp_smooth_end(_, event_name, event):
    global _is_smoothing, _smoothed_any

    enable_bounds_check()

    if _smoothed_any:
        bpy.ops.ed.undo_push(message="GP smooth")
        apply_haptic_feedback(hand="main", type="TINY_STRONG")

    _is_smoothing = False
    _smoothed_any = False


def enable_tool():
    root.add_event_listener("trigger_main_start", on_gp_smooth_start)
    root.add_event_listener("trigger_main_press", on_gp_smooth)
    root.add_event_listener("trigger_main_end", on_gp_smooth_end)


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_gp_smooth_start)
    root.remove_event_listener("trigger_main_press", on_gp_smooth)
    root.remove_event_listener("trigger_main_end", on_gp_smooth_end)
