import bpy
from mathutils import Matrix

import bl_xr
from bl_xr import root, xr_session, Node
from bl_xr.events.make_events import controller

from ..utils import get_blendlink_collection, gc_blendlink_collection

BASE = "BL-Base"
HEADSET = "BL-Headset"
CONTROLLER_RIGHT = "BL-Controller-Right"
CONTROLLER_LEFT = "BL-Controller-Left"

BUTTONS_TO_TRACK = [
    ("trigger", float),
    ("squeeze", float),
    ("joystick_x", float),
    ("joystick_y", float),
    ("button_a", bool),
    ("button_b", bool),
]


def create_empties():
    bl_collection = get_blendlink_collection()

    for obj_name in (BASE, HEADSET, CONTROLLER_RIGHT, CONTROLLER_LEFT):
        if obj_name in bl_collection.objects:
            continue

        # create the object
        empty = bpy.data.objects.new(obj_name, None)
        empty.empty_display_size = 1
        empty.empty_display_type = "ARROWS"
        empty.hide_viewport = True
        empty.hide_select = True
        bl_collection.objects.link(empty)

        # create the custom properties
        if obj_name in (CONTROLLER_RIGHT, CONTROLLER_LEFT):
            for button, btn_type in BUTTONS_TO_TRACK:
                empty[button] = False if btn_type == bool else 0.0


def delete_empties():
    bl_collection = get_blendlink_collection()

    for obj_name in (BASE, HEADSET, CONTROLLER_RIGHT, CONTROLLER_LEFT):
        if obj_name in bl_collection.objects:
            obj = bl_collection.objects[obj_name]
            bpy.data.objects.remove(obj, do_unlink=True)

    gc_blendlink_collection()


def get_empty(name):
    bl_collection = get_blendlink_collection()
    return bl_collection.objects.get(name)


class SyncEmpties(Node):
    def update(self):
        bl_collection = get_blendlink_collection()

        right_hand = "main" if bl_xr.main_hand == "right" else "alt"
        left_hand = "alt" if bl_xr.main_hand == "right" else "main"

        for obj_name in (BASE, HEADSET, CONTROLLER_RIGHT, CONTROLLER_LEFT):
            ob = bl_collection.objects[obj_name]

            # Update the transform
            if obj_name == BASE:
                ob.matrix_world = Matrix.LocRotScale(xr_session.viewer_location, xr_session.viewer_rotation, (1, 1, 1))
            elif obj_name == HEADSET:
                ob.matrix_world = xr_session.viewer_camera_pose.to_matrix()
            elif obj_name == CONTROLLER_RIGHT:
                pos = getattr(xr_session, f"controller_{right_hand}_aim_position")
                rot = getattr(xr_session, f"controller_{right_hand}_aim_rotation")
                ob.matrix_world = Matrix.LocRotScale(pos, rot, (1, 1, 1))
            elif obj_name == CONTROLLER_LEFT:
                pos = getattr(xr_session, f"controller_{left_hand}_aim_position")
                rot = getattr(xr_session, f"controller_{left_hand}_aim_rotation")
                ob.matrix_world = Matrix.LocRotScale(pos, rot, (1, 1, 1))

            # Update button states (for controllers)
            if obj_name in (CONTROLLER_RIGHT, CONTROLLER_LEFT):
                hand = right_hand if obj_name == CONTROLLER_RIGHT else left_hand
                for button, btn_type in BUTTONS_TO_TRACK:
                    prop_name = f"{button}_{hand}_state"
                    if prop_name in controller.input_state:
                        value = controller.input_state[prop_name]
                        if btn_type == bool:
                            value = bool(value)
                    else:
                        value = False if btn_type == bool else 0.0

                    ob[button] = value


def on_file_load(self, event_name, scene):
    create_empties()


def on_unload(self, event_name, event):
    delete_empties()


sync_empties_node = SyncEmpties(id="sync_empties", intersects=None)


def enable_gizmo():
    root.append_child(sync_empties_node)

    create_empties()

    root.add_event_listener("fb.file_load", on_file_load)
    root.add_event_listener("fb.unload", on_unload)


def disable_gizmo():
    root.remove_child(sync_empties_node)

    delete_empties()

    root.remove_event_listener("fb.file_load", on_file_load)
    root.remove_event_listener("fb.unload", on_unload)
