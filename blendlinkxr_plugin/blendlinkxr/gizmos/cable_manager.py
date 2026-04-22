import bpy

from bl_xr import root, Text

from mathutils import Vector
from blendlinkxr import settings
from blendlinkxr import tools
from blendlinkxr.utils import get_selected_objects


def _format_length(meters: float) -> str:
    """Convert a raw Blender length (metres) to a human-readable scene-unit string."""
    unit_settings = bpy.context.scene.unit_settings
    return bpy.utils.units.to_string(
        unit_settings.system,
        "LENGTH",
        meters,
        precision=3,
        split_unit=unit_settings.use_separate,
    )


def _update_length_text(self):
    """Update the length label that lives on the alt controller."""
    selected_curves = [ob for ob in get_selected_objects() if ob.type == "CURVE"]

    from collections import defaultdict
    dia_groups = defaultdict(list)

    for ob in selected_curves:
        splines = ob.data.splines
        if not splines:
            continue
        dia = ob.data.bevel_depth * 2
        length = splines[0].calc_length()

        dia_to_use = None
        for existing_dia in dia_groups:
            existing_dia_f = float(existing_dia)
            if abs(existing_dia_f - dia) < 0.001:
                dia_to_use = existing_dia
                break

        if dia_to_use is None:
            dia_to_use = f"{dia:.6f}"

        dia_groups[dia_to_use].append(length)

    n = len(selected_curves)
    if n == 0:
        text = "== 0 cables selected =="
    else:
        cable_word = "cable" if n == 1 else "cables"
        text = f"== {n} {cable_word} selected ==\n"

        if dia_groups:
            sorted_dias = sorted(dia_groups.keys())
            for dia in sorted_dias:
                lengths = dia_groups[dia]
                count = len(lengths)
                total_len = sum(lengths)
                dia_str = _format_length(float(dia))
                len_str = _format_length(total_len)
                text += f"Dia: {dia_str}, Cables: {count}, Total Length: {len_str}\n"
            text = text.rstrip()  # remove trailing newline

    self.text = text


def _update_diameter_text(self):
    """Update the diameter label that lives on the main controller."""
    cursor = root.q("#cursor_main")
    if cursor is None:
        self.text = ""
        return

    if settings["demo.cable_manager_use_fixed_diameter"] and tools.active_tool == "draw.stroke":
        diameter = settings["demo.cable_manager_diameter"]
        cursor.size_world = diameter / 2.0

    diameter = 2.0 * cursor.size_world
    self.text = _format_length(diameter)


# ── UI nodes ────────────────────────────────────────────────────────────────

length_text = Text(
    "",
    id="cable_manager_length_text",
    font_size=20,
    intersects=None,
    position=Vector((0.06, -0.05, 0)),
    style={"depth_test": False},
)
length_text.scale = 0.0005
length_text.update = _update_length_text.__get__(length_text)

diameter_text = Text(
    "",
    id="cable_manager_diameter_text",
    font_size=30,
    intersects=None,
    position=Vector((0, 0.06, 0)),
    style={"depth_test": False},
)
diameter_text.scale = 0.0005
diameter_text.update = _update_diameter_text.__get__(diameter_text)


# ── Lifecycle ────────────────────────────────────────────────────────────────

def enable_gizmo():
    controller_alt = root.q("#controller_alt")
    controller_main = root.q("#controller_main")

    if controller_alt and controller_main:
        controller_alt.append_child(length_text)
        controller_main.append_child(diameter_text)


def disable_gizmo():
    controller_alt = root.q("#controller_alt")
    controller_main = root.q("#controller_main")

    if controller_alt and length_text in controller_alt.child_nodes:
        controller_alt.remove_child(length_text)
    if controller_main and diameter_text in controller_main.child_nodes:
        controller_main.remove_child(diameter_text)
