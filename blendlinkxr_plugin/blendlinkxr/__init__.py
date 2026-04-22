# set up file logging as early as possible, with zero non-stdlib/non-blender dependencies
from .log_manager import LOG_FILE, init_logging as _init_logging

_init_logging()

# initialize the rest of blendlinkxr after logging
from .settings_manager import settings, reset_settings, MODULE_ID

# Import and init logging first, and then import settings, and then import the rest. This order is important.

from bl_xr import root, xr_session

from .tools import enable_tool, disable_tool
from .gizmos import enable_gizmo, disable_gizmo, toggle_gizmo
from .undo_redo import undo, redo
from .updater import check_update

import bpy
from bpy.app.handlers import persistent

_loaded = False


def on_xr_start(self, event_name, event):
    from . import tools
    from .utils import set_default_cursor, log
    from .ui import reset_viewer_settings, enable_xr_ui
    from .updater import check_update
    from .settings_manager import _get_preferences

    prefs = _get_preferences()

    enable_xr_ui()

    if tools.active_tool is None:
        enable_tool("draw.stroke")  # default tool
        set_default_cursor("pen")

    # temp hack for testing
    from .tools.transform_trigger import (
        enable_tool as enable_trigger_transform,
        disable_tool as disable_trigger_transform,
    )
    from .tools.transform import (
        enable_tool as enable_squeeze_transform,
        disable_tool as disable_squeeze_transform,
    )
    from .tools.clone import enable_tool as enable_clone, disable_tool as disable_clone
    from bl_xr import intersections

    log.info(f"Transform button: {settings['transform.grab_button']}. Allow squeeze: {intersections.allow_squeeze}")
    if settings["transform.grab_button"] == "squeeze":
        if not intersections.allow_squeeze:
            disable_trigger_transform()
            enable_squeeze_transform()
            enable_clone()

        intersections.allow_squeeze = True
    else:
        if intersections.allow_squeeze:
            disable_squeeze_transform()
            disable_clone()

            if tools.active_tool == "select":
                enable_trigger_transform()
                enable_clone()

        intersections.allow_squeeze = False
    # end of temp hack for testing

    # hack for cable manager (demo)
    if prefs.demo_cable_manager_enabled:
        if "cable_manager" in gizmos.active_gizmos:
            disable_gizmo("cable_manager")
        enable_gizmo("cable_manager")

    check_update(ref="xr_start")

    reset_viewer_settings()

    # Enable MX Ink dock state tracking
    _enable_mx_ink_dock_tracking()

    # Enable MX Ink pen model (replaces right controller visual)
    enable_gizmo("mx_ink_pen_model")


def on_xr_end(self, event_name, event):
    from .ui import reset_viewer_settings, disable_xr_ui

    from bl_xr.utils import log

    # temp hack
    from .tools.transform_trigger import disable_tool as disable_trigger_transform
    from .tools.transform import disable_tool as disable_squeeze_transform
    from .tools.clone import disable_tool as disable_clone
    from bl_xr import intersections

    log.info(f"Transform button: {settings['transform.grab_button']}. Allow squeeze: {intersections.allow_squeeze}")
    if settings["transform.grab_button"] == "squeeze":
        if intersections.allow_squeeze:
            disable_squeeze_transform()
            disable_clone()
    else:
        if tools.active_tool == "select":
            disable_trigger_transform()
            disable_clone()

    intersections.allow_squeeze = False  # clean up, and revert this back to bl_xr factory default
    # end of temp hack

    disable_xr_ui()

    reset_viewer_settings()

    # Disable MX Ink dock state tracking
    _disable_mx_ink_dock_tracking()

    # Disable MX Ink pen model
    disable_gizmo("mx_ink_pen_model")


# ---------------------------------------------------------------------------
# MX Ink dock state & combo tracking
# ---------------------------------------------------------------------------
# When the MX Ink stylus is placed in its dock, we suppress trigger events
# so the user doesn't accidentally draw/select/erase while putting the pen
# down.  The dock state is exposed as settings["mx_ink.docked"] and an
# fb.mx_ink_dock_change event is dispatched on transitions.
#
# Tip force is tracked continuously and exposed as settings["mx_ink.tip_force"]
# so drawing tools can use it for pressure-sensitive stroke width even though
# the trigger (middle cluster force) is an analog button.
#
# Combo system for missing right thumbstick:
#   Back click HOLD + middle force value → cursor/brush size adjust
#   Front click HOLD + middle force value → proportional edit radius /
#                                           keyframe frame nav (context)
#
# These combos intercept the trigger (middle force) events when a modifier
# button is held, redirecting the analog value to resize/navigate instead
# of drawing.

_mx_ink_dock_listeners_active = False

# Combo state tracking
_mx_ink_back_held = False    # back click (A button / quicktools) is held
_mx_ink_front_held = False   # front click (squeeze / grab) is held
_mx_ink_combo_active = False # a combo consumed the trigger, suppress tool action


def _on_mx_ink_dock_start(self, event_name, event):
    """MX Ink was placed in the dock."""
    settings["mx_ink.docked"] = True
    root.dispatch_event("fb.mx_ink_dock_change", {"docked": True})
    from .utils import log
    log.info("[MX Ink] Stylus docked — input suppressed")


def _on_mx_ink_dock_end(self, event_name, event):
    """MX Ink was removed from the dock."""
    settings["mx_ink.docked"] = False
    root.dispatch_event("fb.mx_ink_dock_change", {"docked": False})
    from .utils import log
    log.info("[MX Ink] Stylus undocked — input active")


def _on_mx_ink_front_double_tap(self, event_name, event):
    """Front button double-tap on MX Ink — mapped to undo."""
    undo()


def _on_mx_ink_back_double_tap(self, event_name, event):
    """Back button double-tap on MX Ink — mapped to redo."""
    redo()


def _on_mx_ink_tip_force_update(self, event_name, event):
    """Track tip force continuously for pressure-sensitive drawing."""
    settings["mx_ink.tip_force"] = event.value


def _on_mx_ink_tip_force_end(self, event_name, event):
    """Tip lifted — reset force to 0."""
    settings["mx_ink.tip_force"] = 0.0


# --- Combo modifier tracking ---
# These track when back click (A button) or front click (squeeze) are held
# so we can intercept trigger events for cursor resize / keyframe nav.

def _on_mx_ink_back_btn_start(self, event_name, event):
    """Back click pressed — start tracking for combo."""
    global _mx_ink_back_held
    _mx_ink_back_held = True


def _on_mx_ink_back_btn_end(self, event_name, event):
    """Back click released — end combo tracking."""
    global _mx_ink_back_held, _mx_ink_combo_active
    _mx_ink_back_held = False
    _mx_ink_combo_active = False


def _on_mx_ink_front_btn_start(self, event_name, event):
    """Front click pressed — start tracking for combo."""
    global _mx_ink_front_held
    _mx_ink_front_held = True


def _on_mx_ink_front_btn_end(self, event_name, event):
    """Front click released — end combo tracking."""
    global _mx_ink_front_held, _mx_ink_combo_active
    _mx_ink_front_held = False
    _mx_ink_combo_active = False


def _on_mx_ink_trigger_for_combo(self, event_name, event):
    """Intercept trigger (middle force) when a modifier button is held.

    Back click + middle force → cursor/brush size (replaces joystick_x_main)
    Front click + middle force → keyframe nav or prop edit radius (context)
    """
    global _mx_ink_combo_active

    if not (_mx_ink_back_held or _mx_ink_front_held):
        return  # no modifier held, let normal trigger flow through

    _mx_ink_combo_active = True

    value = event.value  # 0.0–1.0 analog from middle cluster force

    if _mx_ink_back_held:
        # Back click + middle force → cursor/brush resize
        # Map force to a resize delta: center (0.5) = no change,
        # >0.5 = bigger, <0.5 = smaller.  Since force is 0–1 and
        # starts from 0, we treat any force as "make bigger" and
        # use the absence of force (release) as the end signal.
        # Simpler: force value directly drives resize speed.
        _do_cursor_resize(value)

    elif _mx_ink_front_held:
        # Front click + middle force → keyframe nav / prop edit radius
        _do_context_action(value)


def _on_mx_ink_trigger_combo_end(self, event_name, event):
    """Trigger released while combo was active — clean up."""
    global _mx_ink_combo_active
    if _mx_ink_combo_active:
        _do_cursor_resize_end()
        _mx_ink_combo_active = False


def _do_cursor_resize(force_value):
    """Drive cursor resize using middle cluster force value.

    Force 0–1 maps to resize: positive = grow cursor.
    We scale it to match the joystick range (-1 to +1) that the
    cursor gizmo expects.
    """
    try:
        cursor = root.q("#cursor_main")
        if cursor is None:
            return

        from . import gizmos
        from bl_xr import ControllerEvent

        if "joystick_for_keyframe" in gizmos.active_gizmos:
            return  # keyframe tool handles its own input

        # Map force (0–1) to resize amount.
        # Light force = grow slowly, full force = grow fast.
        # To shrink: release back click, re-hold, then use without force
        # (or we can use negative mapping later).
        # For now: force > 0 = grow.  This matches the joystick-right behavior.
        resize_amt = force_value

        speed = settings["gizmo.cursor.resize_speed"]
        min_size = settings["gizmo.cursor.min_size"]
        max_size = settings["gizmo.cursor.max_size"]
        from bl_xr.utils import lerp, clamp

        curr_size = cursor.size
        size_t = (curr_size - min_size) / (max_size - min_size)
        speed_mul = lerp(
            settings["gizmo.cursor.resize_speed_small_multiplier"],
            settings["gizmo.cursor.resize_speed_large_multiplier"],
            size_t,
        )
        d = resize_amt * speed * speed_mul
        new_size = clamp(curr_size + d, min_size, max_size)
        cursor.size = new_size

        # Save to settings
        from . import tools as tools_module
        if tools_module.active_tool in cursor.CURSOR_DEFAULTS_KEYS:
            size_key, _ = cursor.CURSOR_DEFAULTS_KEYS[tools_module.active_tool]
            settings[size_key] = cursor.size
    except Exception:
        pass


def _do_cursor_resize_end():
    """Clean up after combo-driven cursor resize."""
    pass


def _do_context_action(force_value):
    """Front click + middle force: context-dependent action.

    - In Keyframe tool: navigate frames (force = advance speed)
    - In Edit mode with proportional editing: resize influence sphere
    - Otherwise: also cursor resize (shrink direction)
    """
    import bpy

    try:
        from . import gizmos

        # Keyframe frame navigation
        if "joystick_for_keyframe" in gizmos.active_gizmos:
            # Advance frames proportional to force
            if force_value > 0.3:
                frame = bpy.context.scene.frame_current
                bpy.context.scene.frame_set(frame + 1)
            return

        # Proportional edit radius
        ob = bpy.context.view_layer.objects.active
        if ob and ob.mode == "EDIT" and ob.type == "MESH":
            tool_settings = bpy.context.scene.tool_settings
            if tool_settings.use_proportional_edit:
                p_attr = "proportional_distance" if hasattr(tool_settings, "proportional_distance") else "proportional_size"
                curr = getattr(tool_settings, p_attr)
                delta = force_value * 0.005
                setattr(tool_settings, p_attr, max(0.01, curr + delta))
                return

        # Fallback: cursor resize in shrink direction
        _do_cursor_resize(-force_value)
    except Exception:
        pass


def _enable_mx_ink_dock_tracking():
    global _mx_ink_dock_listeners_active

    if _mx_ink_dock_listeners_active:
        return

    settings["mx_ink.docked"] = False
    settings["mx_ink.tip_force"] = 0.0

    # Dock state
    root.add_event_listener("mx_ink_dock_state_main_start", _on_mx_ink_dock_start)
    root.add_event_listener("mx_ink_dock_state_main_end", _on_mx_ink_dock_end)

    # Double-tap shortcuts: front = undo, back = redo (no joystick on pen)
    root.add_event_listener("mx_ink_front_double_tap_main_start", _on_mx_ink_front_double_tap)
    root.add_event_listener("mx_ink_back_double_tap_main_start", _on_mx_ink_back_double_tap)

    # Tip force tracking for pressure-sensitive drawing
    root.add_event_listener("mx_ink_tip_force_main_start", _on_mx_ink_tip_force_update)
    root.add_event_listener("mx_ink_tip_force_main_press", _on_mx_ink_tip_force_update)
    root.add_event_listener("mx_ink_tip_force_main_end", _on_mx_ink_tip_force_end)

    # Combo modifier tracking (back click = A button, front click = squeeze)
    root.add_event_listener("button_a_main_start", _on_mx_ink_back_btn_start)
    root.add_event_listener("button_a_main_end", _on_mx_ink_back_btn_end)
    root.add_event_listener("squeeze_main_start", _on_mx_ink_front_btn_start)
    root.add_event_listener("squeeze_main_end", _on_mx_ink_front_btn_end)

    # Trigger combo interception (middle force while modifier held)
    root.add_event_listener("trigger_main_press", _on_mx_ink_trigger_for_combo)
    root.add_event_listener("trigger_main_end", _on_mx_ink_trigger_combo_end)

    _mx_ink_dock_listeners_active = True


def _disable_mx_ink_dock_tracking():
    global _mx_ink_dock_listeners_active

    if not _mx_ink_dock_listeners_active:
        return

    root.remove_event_listener("mx_ink_dock_state_main_start", _on_mx_ink_dock_start)
    root.remove_event_listener("mx_ink_dock_state_main_end", _on_mx_ink_dock_end)
    root.remove_event_listener("mx_ink_front_double_tap_main_start", _on_mx_ink_front_double_tap)
    root.remove_event_listener("mx_ink_back_double_tap_main_start", _on_mx_ink_back_double_tap)
    root.remove_event_listener("mx_ink_tip_force_main_start", _on_mx_ink_tip_force_update)
    root.remove_event_listener("mx_ink_tip_force_main_press", _on_mx_ink_tip_force_update)
    root.remove_event_listener("mx_ink_tip_force_main_end", _on_mx_ink_tip_force_end)
    root.remove_event_listener("button_a_main_start", _on_mx_ink_back_btn_start)
    root.remove_event_listener("button_a_main_end", _on_mx_ink_back_btn_end)
    root.remove_event_listener("squeeze_main_start", _on_mx_ink_front_btn_start)
    root.remove_event_listener("squeeze_main_end", _on_mx_ink_front_btn_end)
    root.remove_event_listener("trigger_main_press", _on_mx_ink_trigger_for_combo)
    root.remove_event_listener("trigger_main_end", _on_mx_ink_trigger_combo_end)

    _mx_ink_dock_listeners_active = False


@persistent
def on_file_load(scene):
    global _loaded

    from bl_xr import root

    if not _loaded:
        _loaded = True
        root.dispatch_event("fb.load", None)

    root.dispatch_event("fb.file_load", scene)


def on_unload():
    from bl_xr import root

    root.dispatch_event("fb.unload", None)


def register():
    import bpy
    from . import settings_manager

    settings_manager.register()

    bpy.app.handlers.load_post.append(on_file_load)

    from .utils import log

    try:
        from bl_xr import Image
        from os import path

        from .ui import enable_desktop_ui

        from .utils import enable_bounds_check, disable_bounds_check, get_device_info, watch_for_blender_mode_changes
        from .utils import misc_utils
        from .navigate import enable as enable_navigation
        from .undo_redo import enable as enable_undo_redo
        from .tools.transform import enable_tool as enable_object_transform
        from .tools.clone import enable_tool as enable_clone
        from .gizmos import enable_gizmo

        # setup the base directory for images
        Image.base_dir = path.abspath(path.join(path.dirname(__file__), ".."))
        log.debug(f"Setup image base directory to {Image.base_dir}")

        # handle the button press event sent by the Operator in ui/desktop_panels.py
        root.add_event_listener("fb.xr_start", on_xr_start)
        root.add_event_listener("fb.xr_end", on_xr_end)

        enable_bounds_check()

        enable_desktop_ui()
        enable_navigation()
        # enable_object_transform()
        # enable_clone()
        enable_undo_redo()
        enable_gizmo("preserve_view_across_restarts")
        enable_gizmo("auto_keyframe_transforms")
        enable_gizmo("see_through_pose_bones")
        enable_gizmo("select_switch")
        enable_gizmo("proportional_edit_cursor")
        enable_gizmo("auto_record_events")
        enable_gizmo("text_editor_ux_improvements")

        if not bpy.app.background:
            log.info(f"Blender: {bpy.app.version}")
            log.info(f"Device Info: {get_device_info()}")

        watch_for_blender_mode_changes()

        settings_manager.stop_syncing = False
        misc_utils.stop_checking_mode = False
    except Exception as e:
        import traceback

        # Blender logs to stdout. Log to BlendLink's file logger as well
        log.critical(f"Error while registering BlendLink: {traceback.format_exc()}")
        raise e


def unregister():
    from . import settings_manager

    settings_manager.unregister()

    if on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load)

    on_unload()

    from .utils import log

    try:
        from .ui import disable_desktop_ui

        from .navigate import disable as disable_navigation
        from .undo_redo import disable as disable_undo_redo
        from .tools.transform import disable_tool as disable_object_transform
        from .tools.clone import disable_tool as disable_clone
        from . import settings_manager
        from .utils import misc_utils

        root.remove_event_listener("fb.xr_start", on_xr_start)
        root.remove_event_listener("fb.xr_end", on_xr_end)

        disable_desktop_ui()
        disable_navigation()
        # disable_object_transform()
        # disable_clone()
        disable_undo_redo()
        disable_gizmo("preserve_view_across_restarts")
        disable_gizmo("auto_keyframe_transforms")
        disable_gizmo("see_through_pose_bones")
        disable_gizmo("select_switch")
        disable_gizmo("proportional_edit_cursor")
        disable_gizmo("auto_record_events")
        disable_gizmo("text_editor_ux_improvements")

        settings_manager.stop_syncing = True
        misc_utils.stop_checking_mode = True
    except Exception as e:
        import traceback

        # Blender logs to stdout. Log to BlendLink's file logger as well
        log.critical(f"Error while un-registering BlendLink: {traceback.format_exc()}")
        raise e
