import bpy

import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Button, Grid2D
from bl_xr.utils import get_mesh_mode, apply_haptic_feedback, to_blender_axis_system

from mathutils import Vector

from ..gizmos import toggle_gizmo
from ..utils import set_mode, set_tool, set_default_cursor as set_cursor
from ..settings_manager import settings, save_settings_to_file
from .. import tools, gizmos

SUBMENU_Y_OFFSET = 0.0
SUBMENU_Z_OFFSET = 0.005
BUTTON_SIZE = 0.04
MODE_PANEL_BUTTON_SIZE = BUTTON_SIZE * 0.62

submenus = {}


def set_edit_type(type):
    ob = bpy.context.view_layer.objects.active
    if ob and ob.type == "MESH":
        bpy.ops.mesh.select_mode(type=type)

    return True


def set_option(name, value):
    settings[name] = value
    return True


def toggle_option(name, options=[False, True]):
    curr_value = settings.get(name, options[0])
    settings[name] = options[1] if curr_value == options[0] else options[0]
    return True


def set_transform_space(value):
    bpy.context.scene.transform_orientation_slots[0].type = value


def buzz():
    apply_haptic_feedback(hand="alt")
    return True


def toggle_proportional_edit():
    tool_settings = bpy.context.scene.tool_settings
    tool_settings.use_proportional_edit = not tool_settings.use_proportional_edit
    return True


def reset_world_scale():
    if not xr_session.is_running or xr_session.session_state is None:
        return

    actual_location = xr_session.session_state.viewer_pose_location
    actual_rotation = to_blender_axis_system(xr_session.session_state.viewer_pose_rotation)

    actual_rotation = actual_rotation.to_euler()
    actual_rotation.x = actual_rotation.y = 0
    actual_rotation = actual_rotation.to_quaternion()

    xr_session.session_settings.base_scale = 1
    xr_session.session_settings.base_pose_location = Vector()
    xr_session.session_settings.base_pose_angle = 0

    xr_session.session_state.navigation_scale = 1
    xr_session.session_state.navigation_location = Vector(actual_location)
    xr_session.session_state.navigation_rotation = actual_rotation


Node.STYLESHEET.update(
    {
        ".main_menu_btn": {
            "scale": Vector((BUTTON_SIZE,) * 3),
        },
        ".mode_menu_btn": {
            "scale": Vector((MODE_PANEL_BUTTON_SIZE,) * 3),
        },
    }
)

main_menu = Grid2D(
    id="main_menu",
    class_name="menu_items panel",
    num_cols=2,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/select.png",
            tooltip="SELECT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("select") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "select",
        ),
        Button(
            icon="images/pen.png",
            tooltip="PEN",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
            and set_option("stroke.type", "pen")
            and set_mode("OBJECT")
            and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.stroke",
        ),
        Button(
            icon="images/erase.png",
            tooltip="ERASE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("erase") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "erase",
        ),
        Button(
            id="shape",
            icon="images/shape_cube.png",
            tooltip="SHAPE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.shape") and set_mode("OBJECT") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.shape",
        ),
        Button(
            icon="images/hull.png",
            tooltip="HULL",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.hull") and set_mode("OBJECT") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.hull",
        ),
        Button(
            icon="images/text.png",
            tooltip="TEXT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_mode("OBJECT") and set_tool("draw.text") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.text",
        ),
        Button(
            icon="images/measure.png",
            tooltip="MEASURE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("measure") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "measure",
        ),
        Button(
            icon="images/pen_thin.png",
            tooltip="GP DRAW",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.grease_pencil")
            and set_mode("OBJECT")
            and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.grease_pencil",
        ),
    ],
)

submenus["PEN"] = Grid2D(
    id="submenu_pen",
    class_name="controller_submenu menu_items",
    num_cols=3,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    position=Vector((main_menu.bounds_local.max.x, SUBMENU_Y_OFFSET + 0.08, SUBMENU_Z_OFFSET)),
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/pen_thin.png",
            tooltip="PEN",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
            and set_option("stroke.type", "pen")
            and set_cursor("pen")
            and buzz(),
            highlight_checker=lambda *x: settings["stroke.type"] == "pen",
        ),
        Button(
            icon="images/pipe.png",
            tooltip="PIPE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("stroke.type", "pipe") and set_cursor("pipe") and buzz(),
            highlight_checker=lambda *x: settings["stroke.type"] == "pipe",
        ),
        Button(
            icon=None,
            tooltip="",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: False,
            highlight_checker=lambda *x: False,
        ),
        Button(
            icon="images/straight_line.png",
            tooltip="STRAIGHT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("stroke.straight_line") and buzz(),
            highlight_checker=lambda *x: settings["stroke.straight_line"],
        ),
        Button(
            icon="images/extend_stroke.png",
            tooltip="EXTEND",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("stroke.extend") and buzz(),
            highlight_checker=lambda *x: settings["stroke.extend"],
            enabled_checker=lambda: bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.type == "CURVE",
        ),
        Button(
            icon="images/fixed_thickness.png",
            tooltip="FIXED THICKNESS",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("stroke.fixed_thickness") and buzz(),
            highlight_checker=lambda *x: settings["stroke.fixed_thickness"],
        ),
    ],
)

if bpy.app.version < (4, 3):
    btn = Button(
        icon="images/annotate.png",
        tooltip="ANNOTATE",
        class_name="main_menu_btn",
        on_pointer_main_press_end=lambda *x: set_tool("draw.stroke")
        and set_option("stroke.type", "annotation")
        and set_cursor("pen")
        and buzz(),
        highlight_checker=lambda *x: settings["stroke.type"] == "annotation",
    )
    submenus["PEN"].insert_before(btn, submenus["PEN"].first_child)

submenus["SHAPE"] = Grid2D(
    id="submenu_shape",
    class_name="controller_submenu menu_items",
    num_cols=2,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/shape_cube.png",
            tooltip="CUBE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cube") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cube",
        ),
        Button(
            icon="images/shape_sphere.png",
            tooltip="SPHERE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "sphere") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "sphere",
        ),
        Button(
            icon="images/shape_cylinder.png",
            tooltip="CYLINDER",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cylinder") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cylinder",
        ),
        Button(
            icon="images/shape_cone.png",
            tooltip="CONE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "cone") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "cone",
        ),
        Button(
            icon="images/shape_monkey.png",
            tooltip="MONKEY",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "monkey") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "monkey",
        ),
        Button(
            icon="images/shape_torus.png",
            tooltip="TORUS",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("shape.type", "torus") and buzz(),
            highlight_checker=lambda *x: settings["shape.type"] == "torus",
        ),
    ],
)

submenus["GP"] = Grid2D(
    id="submenu_gp",
    class_name="controller_submenu menu_items",
    num_cols=3,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        # Row 1: GP tools
        Button(
            icon="images/pen_thin.png",
            tooltip="GP DRAW",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.grease_pencil")
            and set_mode("OBJECT")
            and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.grease_pencil",
        ),
        Button(
            icon="images/erase.png",
            tooltip="GP ERASE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.gp_erase") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.gp_erase",
        ),
        Button(
            icon="images/straight_line.png",
            tooltip="GP LINE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.gp_line")
            and set_mode("OBJECT")
            and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.gp_line",
        ),
        # Row 2: GP tools continued + smooth
        Button(
            icon="images/hull.png",
            tooltip="GP SMOOTH",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_tool("draw.gp_smooth") and buzz(),
            highlight_checker=lambda *x: tools.active_tool == "draw.gp_smooth",
        ),
        # Brush presets
        Button(
            icon="images/pen.png",
            tooltip="PENCIL",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_brush", "pencil") and buzz(),
            highlight_checker=lambda *x: settings.get("gp.active_brush") == "pencil",
        ),
        Button(
            icon="images/pen_thin.png",
            tooltip="INK PEN",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_brush", "ink_pen") and buzz(),
            highlight_checker=lambda *x: settings.get("gp.active_brush") == "ink_pen",
        ),
        # Row 3: More brushes
        Button(
            icon="images/pipe.png",
            tooltip="MARKER",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_brush", "marker_bold") and buzz(),
            highlight_checker=lambda *x: settings.get("gp.active_brush") == "marker_bold",
        ),
        Button(
            icon="images/annotate.png" if bpy.app.version < (4, 3) else "images/pen.png",
            tooltip="AIRBRUSH",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_brush", "airbrush") and buzz(),
            highlight_checker=lambda *x: settings.get("gp.active_brush") == "airbrush",
        ),
        Button(
            icon="images/shape_sphere.png",
            tooltip="DOT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_brush", "dot") and buzz(),
            highlight_checker=lambda *x: settings.get("gp.active_brush") == "dot",
        ),
    ],
)

# GP Color palette — separate panel below GP submenu
gp_color_panel = Grid2D(
    id="gp_color_panel",
    class_name="controller_submenu menu_items",
    num_cols=5,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((main_menu.bounds_local.max.x, SUBMENU_Y_OFFSET - 0.08, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            icon="images/shape_cube.png",
            tooltip="BLACK",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.0, 0.0, 0.0, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.0, 0.0, 0.0, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="WHITE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (1.0, 1.0, 1.0, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((1.0, 1.0, 1.0, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="RED",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.8, 0.1, 0.1, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.8, 0.1, 0.1, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="GREEN",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.1, 0.7, 0.2, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.1, 0.7, 0.2, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="BLUE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.1, 0.3, 0.9, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.1, 0.3, 0.9, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="YELLOW",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.9, 0.9, 0.1, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.9, 0.9, 0.1, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="ORANGE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.9, 0.5, 0.1, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.9, 0.5, 0.1, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="PURPLE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.6, 0.1, 0.8, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.6, 0.1, 0.8, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="BROWN",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.4, 0.25, 0.1, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.4, 0.25, 0.1, 1.0)),
        ),
        Button(
            icon="images/shape_cube.png",
            tooltip="GRAY",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: set_option("gp.active_color", (0.5, 0.5, 0.5, 1.0)) and buzz(),
            highlight_checker=lambda *x: _is_color_active((0.5, 0.5, 0.5, 1.0)),
        ),
    ],
)


def _is_color_active(color):
    """Check if a color matches the active GP color."""
    active = settings.get("gp.active_color", (0.0, 0.0, 0.0, 1.0))
    if not isinstance(active, (tuple, list)):
        return False
    return (abs(active[0] - color[0]) < 0.05 and
            abs(active[1] - color[1]) < 0.05 and
            abs(active[2] - color[2]) < 0.05)


def on_loop_cut_click():
    if tools.active_tool == "edit_mesh.loop_cut":
        set_tool("select")
    else:
        set_tool("edit_mesh.loop_cut")

    buzz()


def on_merge_click():
    bpy.ops.mesh.merge(type="CENTER")

    bpy.ops.ed.undo_push(message="merge")
    buzz()


def on_make_face_click():
    bpy.ops.mesh.edge_face_add()

    bpy.ops.ed.undo_push(message="make face")
    buzz()


submenus["EDIT"] = Grid2D(
    id="submenu_edit",
    class_name="controller_submenu menu_items",
    num_cols=3,
    cell_width=BUTTON_SIZE,
    cell_height=BUTTON_SIZE,
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/edit_vert.png",
            tooltip="VERT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("VERT") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "VERT",
        ),
        Button(
            icon="images/edit_edge.png",
            tooltip="EDGE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("EDGE") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "EDGE",
        ),
        Button(
            icon="images/edit_face.png",
            tooltip="FACE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: set_edit_type("FACE") and buzz(),
            highlight_checker=lambda *x: get_mesh_mode() == "FACE",
        ),
        Button(
            icon="images/edit_bevel.png",
            tooltip="BEVEL",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_gizmo("edit_mesh.bevel") and buzz(),
            highlight_checker=lambda *x: "edit_mesh.bevel" in gizmos.active_gizmos,
        ),
        Button(
            icon="images/edit_inset.png",
            tooltip="INSET",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_gizmo("edit_mesh.inset") and buzz(),
            highlight_checker=lambda *x: "edit_mesh.inset" in gizmos.active_gizmos,
        ),
        Button(
            icon="images/edit_extrude.png",
            tooltip="EXTRUDE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_option("edit.perform_extrude"),
            highlight_checker=lambda *x: settings["edit.perform_extrude"],
        ),
        Button(
            icon="images/edit_loop_cut.png",
            tooltip="LOOP CUT",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_loop_cut_click(),
            highlight_checker=lambda *x: tools.active_tool == "edit_mesh.loop_cut",
        ),
        Button(
            icon="images/edit_merge.png",
            tooltip="MERGE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_merge_click(),
        ),
        Button(
            icon="images/edit_make_face.png",
            tooltip="MAKE FACE",
            class_name="main_menu_btn",
            on_pointer_main_press_end=lambda *x: on_make_face_click(),
        ),
    ],
)


submenus["SELECT"] = Grid2D(
    id="submenu_select",
    class_name="controller_submenu menu_items",
    num_cols=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((-main_menu.bounds_local.max.x * 0.4, SUBMENU_Y_OFFSET, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            id="transform_button",
            icon="images/select.png",
            tooltip="FREE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", None),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] is None,
        ),
        Button(
            id="transform_button",
            icon="images/translate.png",
            tooltip="MOVE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "translate"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "translate",
        ),
        Button(
            id="transform_button",
            icon="images/rotate.png",
            tooltip="ROTATE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "rotate"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "rotate",
        ),
        Button(
            id="transform_button",
            icon="images/scale.png",
            tooltip="SCALE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_option("gizmo.transform_handles.type", "scale"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and settings["gizmo.transform_handles.type"] == "scale",
        ),
    ],
)

submenus["TRANSFORM_SPACE"] = Grid2D(
    id="submenu_select",
    class_name="controller_submenu menu_items",
    num_cols=2,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((-main_menu.bounds_local.max.x * 0.74, SUBMENU_Y_OFFSET + 0.14, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            id="transform_button",
            icon="images/transform_global.png",
            tooltip="GLOBAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_transform_space("GLOBAL"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and bpy.context.scene.transform_orientation_slots[0].type == "GLOBAL",
        ),
        Button(
            id="transform_button",
            icon="images/transform_local.png",
            tooltip="LOCAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and set_transform_space("LOCAL"),
            highlight_checker=lambda *x: tools.active_tool == "select"
            and bpy.context.scene.transform_orientation_slots[0].type == "LOCAL",
        ),
    ],
)


def toggle_auto_key():
    prev = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = not prev

    return True


def on_key_frame_insert():
    ob = bpy.context.view_layer.objects.active
    ob.keyframe_insert(data_path="location")
    ob.keyframe_insert(data_path="rotation_euler")
    ob.keyframe_insert(data_path="scale")

    return True


def on_prev_frame():
    bpy.context.scene.frame_current -= 1

    return True


def on_next_frame():
    bpy.context.scene.frame_current += 1

    return True


anim_panel = Grid2D(
    id="anim_panel",
    class_name="menu_items panel",
    num_rows=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector((0, 0.035, 0)),
    style={"visible": False},
    z_offset=0.001,
    child_nodes=[
        Button(
            icon="images/anim_frame_autokey.png",
            tooltip="AUTO KEY",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: toggle_auto_key() and buzz(),
            highlight_checker=lambda *x: bpy.context.scene.tool_settings.use_keyframe_insert_auto,
        ),
        Button(
            icon="images/anim_frame_insert.png",
            tooltip="INSERT",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_key_frame_insert() and buzz(),
        ),
        Button(
            icon="images/anim_frame_prev.png",
            tooltip="PREV",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_prev_frame() and buzz(),
        ),
        Button(
            icon="images/anim_frame_next.png",
            tooltip="NEXT",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: on_next_frame() and buzz(),
        ),
    ],
)

gizmo_panel = Grid2D(
    id="gizmo_panel",
    class_name="panel",
    num_rows=2,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector(),
    z_offset=0.001,
    child_nodes=[
        Button(
            id="3d_grid_button",
            icon="images/3d_grid.png",
            tooltip="3D GRID",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("3d_grid"),
            highlight_checker=lambda *x: "3d_grid" in gizmos.active_gizmos,
        ),
        Button(
            id="camera_preview_button",
            icon="images/camera.png",
            tooltip="VIEW CAMERA",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("camera_preview"),
            highlight_checker=lambda *x: "camera_preview" in gizmos.active_gizmos,
        ),
        Button(
            id="keyframe_button",
            icon="images/anim_timeline_icon.png",
            tooltip="KEYFRAME",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("joystick_for_keyframe"),
            highlight_checker=lambda *x: "joystick_for_keyframe" in gizmos.active_gizmos,
        ),
        Button(
            id="mirror_button",
            icon="images/mirror.png",
            tooltip="MIRROR",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz()
            and toggle_option("gizmo.mirror.enabled")
            and toggle_gizmo("mirror_plane"),
            highlight_checker=lambda *x: settings["gizmo.mirror.enabled"],
        ),
        Button(
            id="reset_world_scale_button",
            icon="images/scale.png",
            tooltip="RESET SCALE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and reset_world_scale(),
        ),
        Button(
            id="walk_button",
            icon="images/walk.png",
            tooltip="WALK",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz()
            and toggle_option("world_nav.nav_mode", options=["GRAB", "WALK"]),
            highlight_checker=lambda *x: settings["world_nav.nav_mode"] == "WALK",
        ),
        Button(
            id="linked_duplicate_button",
            icon="images/link.png",
            tooltip="LINKED CLONE",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("clone.linked_duplicates"),
            highlight_checker=lambda *x: settings["clone.linked_duplicates"],
        ),
        Button(
            id="proportional_edit_button",
            icon="images/proportional_edit.png",
            tooltip="PROPORTIONAL",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_proportional_edit(),
            highlight_checker=lambda *x: bpy.context.scene.tool_settings.use_proportional_edit,
        ),
        # Button(
        #     id="desktop_viewer_button",
        #     icon="images/desktop.png",
        #     tooltip="VIEW DESKTOP",
        #     class_name="mode_menu_btn",
        #     on_pointer_main_press_end=lambda *x: buzz() and toggle_gizmo("desktop_viewer"),
        #     highlight_checker=lambda *x: "desktop_viewer" in gizmos.active_gizmos,
        # ),
    ],
)

proportional_edit_button = gizmo_panel.q("#proportional_edit_button")

mirror_panel = Grid2D(
    id="mirror_panel",
    class_name="cmenu_items panel",
    num_cols=3,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    z_offset=0.001,
    position=Vector((0.1, MODE_PANEL_BUTTON_SIZE, SUBMENU_Z_OFFSET)),
    child_nodes=[
        Button(
            icon="images/icon_x.png",
            tooltip="X",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_x"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_x"],
        ),
        Button(
            icon="images/icon_y.png",
            tooltip="Y",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_y"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_y"],
        ),
        Button(
            icon="images/icon_z.png",
            tooltip="Z",
            class_name="mode_menu_btn",
            on_pointer_main_press_end=lambda *x: buzz() and toggle_option("gizmo.mirror.axis_z"),
            highlight_checker=lambda *x: settings["gizmo.mirror.axis_z"],
        ),
    ],
)

# --- BlendLink XR Color Scheme ---
# Blue panels with white accent
BL_PANEL_BG = (0.12, 0.46, 0.90, 1)
BL_PANEL_BORDER = (0.002, (0.95, 0.96, 0.97, 1))
BL_PANEL_RADIUS = 0.006
BL_PANEL_OPACITY = 0.94
BL_SUBMENU_BG = (0.10, 0.40, 0.82, 1)

Node.STYLESHEET.update(
    {
        "#main_menu_group": {
            "fixed_scale": True,
        },
        "#main_menu_panels": {
            "position": Vector((0, 0.051, 0.001)),
        },
        "#3d_grid_button": {
            "position": Vector((0, 0, 0.001)),
        },
        ".controller_submenu": {
            "visible": False,
            "position": Vector((main_menu.bounds_local.max.x, SUBMENU_Y_OFFSET, SUBMENU_Z_OFFSET)),
            "opacity": BL_PANEL_OPACITY,
            "background": BL_SUBMENU_BG,
            "border": BL_PANEL_BORDER,
            "border_radius": BL_PANEL_RADIUS,
        },
        ".panel": {
            "opacity": BL_PANEL_OPACITY,
            "background": BL_PANEL_BG,
            "border": BL_PANEL_BORDER,
            "border_radius": BL_PANEL_RADIUS,
        },
    }
)

object_mode_btn = Button(
    icon="images/object_mode.png",
    tooltip="OBJECT",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("OBJECT")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "OBJECT",
)
edit_mode_btn = Button(
    icon="images/edit_mode.png",
    tooltip="EDIT",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("EDIT")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "EDIT",
)

pose_mode_btn = Button(
    icon="images/armature.png",
    tooltip="POSE",
    class_name="mode_menu_btn",
    on_pointer_main_press_end=lambda *x: bpy.context.view_layer.objects.active
    and set_tool("select")
    and set_mode("POSE")
    and buzz(),
    highlight_checker=lambda *x: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "POSE",
)

mode_panel = Grid2D(
    id="mode_panel",
    class_name="menu_items panel",
    num_rows=1,
    cell_width=MODE_PANEL_BUTTON_SIZE,
    cell_height=MODE_PANEL_BUTTON_SIZE,
    position=Vector(),
    z_offset=0.001,
    child_nodes=[object_mode_btn, edit_mode_btn, pose_mode_btn],
)
mode_panel.position.y = main_menu.bounds_local.size.y + gizmo_panel.bounds_local.size.y + 0.005

# BlendLink XR logo — displayed above the mode panel
from bl_xr import Image as BLImage
bl_logo = BLImage(
    id="bl_logo",
    src="images/Blendlinkxr-logo.png",
    width=main_menu.bounds_local.size.x,
    intersects=None,
    style={"opacity": 0.9},
)
bl_logo.position = Vector((
    0,
    mode_panel.position.y + MODE_PANEL_BUTTON_SIZE + 0.003,
    0.002,
))


menu_group = Node(
    id="main_menu_group",
    child_nodes=[
        bl_logo,
        mode_panel,
        Node(
            id="main_menu_panels",
            child_nodes=[main_menu] + list(submenus.values()),
        ),
        anim_panel,
        gizmo_panel,
        mirror_panel,
        gp_color_panel,
    ],
)
menu_group.prevent_trigger_events_on_raycast = True
menu_group.style["visible"] = settings["view.show_main_menu"]

# hack to get controller pointer visibility
mode_panel.add_event_listener("pointer_main_press_start", lambda *x: None)
main_menu.add_event_listener("pointer_main_press_start", lambda *x: None)

for submenu in submenus.values():
    submenu.add_event_listener("pointer_main_press_start", lambda *x: None)

gp_color_panel.add_event_listener("pointer_main_press_start", lambda *x: None)

anim_panel.add_event_listener("pointer_main_press_start", lambda *x: None)
gizmo_panel.add_event_listener("pointer_main_press_start", lambda *x: None)
mirror_panel.add_event_listener("pointer_main_press_start", lambda *x: None)

submenu_tests = {
    "EDIT": lambda: bpy.context.view_layer.objects.active
    and bpy.context.view_layer.objects.active.mode == "EDIT"
    and bpy.context.view_layer.objects.active.type == "MESH",
    "PEN": lambda: tools.active_tool == "draw.stroke"
    and (not bpy.context.view_layer.objects.active or bpy.context.view_layer.objects.active.mode == "OBJECT"),
    "SHAPE": lambda: tools.active_tool == "draw.shape"
    and (not bpy.context.view_layer.objects.active or bpy.context.view_layer.objects.active.mode == "OBJECT"),
    "GP": lambda: tools.active_tool in ("draw.grease_pencil", "draw.gp_erase", "draw.gp_smooth", "draw.gp_line"),
    "SELECT": lambda: tools.active_tool == "select",
    "TRANSFORM_SPACE": lambda: tools.active_tool == "select" and settings["gizmo.transform_handles.type"] is not None,
}
mode_button_tests = {
    "OBJECT": lambda: True,
    "EDIT": lambda: bpy.context.view_layer.objects.active,
    "POSE": lambda: bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.type == "ARMATURE",
}


def on_update(self):
    self.rotation = xr_session.controller_alt_aim_rotation
    self.position = xr_session.controller_alt_aim_position + self.rotation @ Vector(
        (-BUTTON_SIZE * xr_session.viewer_scale, 0, 0)
    )

    for name, submenu in submenus.items():
        visibility_test = submenu_tests[name]
        status = True if visibility_test() else False
        submenu.style["visible"] = status

    for btn in mode_panel.child_nodes:
        btn_name = btn.tooltip.text
        visibility_test = mode_button_tests[btn_name]
        status = True if visibility_test() else False
        btn.style["visible"] = status

    mirror_panel.style["visible"] = settings["gizmo.mirror.enabled"]

    # Show color palette when any GP tool is active
    _gp_active = tools.active_tool in (
        "draw.grease_pencil", "draw.gp_erase", "draw.gp_smooth", "draw.gp_line")
    gp_color_panel.style["visible"] = _gp_active

    # Toggle color wheel gizmo with GP tools
    from .. import gizmos as _gizmos_mod
    if _gp_active and "color_wheel" not in _gizmos_mod.active_gizmos:
        from ..gizmos import enable_gizmo as _eg
        _eg("color_wheel")
        _cw = root.q("#color_wheel")
        if _cw:
            _cw.position = Vector((
                main_menu.bounds_local.max.x + 0.01,
                SUBMENU_Y_OFFSET - 0.15,
                SUBMENU_Z_OFFSET,
            ))
    elif not _gp_active and "color_wheel" in _gizmos_mod.active_gizmos:
        from ..gizmos import disable_gizmo as _dg
        _dg("color_wheel")

    ob = bpy.context.view_layer.objects.active
    proportional_edit_button.style["visible"] = ob and ob.mode == "EDIT" and ob.type == "MESH"


menu_group.update = on_update.__get__(menu_group)


def on_menu_toggle(self, event_name, event):
    menu_group.style["visible"] = not menu_group.style["visible"]

    settings["view.show_main_menu"] = not settings["view.show_main_menu"]
    save_settings_to_file()


def apply_handedness(hand):
    # mirror the buttons in the main menu
    new_nodes = []

    for i in range(0, len(main_menu.child_nodes) - 3, 2):  # leave the last row alone
        new_nodes.append(main_menu.child_nodes[i + 1])
        new_nodes.append(main_menu.child_nodes[i])

    new_nodes.append(main_menu.child_nodes[-2])
    new_nodes.append(main_menu.child_nodes[-1])

    main_menu.child_nodes.clear()
    main_menu.append_children(new_nodes)

    # move the subpanels to the other side of the main menu
    for submenu_name, submenu in submenus.items():
        p = Vector(submenu.position)

        if submenu_name == "SELECT":
            if hand == "right":
                p.x = -main_menu.bounds_local.max.x * 0.4
            else:
                p.x = main_menu.bounds_local.max.x
        elif submenu_name == "TRANSFORM_SPACE":
            if hand == "right":
                p.x = -main_menu.bounds_local.max.x * 0.74
            else:
                p.x = main_menu.bounds_local.max.x
        else:
            p.x = main_menu.bounds_local.max.x if hand == "right" else -submenu.bounds_local.max.x

        submenu.position = p


if bl_xr.main_hand != "right":  # assumed "right" while creating the DOM nodes
    apply_handedness(bl_xr.main_hand)


def on_setting_change(self, event_name, change: dict):
    if "app.main_hand" in change:
        apply_handedness(change["app.main_hand"])


def enable():
    root.append_child(menu_group)
    root.add_event_listener("fb.setting_change", on_setting_change)

    root.add_event_listener("button_b_alt_start", on_menu_toggle)


def disable():
    root.remove_child(menu_group)
    root.remove_event_listener("fb.setting_change", on_setting_change)

    root.remove_event_listener("button_b_alt_start", on_menu_toggle)
