from bl_xr import root, xr_session, intersections
from bl_xr import Line, Node

is_drawing = False


def on_controller_update(self):
    self.position = xr_session.controller_main_aim_position
    self.rotation = xr_session.controller_main_aim_rotation

    controller_pointer_line.style["visible"] = not is_drawing and len(intersections.curr["raycast"]) > 0


controller_pointer_line = Line(length=1)
controller_pointer = Node(
    id="controller_main_pointer",
    child_nodes=[controller_pointer_line],
    intersects=None,
    style={"fixed_scale": True},
)
controller_pointer.update = on_controller_update.__get__(controller_pointer)


def on_draw_start(self, event_name, event):
    global is_drawing

    is_drawing = True


def on_draw_end(self, event_name, event):
    global is_drawing

    is_drawing = False


def enable_gizmo():
    root.append_child(controller_pointer)

    root.add_event_listener("trigger_main_start", on_draw_start)
    root.add_event_listener("trigger_main_end", on_draw_end)


def disable_gizmo():
    root.remove_child(controller_pointer)

    root.remove_event_listener("trigger_main_start", on_draw_start)
    root.remove_event_listener("trigger_main_end", on_draw_end)
