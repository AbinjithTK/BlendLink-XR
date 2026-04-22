# SPDX-License-Identifier: GPL-2.0-or-later

"""GP v3 stroke eraser — removes strokes near the cursor."""

import bpy

from bl_xr import root, xr_session
from bl_xr.utils import apply_haptic_feedback
from mathutils import Vector

from ..settings_manager import settings
from ..utils import log
from ..utils import enable_bounds_check, disable_bounds_check
from .gp_utils import get_gp_object, get_active_drawing, world_to_local, local_to_world

_is_erasing = False
_erased_any = False


def _find_strokes_near_cursor(drawing, gp_obj, world_pos, radius):
    """Find stroke indices whose points are within radius of world_pos."""
    local_pos = world_to_local(gp_obj, world_pos)
    local_radius = radius / max(gp_obj.matrix_world.to_scale())

    indices_to_remove = []
    for i, stroke in enumerate(drawing.strokes):
        for pt in stroke.points:
            dist = (Vector(pt.position) - local_pos).length
            if dist < local_radius:
                indices_to_remove.append(i)
                break  # one hit is enough to mark the stroke

    return indices_to_remove


def on_gp_erase_start(_, event_name, event):
    global _is_erasing, _erased_any

    disable_bounds_check()
    _is_erasing = True
    _erased_any = False


def on_gp_erase(_, event_name, event):
    global _erased_any

    if not _is_erasing:
        return

    try:
        gp_obj = get_gp_object()
        if gp_obj is None:
            return

        drawing = get_active_drawing(gp_obj)
        if drawing is None or len(drawing.strokes) == 0:
            return

        world_pos = Vector(event.position)
        cursor_size = settings.get("erase.default_cursor_size", 0.01)
        erase_radius = cursor_size * xr_session.viewer_scale

        indices = _find_strokes_near_cursor(drawing, gp_obj, world_pos, erase_radius)
        if indices:
            drawing.remove_strokes(indices=indices)
            _erased_any = True
            apply_haptic_feedback(hand="main", type="TINY_LIGHT")

    except Exception as e:
        log.error("[GP Erase] Error: {}".format(e))


def on_gp_erase_end(_, event_name, event):
    global _is_erasing, _erased_any

    enable_bounds_check()

    if _erased_any:
        bpy.ops.ed.undo_push(message="GP erase")
        apply_haptic_feedback(hand="main", type="SHORT_LIGHT")

    _is_erasing = False
    _erased_any = False


def enable_tool():
    root.add_event_listener("trigger_main_start", on_gp_erase_start)
    root.add_event_listener("trigger_main_press", on_gp_erase)
    root.add_event_listener("trigger_main_end", on_gp_erase_end)


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_gp_erase_start)
    root.remove_event_listener("trigger_main_press", on_gp_erase)
    root.remove_event_listener("trigger_main_end", on_gp_erase_end)
