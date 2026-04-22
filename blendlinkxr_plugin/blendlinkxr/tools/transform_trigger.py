import bpy
from bpy.types import Object
from bmesh.types import BMVert, BMEdge, BMFace
from bl_xr import root
from bl_xr.utils import filter_event_by_buttons, is_within_fov, get_bmesh
from math import radians

import time
import logging

from ..settings_manager import settings
from ..utils import set_select_state_all, set_select_state, log, desktop_viewport
from ..utils import enable_bounds_check, disable_bounds_check

from .transform_common import (
    transform_state as T,
    get_selected_elements,
    pre_process_edit_bones,
    pre_process_pose_bones,
    dispatch_event,
    on_transform_object as on_transform_object_orig,
    on_transform_edit_curve,
    on_transform_edit_mesh,
    on_transform_edit_armature,
    on_transform_pose_armature,
    on_joystick_vertical,
    is_transform_allowed,
    constrain_for_gizmo,
    on_grab_start,
    on_grab_end,
)

is_transform_dragging = False
trigger_press_start_time = {}  # trigger_name -> seconds


def on_transform_drag_start(self, event_name, event):
    global is_transform_dragging
    if self != event.targets[0]:
        return

    ob = T["object_to_transform"]
    if not is_transform_allowed(ob, event):
        return

    if ob.hide_select:
        log.debug("Skipping transform since the object is not selectable!")
        return

    if (
        settings["transform.check_for_fov"]
        and not T["has_transformed"]
        and not is_within_fov(event.pivot_position, radians(45))
    ):
        log.debug("Skipping transform since it is outside the FOV!")
        return

    if ob.mode in ("EDIT", "POSE") and event.sub_targets is None:
        return

    disable_bounds_check()

    event.stop_propagation = True
    event.stop_propagation_immediate = True
    T["is_transforming"] = True
    T["is_transforming_from_grab"] = not hasattr(event, "is_handle_drag")

    T["lock_bone_position"] = False

    if settings["gizmo.transform_handles.type"]:
        T["transform_gizmo"] = root.q("#transform_gizmo")

    trigger_alt_start_time = trigger_press_start_time.get("trigger_alt")
    trigger_main_start_time = trigger_press_start_time.get("trigger_main")
    alt_trigger_debounce_time = settings["transform.alt_trigger_debounce_time"]
    if (
        trigger_alt_start_time is not None
        and trigger_main_start_time > trigger_alt_start_time + alt_trigger_debounce_time
    ):
        log.error(
            "Ignoring transform drag because the main trigger was pressed after the alt trigger, "
            + "beyond the threshold alt debounce time! "
            + f"trigger_main_start_time: {trigger_main_start_time}, trigger_alt_start_time: {trigger_alt_start_time}, "
            + f"alt_trigger_debounce_time: {alt_trigger_debounce_time}"
        )
        return

    is_transform_dragging = True

    T["context_override"] = desktop_viewport.temp_override()

    if ob.type == "MESH" and ob.mode == "EDIT" and settings["edit.perform_extrude"]:
        set_select_state_all(False)
        set_select_state(T["transform_elements"], True)

        bpy.ops.mesh.extrude_context()

        T["transform_elements"] = T["preselected_targets"] = get_selected_elements(active_ob=ob)

    # now select the elements that we'll transform
    set_select_state(T["preselected_targets"], False)
    set_select_state(T["transform_elements"], True)

    # convert bmesh element indices to actual vertex indices
    if ob.type == "MESH" and ob.mode == "EDIT" and len(T["transform_elements"]) > 0:
        bm = get_bmesh()
        el_type = list(T["transform_elements"])[0][1]
        if el_type == BMEdge:
            T["transform_elements"] = {bm.edges[i] for i, _ in T["transform_elements"]}
            T["transform_elements"] = {(v.index, BMVert) for e in T["transform_elements"] for v in e.verts}
        elif el_type == BMFace:
            T["transform_elements"] = {bm.faces[i] for i, _ in T["transform_elements"]}
            T["transform_elements"] = {(v.index, BMVert) for e in T["transform_elements"] for v in e.verts}

    dispatch_event(ob, "fb.transform_start", event)

    on_transform_drag(ob, event_name, event)


def on_transform_drag(self, event_name, event):
    if self != event.targets[0]:
        return

    ob = T["object_to_transform"]
    if not T["is_transforming"]:
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Unexpected transform_drag! Ignoring because T['is_transforming'] is False.")
        return

    if not is_transform_allowed(ob, event):
        return

    event.stop_propagation = True
    event.stop_propagation_immediate = True

    if not is_transform_dragging:
        return

    constrain_for_gizmo(ob, event)

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"TRANSFORMING {ob} by {event.pose_delta} pivot: {event.pivot_position}")

    T["has_transformed"] = True

    if ob.mode == "OBJECT":
        on_transform_object(ob, event_name, event)
    elif ob.mode == "EDIT":
        if ob.type == "CURVE":
            on_transform_edit_curve(ob, event_name, event)
        elif ob.type == "MESH":
            on_transform_edit_mesh(ob, event_name, event)
        elif ob.type == "ARMATURE":
            on_transform_edit_armature(ob, event_name, event)
    elif ob.mode == "POSE":
        if ob.type == "ARMATURE":
            on_transform_pose_armature(ob, event_name, event)

    dispatch_event(self, "fb.transform", event)


def on_transform_drag_end(self, event_name, event):
    global is_transform_dragging
    if self != event.targets[0]:
        return

    ob = T["object_to_transform"]

    if not T["is_transforming"]:
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Unexpected transform_drag_end! Ignoring because T['is_transforming'] is False.")
        return

    if not is_transform_allowed(ob, event):
        return

    enable_bounds_check()

    T["is_transforming"] = False
    T["is_transforming_from_grab"] = False
    T["transform_gizmo"] = None
    T["lock_bone_position"] = False
    event.stop_propagation = True
    event.stop_propagation_immediate = True

    if T["has_transformed"] and not T["has_cloned"]:
        bpy.ops.ed.undo_push(message="transform")
        log.debug("CREATED UNDO EVENT for transform")

        bpy.ops.transform.translate()

        dispatch_event(ob, "fb.transform_end", event)

    is_transform_dragging = False
    T["object_to_transform"] = None
    T["has_transformed"] = False
    T["has_cloned"] = False

    if ob.type == "MESH" and ob.mode == "EDIT" and settings["edit.perform_extrude"]:
        get_bmesh(skip_cache=True)  # refresh the bmesh and bvh


def on_transform_object(self, event_name, event):
    on_transform_object_orig(self, event_name, event)

    if len(T["transform_elements"]) > 0:
        bpy.context.view_layer.objects.active = list(T["transform_elements"])[-1]


def on_trigger_press_start(self, event_name, event):
    trigger_press_start_time[event.button_name] = time.time()


def on_trigger_press_end(self, event_name, event):
    trigger_press_start_time[event.button_name] = None


def enable_tool():
    # enable_bounds_check()

    Object.add_event_listener(
        "drag_start", on_transform_drag_start, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )
    Object.add_event_listener(
        "drag", on_transform_drag, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )
    Object.add_event_listener(
        "drag_end", on_transform_drag_end, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )

    Object.add_event_listener("trigger_main_start", on_grab_start)
    Object.add_event_listener("trigger_main_end", on_grab_end)

    Object.add_event_listener("trigger_alt_start", on_trigger_press_start)
    Object.add_event_listener("trigger_alt_end", on_trigger_press_end)
    Object.add_event_listener("trigger_main_start", on_trigger_press_start)
    Object.add_event_listener("trigger_main_end", on_trigger_press_end)
    root.add_event_listener("trigger_alt_start", on_trigger_press_start)
    root.add_event_listener("trigger_alt_end", on_trigger_press_end)
    root.add_event_listener("trigger_main_start", on_trigger_press_start)
    root.add_event_listener("trigger_main_end", on_trigger_press_end)

    root.add_event_listener("joystick_y_main_press", on_joystick_vertical)


def disable_tool():
    # disable_bounds_check()

    Object.remove_event_listener("drag_start", on_transform_drag_start)
    Object.remove_event_listener("drag", on_transform_drag)
    Object.remove_event_listener("drag_end", on_transform_drag_end)

    Object.remove_event_listener("trigger_main_start", on_grab_start)
    Object.remove_event_listener("trigger_main_end", on_grab_end)

    Object.remove_event_listener("trigger_alt_start", on_trigger_press_start)
    Object.remove_event_listener("trigger_alt_end", on_trigger_press_end)
    Object.remove_event_listener("trigger_main_start", on_trigger_press_start)
    Object.remove_event_listener("trigger_main_end", on_trigger_press_end)
    root.remove_event_listener("trigger_alt_start", on_trigger_press_start)
    root.remove_event_listener("trigger_alt_end", on_trigger_press_end)
    root.remove_event_listener("trigger_main_start", on_trigger_press_start)
    root.remove_event_listener("trigger_main_end", on_trigger_press_end)

    root.remove_event_listener("joystick_y_main_press", on_joystick_vertical)
