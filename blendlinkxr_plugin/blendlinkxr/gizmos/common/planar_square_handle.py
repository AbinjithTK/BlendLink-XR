import bl_xr
from bl_xr import xr_session, Node, Plane
from bl_xr.utils import apply_haptic_feedback

from mathutils import Vector

from ...settings_manager import settings
from ...utils import log


class PlanarSquareHandle(Node):
    "A square that can be dragged along a plane (and dispatches handle drag events to itself)"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        size = kwargs.get("size", settings["gizmo.planar_handle.size"])

        self._color = (1, 0.77, 0.25, 1)
        self.highlight_color = (1, 0.92, 0.61, 1)

        self.plane = Plane(width=size, height=size)
        self.plane.position = Vector((0.05, 0.05, 0))
        self.plane.style.update({"color": self._color, "opacity": 0.8})

        self.style["fixed_scale"] = True
        self.plane.style["depth_test"] = False
        self.haptic_feedback = kwargs.get("haptic_feedback", True)

        self.apply_total_offset = kwargs.get("apply_total_offset", True)

        self.intersects = "bounds"

        self._is_pressing = False
        self._is_highlighted = False
        self._is_dragging = False

        self.append_child(self.plane)

        self.plane.add_event_listener("drag_start", self.on_plane_drag)
        self.plane.add_event_listener("drag", self.on_plane_drag)
        self.plane.add_event_listener("drag_end", self.on_plane_drag_end)

        # absorb trigger events, we don't want them to go to the root
        self.plane.add_event_listener("trigger_main_start", self.absorb_trigger_press_event)
        self.plane.add_event_listener("trigger_main_press", self.absorb_trigger_press_event)
        self.plane.add_event_listener("trigger_main_end", self.absorb_trigger_press_event)
        self.plane.add_event_listener("squeeze_main_start", self.absorb_trigger_press_event)
        self.plane.add_event_listener("squeeze_main_press", self.absorb_trigger_press_event)
        self.plane.add_event_listener("squeeze_main_end", self.absorb_trigger_press_event)

    def highlight(self, state: bool, haptic=True):
        self._is_highlighted = state
        self.plane.style["color"] = self.highlight_color if state else self._color

        if state and haptic and self.haptic_feedback:
            apply_haptic_feedback()

    @property
    def is_highlighted(self):
        return self._is_highlighted

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c
        self.highlight(self._is_highlighted, haptic=False)

    def on_plane_drag(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        if event_name != "drag_start" and not self._is_dragging:  # skip further events if we didn't drag at the start
            return

        event.stop_propagation = True
        event.stop_propagation_immediate = True

        self._is_dragging = True

        if event_name == "drag_start":
            self.dispatch_event("handle_drag_start", event)

        self.dispatch_event("handle_drag", event)

    def on_plane_drag_end(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        self._is_pressing = False

        if not self._is_dragging:  # skip further events if we didn't drag at the start
            return

        event.stop_propagation = True
        event.stop_propagation_immediate = True

        self._is_dragging = False

        self.dispatch_event("handle_drag_end", event)

    def absorb_trigger_press_event(self, event_name, event):
        expected_button_name = settings["transform.grab_button"]

        if event_name == f"{expected_button_name}_main_start" and not self._is_pressing:
            self._is_pressing = True

        if self._is_pressing:
            event.stop_propagation = True
            event.stop_propagation_immediate = True

    def update(self):
        controller_p = xr_session.controller_main_aim_position
        should_highlight = self.plane.intersect(
            controller_p, bl_xr.selection_shape, bl_xr.selection_size * xr_session.viewer_scale
        )
        if should_highlight:
            if not self._is_highlighted:
                self.highlight(True)
        elif self._is_highlighted:
            self.highlight(False)
