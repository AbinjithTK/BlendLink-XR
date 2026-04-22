import bpy

import bl_xr
from bl_xr import root, xr_session

import numpy as np
from math import radians
from mathutils import Vector

from ..settings_manager import settings
from ..utils import log, link_to_configured_collection
from ..utils import enable_bounds_check, disable_bounds_check

curr_stroke = None


class Stroke:
    def __init__(self):
        self.prev_pt = None
        self.curve = None
        self.point_co_size = 3
        self.pressure_field = "radius"

    def add_pt(self):
        if len(self.curve.points) > 0:
            prev_pt = self.curve.points[-1].co
            if self.point_co_size == 4:
                prev_pt = prev_pt[:-1]
            self.prev_pt = Vector(prev_pt)

        self.curve.points.add(1)

    def update_pt(self, stroke_pt, pressure, index=-1):
        pt = self.curve.points[index]
        pt_co = stroke_pt.to_tuple()
        if self.point_co_size == 4:
            pt_co += (1,)
        pt.co = pt_co
        setattr(pt, self.pressure_field, pressure)

    def is_direction_change(self, stroke_pt):
        prev_pt = self.curve.points[-1].co
        if self.point_co_size == 4:
            prev_pt = prev_pt[:-1]
        prev_pt = Vector(prev_pt)

        prev_prev_pt = self.prev_pt

        a = prev_pt - prev_prev_pt
        b = stroke_pt - prev_pt

        angle = a.angle(b, 0)
        return angle > radians(settings["stroke.angle_threshold_for_dir_change"])


class Annotation(Stroke):
    def start(self, stroke_pt, pressure):
        new_gpencil = "Annotations" not in bpy.data.grease_pencils
        if new_gpencil:
            self.call_operator()

        gpencil = bpy.data.grease_pencils["Annotations"]
        gp_layer_idx = gpencil.layers.active_index
        gp_layer = gpencil.layers[gp_layer_idx]
        if gp_layer.active_frame is None:
            self.call_operator()
            new_gpencil = True

        if new_gpencil:
            gp_layer.show_in_front = False

        gp_frame = gp_layer.active_frame

        self.pressure_field = "pressure"
        self.curve = gp_frame.strokes.new()
        self.curve.display_mode = "3DSPACE"

        self.add_pt()
        self.update_pt(stroke_pt, pressure)

        self.add_pt()
        self.update_pt(stroke_pt, pressure)

    def stroke(self, stroke_pt, pressure):
        if settings["stroke.straight_line"] or settings["stroke.fixed_thickness"]:
            pressure = 1

        if not settings["stroke.straight_line"]:
            pt = self.curve.points[-1].co
            pt = Vector(pt)

            d = (pt - self.prev_pt).length
            d /= xr_session.viewer_scale

            dir_change = self.is_direction_change(stroke_pt)
            if d > settings["stroke.min_stroke_distance"] or dir_change:
                self.add_pt()

        self.update_pt(stroke_pt, pressure, index=-1)

    def end(self):
        pass

    def call_operator(self):
        from blendlinkxr.utils import desktop_viewport

        with desktop_viewport.temp_override():
            bpy.ops.gpencil.annotate()  # creates the default annotation entry and layer


class NURBSCurve(Stroke):
    def __init__(self):
        super().__init__()

        self.extended_stroke = False
        self._reversed_for_extend = False

    def start(self, stroke_pt, pressure):
        stroke_type = settings["stroke.type"]

        cursor = root.q("#cursor_main")
        cursor_size = cursor.size * cursor.scale.x

        self.point_co_size = 4

        if settings["stroke.straight_line"] or settings["stroke.fixed_thickness"]:
            pressure = 1

        active_ob = bpy.context.view_layer.objects.active
        if settings["stroke.extend"] and active_ob and active_ob.type == "CURVE":
            self.extended_stroke = True
            self.cu = active_ob.data
            self.curve = self.cu.splines[0]

            # pick the nearest of the start or end point of the curve to extend from
            start_pt = Vector(self.curve.points[0].co[:-1])
            end_pt = Vector(self.curve.points[-1].co[:-1])
            if (stroke_pt - start_pt).length < (stroke_pt - end_pt).length:
                # reverse the curve points and radii, so that we always extend from the end
                n = len(self.curve.points)
                pts = np.zeros(n * 4)
                radii = np.zeros(n)
                self.curve.points.foreach_get("co", pts)
                self.curve.points.foreach_get("radius", radii)

                pts = pts.reshape(-1, 4)[::-1].flatten()  # reshape pts to group by 4 before reversing
                radii = radii[::-1]

                # Ensure arrays are C-contiguous for Blender 3.4 compatibility
                pts = np.ascontiguousarray(pts)
                radii = np.ascontiguousarray(radii)

                self.curve.points.foreach_set("co", pts)
                self.curve.points.foreach_set("radius", radii)

                self._reversed_for_extend = True

            self.prev_pt = Vector(self.curve.points[-1].co[:-1])
        else:
            self.cu = bpy.data.curves.new(stroke_type, "CURVE")
            self.cu.dimensions = "3D"
            self.cu.bevel_depth = cursor_size * xr_session.viewer_scale
            self.cu.bevel_mode = settings[f"stroke.{stroke_type}.bevel_mode"]
            self.cu.bevel_resolution = settings[f"stroke.{stroke_type}.bevel_resolution"]
            self.cu.use_fill_caps = settings[f"stroke.{stroke_type}.use_fill_caps"]

            ob = bpy.data.objects.new(stroke_type, self.cu)

            if settings["gizmo.mirror.enabled"]:
                from blendlinkxr.gizmos.mirror_plane import get_mirror_object

                mirror = ob.modifiers.new("Mirror", "MIRROR")
                mirror.use_axis = [
                    settings["gizmo.mirror.axis_x"],
                    settings["gizmo.mirror.axis_y"],
                    settings["gizmo.mirror.axis_z"],
                ]
                mirror.mirror_object = get_mirror_object()

            link_to_configured_collection(ob)

            stroke_color = settings[f"stroke.{stroke_type}.color"]
            if stroke_color:
                ob.color = stroke_color

            if settings["stroke.straight_line"]:
                self.curve = self.cu.splines.new("POLY")
            else:
                self.curve = self.cu.splines.new("NURBS")

            self.update_pt(stroke_pt, pressure)

        if settings["stroke.straight_line"] or (settings["stroke.extend"] and self.extended_stroke):
            self.add_pt()
            self.update_pt(stroke_pt, pressure)
        else:
            # hack to make a NURBS line look complete while drawing.
            # the two initial points are needed, otherwise the first
            # point will appear missing in the render (until use_endpoint_u is True)
            self.add_pt()
            self.update_pt(stroke_pt, pressure)
            self.add_pt()
            self.update_pt(stroke_pt, pressure)

            # add another two points, which will be following the pointer
            self.add_pt()
            self.update_pt(stroke_pt, pressure)
            self.add_pt()
            self.update_pt(stroke_pt, pressure)

            # add another point, which will be the pointer
            self.add_pt()
            self.update_pt(stroke_pt, pressure)

    def stroke(self, stroke_pt, pressure):
        if settings["stroke.straight_line"] or settings["stroke.fixed_thickness"]:
            pressure = 1

        if not settings["stroke.straight_line"]:
            pt = self.curve.points[-1].co
            pt = Vector(pt[:-1])

            d = (pt - self.prev_pt).length
            d /= xr_session.viewer_scale

            dir_change = self.is_direction_change(stroke_pt)
            if d > settings["stroke.min_stroke_distance"] or dir_change:
                self.add_pt()

            # hack for NURBS: update the two points before the last, to make the line look complete while drawing
            self.update_pt(stroke_pt, pressure, index=-3)
            self.update_pt(stroke_pt, pressure, index=-2)

        self.update_pt(stroke_pt, pressure, index=-1)

    def end(self):
        if settings["stroke.straight_line"]:
            return

        n = len(self.curve.points)

        # copy the existing points
        pts = np.zeros(n * 4)
        radii = np.zeros(n)
        self.curve.points.foreach_get("co", pts)
        self.curve.points.foreach_get("radius", radii)

        if settings["stroke.extend"] and self.extended_stroke:
            if self._reversed_for_extend:  # bring the points back to the original order
                pts = pts.reshape(-1, 4)[::-1].flatten()  # reshape pts to group by 4 before reversing
                radii = radii[::-1]
        else:
            # remove the first two and last two points, since they were a hack to make the
            # NURBS line look complete while drawing
            remove_start = 2
            remove_end = 2

            n -= remove_start + remove_end
            pts = pts[remove_start * 4 : -remove_end * 4]
            radii = radii[remove_start:-remove_end]

        # Ensure arrays are C-contiguous for Blender 3.4 compatibility
        pts = np.ascontiguousarray(pts)
        radii = np.ascontiguousarray(radii)

        new_polyline = self.cu.splines.new("NURBS")
        new_polyline.points.add(n - 1)  # already has one point
        new_polyline.points.foreach_set("co", pts)
        new_polyline.points.foreach_set("radius", radii)

        self.cu.splines.remove(self.curve)

        new_polyline.use_endpoint_u = True


def on_stroke_start(_, event_name, event):
    global curr_stroke

    disable_bounds_check()

    stroke_type = settings["stroke.type"]

    if stroke_type in ("pen", "pipe"):
        curr_stroke = NURBSCurve()
    elif stroke_type == "annotation":
        curr_stroke = Annotation()

    # Use MX Ink tip force for pressure if available, otherwise use trigger value
    pressure = settings.get("mx_ink.tip_force", 0.0)
    if pressure < 0.01:
        pressure = event.value  # fallback to trigger analog value
    curr_stroke.start(event.position, pressure=pressure)


def on_stroke(_, event_name, event):
    if curr_stroke is None:
        return

    # Use MX Ink tip force for pressure if available, otherwise use trigger value
    pressure = settings.get("mx_ink.tip_force", 0.0)
    if pressure < 0.01:
        pressure = event.value  # fallback to trigger analog value
    curr_stroke.stroke(event.position, pressure=pressure)


def on_stroke_end(_, event_name, event):
    global curr_stroke

    enable_bounds_check()

    if curr_stroke is None:
        return

    log.info("finished spline")

    curr_stroke.end()

    bpy.ops.ed.undo_push(message="add curve")

    curr_stroke = None


def enable_tool():
    root.add_event_listener("trigger_main_start", on_stroke_start)
    root.add_event_listener("trigger_main_press", on_stroke)
    root.add_event_listener("trigger_main_end", on_stroke_end)


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_stroke_start)
    root.remove_event_listener("trigger_main_press", on_stroke)
    root.remove_event_listener("trigger_main_end", on_stroke_end)
