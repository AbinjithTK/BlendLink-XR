import bpy
import time

from bl_xr import root
from blendlinkxr.utils import recenter_mouse_cursor, set_mode

DEBOUNCE_TIME = 0.8  # seconds

wait_till_time = None  # seconds


def on_mode_change(self, event_name, new_mode):
    global wait_till_time

    ob = bpy.context.view_layer.objects.active

    if ob and ob.type == "FONT" and new_mode == "EDIT":
        recenter_mouse_cursor()
        delay_click_to_exit_editing(self, event_name, None)


def delay_click_to_exit_editing(self, event_name, event):
    global wait_till_time

    wait_till_time = time.time() + DEBOUNCE_TIME


def on_click(self, event_name, event):
    if wait_till_time is None or time.time() < wait_till_time:  # prevent immediate click after text creation
        return

    ob = bpy.context.view_layer.objects.active

    if ob and ob.type == "FONT" and ob.mode == "EDIT":
        set_mode("OBJECT")  # end edit if clicked (anywhere in the scene)


def enable_gizmo():
    root.add_event_listener("bl.mode_change", on_mode_change)
    root.add_event_listener("fb.draw_text", delay_click_to_exit_editing)
    root.add_event_listener("trigger_main_end", on_click)


def disable_gizmo():
    root.remove_event_listener("bl.mode_change", on_mode_change)
    root.remove_event_listener("fb.draw_text", delay_click_to_exit_editing)
    root.remove_event_listener("trigger_main_end", on_click)
