from bl_xr import root, xr_session
from bl_xr import Line, Text
from bl_xr.consts import VEC_RIGHT, YELLOW
from bl_xr.utils import quaternion_from_vector

from math import radians, atan2

from mathutils import Vector, Quaternion
import bpy

# Measure tool visual elements
measure_line = None
measure_text = None


def update_measure_tool(self):
    """Update the measure tool line and text based on controller positions"""
    if not xr_session.is_running:
        return

    # Get controller aim positions
    main_pos = xr_session.controller_main_aim_position
    alt_pos = xr_session.controller_alt_aim_position

    # Update line vertices
    measure_line.mesh.vertices.clear()
    measure_line.mesh.vertices.append(main_pos)
    measure_line.mesh.vertices.append(alt_pos)

    # Clear batch to force redraw
    if hasattr(measure_line, "_batch"):
        delattr(measure_line, "_batch")

    # Calculate distance
    distance = (alt_pos - main_pos).length

    # Format distance with scene units
    unit_settings = bpy.context.scene.unit_settings
    distance_text = bpy.utils.units.to_string(unit_settings.system, "LENGTH", distance, precision=3, split_unit=unit_settings.use_separate)

    # Position text above the midpoint
    midpoint = (main_pos + alt_pos) / 2
    text_offset = Vector((0, 0, 0.005 * xr_session.viewer_scale))  # 5cm above the line
    measure_text.position = midpoint + text_offset
    measure_text.text = distance_text

    # Align text to face the viewer
    viewer_pos = xr_session.viewer_location
    direction_to_viewer = (measure_text.position - viewer_pos).normalized()
    horizontal_direction = Vector((direction_to_viewer.x, direction_to_viewer.y, 0)).normalized()
    rot_horizontal = quaternion_from_vector(horizontal_direction)
    horizontal_length = (direction_to_viewer.x**2 + direction_to_viewer.y**2) ** 0.5
    angle = atan2(direction_to_viewer.z, horizontal_length)
    rot_vertical = Quaternion(VEC_RIGHT, angle)
    measure_text.rotation = rot_horizontal @ rot_vertical @ Quaternion(VEC_RIGHT, radians(90))


# Create visual elements
measure_line = Line(id="measure_line", style={"color": YELLOW, "depth_test": False})
measure_text = Text(
    "",
    id="measure_text",
    font_size=25,
    intersects=None,
    style={"fixed_scale": True, "depth_test": False},
    rotation=Quaternion(VEC_RIGHT, radians(90)),
)

# Set up continuous update
measure_line.update = update_measure_tool.__get__(measure_line)


def enable_tool():
    root.append_child(measure_line)
    root.append_child(measure_text)


def disable_tool():
    if measure_line in root.child_nodes:
        root.remove_child(measure_line)
    if measure_text in root.child_nodes:
        root.remove_child(measure_text)
