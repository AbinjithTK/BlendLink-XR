import bpy

from bl_xr import root, xr_session
from bl_xr.utils.debug import event_recording_replay
from bl_xr.utils.test import apply_xr_session_override, reset_xr_session_override_values, remove_xr_session_override
from mathutils import Vector, Quaternion

orig_controller_main_aim_position_getter = None
orig_controller_main_aim_rotation_getter = None
orig_controller_alt_aim_position_getter = None
orig_controller_alt_aim_rotation_getter = None
orig_controller_main_grip_position_getter = None
orig_controller_main_grip_rotation_getter = None
orig_controller_alt_grip_position_getter = None
orig_controller_alt_grip_rotation_getter = None


def start_fake_vr():
    apply_xr_session_override()
    apply_xr_controller_override()
    start_vr()

    xr_session._is_fake_vr = True


def stop_fake_vr():
    xr_session._is_fake_vr = False

    stop_vr()
    remove_xr_controller_override()
    remove_xr_session_override()


def replay_events():
    import tempfile
    from os import path
    from blendlinkxr.utils import log
    import logging

    load_file = path.join(tempfile.gettempdir(), "events.txt")

    from blendlinkxr import settings

    settings["app.debug.auto_record_events"] = False
    settings["view.show_main_menu"] = True
    settings["view.show_info_panel"] = True

    log.setLevel(logging.DEBUG)

    start_fake_vr()

    log.debug(f"Replaying {load_file}")

    try:
        event_recording_replay(load_file)
    finally:
        stop_fake_vr()


def start_vr():
    from blendlinkxr.utils import desktop_viewport

    screen = bpy.context.window_manager.windows[0].screen
    desktop_viewport._area = next((area for area in screen.areas if area.type == "VIEW_3D"), None)

    root.dispatch_event("fb.xr_start", None)  # simulate the "Start VR" button click
    root.dispatch_event("xr_start", bpy.context)  # dispatch the xr_start event
    xr_session.is_running = True


def stop_vr():
    root.dispatch_event("fb.xr_end", None)  # simulate the "Start VR" button click
    xr_session.is_running = False


def apply_xr_controller_override():
    global orig_controller_main_aim_position_getter
    global orig_controller_main_aim_rotation_getter
    global orig_controller_alt_aim_position_getter
    global orig_controller_alt_aim_rotation_getter
    global orig_controller_main_grip_position_getter
    global orig_controller_main_grip_rotation_getter
    global orig_controller_alt_grip_position_getter
    global orig_controller_alt_grip_rotation_getter

    orig_controller_main_aim_position_getter = type(xr_session).controller_main_aim_position.__get__
    orig_controller_main_aim_rotation_getter = type(xr_session).controller_main_aim_rotation.__get__
    orig_controller_alt_aim_position_getter = type(xr_session).controller_alt_aim_position.__get__
    orig_controller_alt_aim_rotation_getter = type(xr_session).controller_alt_aim_rotation.__get__
    orig_controller_main_grip_position_getter = type(xr_session).controller_main_grip_position.__get__
    orig_controller_main_grip_rotation_getter = type(xr_session).controller_main_grip_rotation.__get__
    orig_controller_alt_grip_position_getter = type(xr_session).controller_alt_grip_position.__get__
    orig_controller_alt_grip_rotation_getter = type(xr_session).controller_alt_grip_rotation.__get__

    reset_xr_controller_override_values()


def reset_xr_controller_override_values():
    type(xr_session).controller_main_aim_position = Vector()
    type(xr_session).controller_main_aim_rotation = Quaternion()
    type(xr_session).controller_alt_aim_position = Vector()
    type(xr_session).controller_alt_aim_rotation = Quaternion()
    type(xr_session).controller_main_grip_position = Vector()
    type(xr_session).controller_main_grip_rotation = Quaternion()
    type(xr_session).controller_alt_grip_position = Vector()
    type(xr_session).controller_alt_grip_rotation = Quaternion()

    xr_session.controller_main_aim_position = Vector()
    xr_session.controller_main_aim_rotation = Quaternion()
    xr_session.controller_alt_aim_position = Vector()
    xr_session.controller_alt_aim_rotation = Quaternion()
    xr_session.controller_main_grip_position = Vector()
    xr_session.controller_main_grip_rotation = Quaternion()
    xr_session.controller_alt_grip_position = Vector()
    xr_session.controller_alt_grip_rotation = Quaternion()


def remove_xr_controller_override():
    type(xr_session).controller_main_aim_position = property(orig_controller_main_aim_position_getter)
    type(xr_session).controller_main_aim_rotation = property(orig_controller_main_aim_rotation_getter)
    type(xr_session).controller_alt_aim_position = property(orig_controller_alt_aim_position_getter)
    type(xr_session).controller_alt_aim_rotation = property(orig_controller_alt_aim_rotation_getter)
    type(xr_session).controller_main_grip_position = property(orig_controller_main_grip_position_getter)
    type(xr_session).controller_main_grip_rotation = property(orig_controller_main_grip_rotation_getter)
    type(xr_session).controller_alt_grip_position = property(orig_controller_alt_grip_position_getter)
    type(xr_session).controller_alt_grip_rotation = property(orig_controller_alt_grip_rotation_getter)
