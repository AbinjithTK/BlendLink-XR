import bpy

import bl_xr
from bl_xr import root, xr_session
from bl_xr import Pose, TwoHandedControllerEvent, DragEvent, ControllerEvent
from bl_xr.utils import filter_event_by_buttons
from mathutils import Vector, Euler, Quaternion
from math import radians

import logging

from .settings_manager import settings
from .utils import log
from .utils import enable_bounds_check, disable_bounds_check

nav_pose = None


# GRAB mode
def on_nav_transform_start(self, event_name, event: DragEvent):
    if settings["world_nav.nav_mode"] != "GRAB":
        return

    global nav_pose

    disable_bounds_check()

    nav_pose = xr_session.viewer_pose

    event = event.clone()
    event.type = "fb.navigate_start"

    root.dispatch_event("fb.navigate_start", event)

    on_nav_transform(self, event_name, event)


def on_nav_transform(self, event_name, event: DragEvent):
    if settings["world_nav.nav_mode"] != "GRAB":
        return

    from bl_xr.events.make_events.controller import input_state

    if nav_pose is None:
        return

    if input_state.get("trigger_main_press"):
        log.debug("Skipping world navigate when the main trigger is pressed")
        return

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"world nav delta: {event_name} {event.pose_delta} {event.pivot_position}")

    event = event.clone()
    event.type = "fb.navigate"

    if not isinstance(event, TwoHandedControllerEvent) and settings["world_nav.lock_rotation.single_handed"]:
        yaw = event.pose_delta.rotation.to_euler().z
        event.pose_delta.rotation = Quaternion((0, 0, 1), yaw)

    event.pose_delta = event.pose_delta.inverted()
    nav_pose.transform(event.pose_delta, event.pivot_position)

    pose = nav_pose

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"SETTING to: {pose}")

    if settings["world_nav.interpolate_movement"]:
        t = settings["world_nav.interpolation_factor"]
        pose = Pose.lerp(xr_session.viewer_pose, pose, t)  # interpolate for smoothness

    xr_session.viewer_pose = pose

    root.dispatch_event("fb.navigate", event)


def on_nav_transform_end(self, event_name, event):
    global nav_pose

    if settings["world_nav.nav_mode"] != "GRAB":
        return

    enable_bounds_check()

    if nav_pose is None:
        return

    nav_pose = None

    event = event.clone()
    event.type = "fb.navigate_end"

    root.dispatch_event("fb.navigate_end", event)


filter_fn = filter_event_by_buttons(["squeeze_main", "squeeze_both", "squeeze_alt"])


# WALK mode
def on_strafe_move(self, event_name, event: ControllerEvent):
    """Handle strafe movement: Y for forward/back, X for left/right"""
    global nav_pose

    if settings["world_nav.nav_mode"] != "WALK":
        return

    if nav_pose is None:
        nav_pose = xr_session.viewer_pose

    speed = settings.get("world_nav.walk_speed", 0.1) * xr_session.viewer_scale

    # Get movement value from joystick
    value = event.value

    if "joystick_y" in event_name:
        # Y axis: forward/back (Y up = forward, Y down = back)
        direction = xr_session.viewer_rotation @ Vector((0, value * speed, 0))
    elif "joystick_x" in event_name:
        # X axis: left/right (X right = right, X left = left)
        direction = xr_session.viewer_rotation @ Vector((value * speed, 0, 0))
    else:
        return

    # Only move horizontally (ignore vertical component)
    direction.z = 0

    xr_session.viewer_location += direction


def on_yaw_move(self, event_name, event: ControllerEvent):
    """Handle yaw movement: X for turn right/left, Y for vertical up/down"""
    global nav_pose

    if settings["world_nav.nav_mode"] != "WALK":
        return

    if nav_pose is None:
        nav_pose = xr_session.viewer_pose

    speed = settings.get("world_nav.walk_speed", 0.1) * xr_session.viewer_scale
    rotation_speed = settings.get("world_nav.rotation_speed", 1)
    rotation_speed = radians(rotation_speed)

    # Get movement value from joystick
    value = event.value

    if "joystick_x" in event_name:
        # X axis: turn right/left (X right = turn right, X left = turn left)
        rotation = Euler((0, 0, -value * rotation_speed), "XYZ").to_quaternion()
        xr_session.viewer_rotation = rotation @ xr_session.viewer_rotation
    elif "joystick_y" in event_name:
        # Y axis: vertical up/down (Y up = up, Y down = down)
        direction = Vector((0, 0, value * speed))
        xr_session.viewer_location += direction
    else:
        return


def enable():
    global nav_pose
    nav_pose = xr_session.viewer_pose

    root.add_event_listener(f"joystick_y_alt_press", on_strafe_move)
    root.add_event_listener(f"joystick_x_alt_press", on_strafe_move)

    root.add_event_listener(f"joystick_x_main_press", on_yaw_move)
    root.add_event_listener(f"joystick_y_main_press", on_yaw_move)
    # grab events
    root.add_event_listener("drag_start", on_nav_transform_start, {"filter_fn": filter_fn})
    root.add_event_listener("drag", on_nav_transform, {"filter_fn": filter_fn})
    root.add_event_listener("drag_end", on_nav_transform_end, {"filter_fn": filter_fn})


def disable():
    global nav_pose
    nav_pose = None

    # walk events
    root.remove_event_listener(f"joystick_y_alt_press", on_strafe_move)
    root.remove_event_listener(f"joystick_x_alt_press", on_strafe_move)

    root.remove_event_listener(f"joystick_x_main_press", on_yaw_move)
    root.remove_event_listener(f"joystick_y_main_press", on_yaw_move)

    # grab events
    root.remove_event_listener("drag_start", on_nav_transform_start)
    root.remove_event_listener("drag", on_nav_transform)
    root.remove_event_listener("drag_end", on_nav_transform_end)
