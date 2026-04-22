import bpy

from bl_xr import root, xr_session, Node
from bl_xr.consts import VEC_ONE
from blendlinkxr.utils import set_mode

from math import radians
from mathutils import Vector, Quaternion

temp_text_ob_name = None
cursor = None

OFFSET = Vector((-0.05, 0.05, 0))
FONT_SIZE = 0.05

temp_text = Node(id="temp_text")


def update_text(self):
    if temp_text_ob_name is None:
        return

    temp_text_ob = bpy.data.objects.get(temp_text_ob_name)
    if temp_text_ob is None:
        return

    temp_text_ob.location = cursor.local_to_world_point(OFFSET)
    temp_text_ob.rotation_mode = "QUATERNION"
    temp_text_ob.rotation_quaternion = cursor.rotation_world @ Quaternion((1, 0, 0), radians(45))


temp_text.update = update_text.__get__(temp_text)


def on_place_text(self, event_name, event):
    global temp_text_ob_name

    if temp_text_ob_name is None:
        return

    from blendlinkxr.tools import enable_tool

    temp_text_ob_name = None  # so that it stops following the cursor
    temp_text.style["visible"] = False

    root.dispatch_event("fb.draw_text", None)

    set_mode("EDIT")

    enable_tool("select")


def enable_tool():
    global temp_text_ob_name, cursor

    if not temp_text_ob_name:
        bpy.ops.object.text_add()
        temp_text_ob = bpy.context.view_layer.objects.active
        temp_text_ob.scale = VEC_ONE * FONT_SIZE * xr_session.viewer_scale
        temp_text_ob_name = temp_text_ob.name

    root.append_child(temp_text)
    temp_text.style["visible"] = True

    if not cursor:
        cursor = root.q("#cursor_main")

    root.add_event_listener("trigger_main_end", on_place_text)


def disable_tool():
    global temp_text_ob_name

    try:
        root.remove_child(temp_text)
    except:
        pass

    if temp_text_ob_name:
        try:
            bpy.data.objects.remove(bpy.data.objects.get(temp_text_ob_name))
        except:
            pass
        temp_text_ob_name = None

    root.remove_event_listener("trigger_main_end", on_place_text)
