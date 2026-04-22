def event_recording_start():
    import bpy
    import bl_input
    import logging
    from bl_xr import root, request_animation_frame
    from bl_xr.ui import renderer
    from bl_xr.utils import log
    import tempfile
    from os import path

    log.setLevel(logging.DEBUG)

    log.debug("Starting recording..")

    def get_device_entries():
        headset_entry = _get_headset_pose()
        right_controller_entry = _get_xr_controller_pose("right")
        left_controller_entry = _get_xr_controller_pose("left")

        return [headset_entry, right_controller_entry, left_controller_entry]

    def record_entries(entries):
        for entry in entries:
            log.debug(f"Recording event {len(event_recording_start.recorded_events)}")
            log.debug(f"entry: {entry}")
            event_recording_start.recorded_events.append(entry)

    def on_event(event_type, event_data):
        entries = get_device_entries()

        event_entry = _get_entry_from_recorded_events(event_type, event_data)
        entries.append(event_entry)

        record_entries(entries)

        event_recording_start.orig_event_callback(event_type, event_data)

    def on_update(node):
        if node == root:
            entries = get_device_entries()

            update_entry = ["update"]
            entries.append(update_entry)

            record_entries(entries)

        event_recording_start.orig_update_callback(node)

    event_recording_start.orig_event_callback = bl_input.event_callback
    event_recording_start.orig_update_callback = renderer.update
    bl_input.event_callback = on_event
    renderer.update = on_update

    blend_file = path.join(tempfile.gettempdir(), "events.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_file, check_existing=False, compress=True)

    event_recording_start.recorded_events = [
        ["blender_version", bpy.app.version],
        ["blender_file", blend_file],
    ]

    request_animation_frame(lambda ts: event_recording_start.recorded_events.append(_get_nav_pose()))


def event_recording_stop():
    import json
    import bl_input
    from bl_xr.ui import renderer
    from bl_xr.utils import log
    import tempfile
    from os import path

    if not hasattr(event_recording_start, "orig_event_callback"):
        return

    log.debug("Stopping recording..")

    entries = event_recording_start.recorded_events

    # validate the entries
    for entry in entries:
        try:
            json.dumps(entry)
        except:
            print(f"Failed JSON serialization: {entry}")

    # save the entries
    save_file = path.join(tempfile.gettempdir(), "events.txt")

    if save_file is None:
        for entry in entries:
            log.debug(json.dumps(entry))
    else:
        with open(save_file, "w") as f:
            json.dump(entries, f)

        log.debug(f"Written the event recording to {save_file}")

    bl_input.event_callback = event_recording_start.orig_event_callback
    renderer.update = event_recording_start.orig_update_callback
    delattr(event_recording_start, "orig_event_callback")
    delattr(event_recording_start, "orig_update_callback")
    delattr(event_recording_start, "recorded_events")


def event_recording_replay(load_file):
    import bpy
    import json
    import bl_input
    import logging
    from bl_xr import root
    from bl_xr.ui import renderer
    from bl_xr.utils import log
    from bl_xr.utils.test import make_bl_event, make_bl_mouse_event, is_equal
    from bl_xr.utils.test import deserialize_xr_action, deserialize_xr_controller_move

    orig_pitched_rotation = getattr(make_bl_event, "pitched_rotation", False)
    make_bl_event.pitched_rotation = False

    on_event = bl_input.event_callback

    log.setLevel(logging.DEBUG)

    try:
        with open(load_file, "r") as f:
            entries = json.load(f)

        for i, entry in enumerate(entries):
            event_type, *fn_args = entry
            log.debug(f"Replaying event {i}")
            log.debug(f"entry: {entry}")

            try:
                if event_type == "blender_version":
                    rec_bl_version = fn_args[0][:-1]
                    bl_version = bpy.app.version[:-1]
                    assert is_equal(rec_bl_version, bl_version), f"{rec_bl_version} != {bl_version}"
                elif event_type == "blender_file":
                    filepath = fn_args[0]
                    if bpy.data.filepath != filepath:
                        raise Exception(f"Need to open: {filepath} to continue!")
                elif event_type == "nav_pose":
                    _set_nav_pose(*fn_args)
                elif event_type == "headset_pose":
                    _set_headset_pose(*fn_args)
                elif event_type == "controller_pose":
                    _set_xr_controller_pose(*fn_args)
                elif event_type == "update":
                    renderer.update(root)
                elif event_type == "XR_ACTION":
                    fn_args = deserialize_xr_action(*fn_args)
                    on_event(event_type, make_bl_event(*fn_args))
                elif event_type == "XR_CONTROLLER_MOVE":
                    fn_args = deserialize_xr_controller_move(*fn_args)
                    on_event(event_type, fn_args + [bpy.context])
                elif event_type == "MOUSEMOVE":
                    on_event(event_type, make_bl_mouse_event(*fn_args))
            except Exception as e:
                log.error(f"Error while replaying entry {i} in {load_file}")
                raise e

            bpy.context.view_layer.update()
    finally:
        make_bl_event.pitched_rotation = orig_pitched_rotation


def _get_entry_from_recorded_events(event_type, event_data):
    from bl_xr.utils import log
    from bl_xr.utils.test import xr_action_from_bl_event, xr_controller_move_from_bl_event, mouse_move_from_bl_event

    fn_args = None
    if event_type == "XR_ACTION":
        fn_args = xr_action_from_bl_event(event_data)
    elif event_type == "XR_CONTROLLER_MOVE":
        fn_args = xr_controller_move_from_bl_event(event_data)
    elif event_type == "MOUSEMOVE":
        fn_args = mouse_move_from_bl_event(event_data)

    return [event_type] + fn_args


def _get_headset_pose():
    from bl_xr import xr_session
    from bl_xr.utils.test import make_tuple

    position = make_tuple(xr_session.viewer_camera_position)
    rotation = make_tuple(xr_session.viewer_camera_rotation)

    return ["headset_pose", position, rotation]


def _set_headset_pose(position, rotation):
    from bl_xr import xr_session
    from mathutils import Vector, Quaternion

    xr_session.viewer_camera_position = Vector(position)
    xr_session.viewer_camera_rotation = Quaternion(rotation)


def _get_nav_pose():
    from bl_xr import xr_session
    from bl_xr.utils.test import make_tuple

    position = make_tuple(xr_session.viewer_location)
    rotation = make_tuple(xr_session.viewer_rotation)
    scale = xr_session.viewer_scale

    return ["nav_pose", position, rotation, scale]


def _set_nav_pose(position, rotation, scale):
    from bl_xr import xr_session
    from mathutils import Vector, Quaternion

    xr_session.viewer_location = Vector(position)
    xr_session.viewer_rotation = Quaternion(rotation)
    xr_session.viewer_scale = scale


def _get_xr_controller_pose(hand):
    from bl_xr import xr_session
    from bl_xr.utils.test import make_tuple as t

    if hand == "right":
        aim_position = xr_session.controller_main_aim_position
        aim_rotation = xr_session.controller_main_aim_rotation
        grip_position = xr_session.controller_main_grip_position
        grip_rotation = xr_session.controller_main_grip_rotation
    elif hand == "left":
        aim_position = xr_session.controller_alt_aim_position
        aim_rotation = xr_session.controller_alt_aim_rotation
        grip_position = xr_session.controller_alt_grip_position
        grip_rotation = xr_session.controller_alt_grip_rotation

    return ["controller_pose", hand, t(aim_position), t(aim_rotation), t(grip_position), t(grip_rotation)]


def _set_xr_controller_pose(hand, aim_position, aim_rotation, grip_position, grip_rotation):
    from bl_xr import xr_session
    from mathutils import Vector, Quaternion

    if hand == "right":
        xr_session.controller_main_aim_position = Vector(aim_position)
        xr_session.controller_main_aim_rotation = Quaternion(aim_rotation)
        xr_session.controller_main_grip_position = Vector(grip_position)
        xr_session.controller_main_grip_rotation = Quaternion(grip_rotation)
    elif hand == "left":
        xr_session.controller_alt_aim_position = Vector(aim_position)
        xr_session.controller_alt_aim_rotation = Quaternion(aim_rotation)
        xr_session.controller_alt_grip_position = Vector(grip_position)
        xr_session.controller_alt_grip_rotation = Quaternion(grip_rotation)
