# SPDX-License-Identifier: GPL-2.0-or-later

"""Shared Grease Pencil v3 utilities for all GP tools."""

import bpy
from mathutils import Vector

from ..settings_manager import settings
from ..utils import log, link_to_configured_collection

GP_OBJECT_NAME = "BlendLink Drawing"
GP_LAYER_NAME = "Draw"
GP_MATERIAL_NAME = "BL_GP_Stroke"

_gp_object = None


def get_or_create_gp_object():
    """Get or create the GP object. Sets it as active + selected.

    Uses bpy.ops.object.grease_pencil_add() to create the object so we get
    a proper GP material (is_grease_pencil=True with MaterialGPencilStyle).
    """
    global _gp_object

    if _gp_object is not None:
        try:
            _gp_object.name
            if _gp_object.name in bpy.context.scene.objects:
                _activate_gp_object(_gp_object)
                return _gp_object
        except ReferenceError:
            pass
        _gp_object = None

    obj = bpy.data.objects.get(GP_OBJECT_NAME)
    if obj is not None and obj.type == 'GREASEPENCIL':
        if obj.name in bpy.context.scene.objects:
            _gp_object = obj
            _activate_gp_object(obj)
            return obj

    # Create via operator to get proper GP material
    try:
        bpy.ops.object.grease_pencil_add(type='EMPTY')
        obj = bpy.context.view_layer.objects.active
        obj.name = GP_OBJECT_NAME
        obj.data.name = GP_OBJECT_NAME

        # Rename default layer
        if len(obj.data.layers) > 0:
            obj.data.layers[0].name = GP_LAYER_NAME
        else:
            obj.data.layers.new(GP_LAYER_NAME)

        # Move to configured collection
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        link_to_configured_collection(obj)

    except Exception as e:
        # Fallback: create manually (won't have GP material style)
        log.error("[GP] Operator failed, creating manually: {}".format(e))
        gp_data = bpy.data.grease_pencils.new(GP_OBJECT_NAME)
        obj = bpy.data.objects.new(GP_OBJECT_NAME, gp_data)
        link_to_configured_collection(obj)
        gp_data.layers.new(GP_LAYER_NAME)
        _ensure_gp_material(obj)

    _gp_object = obj
    _activate_gp_object(obj)
    log.info("[GP] Created: {}".format(GP_OBJECT_NAME))
    return obj


def get_gp_object():
    """Get existing GP object or None. Does NOT create."""
    global _gp_object

    if _gp_object is not None:
        try:
            _gp_object.name
            if _gp_object.name in bpy.context.scene.objects:
                return _gp_object
        except ReferenceError:
            pass
        _gp_object = None

    obj = bpy.data.objects.get(GP_OBJECT_NAME)
    if obj is not None and obj.type == 'GREASEPENCIL':
        if obj.name in bpy.context.scene.objects:
            _gp_object = obj
            return obj
    return None


def _activate_gp_object(obj):
    try:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
    except Exception:
        pass


def _ensure_gp_material(gp_obj):
    if len(gp_obj.data.materials) > 0:
        return
    # This fallback creates a regular material — won't have GP style
    # The proper path is get_or_create_gp_object() which uses the operator
    mat = bpy.data.materials.get(GP_MATERIAL_NAME)
    if mat is None:
        mat = bpy.data.materials.new(GP_MATERIAL_NAME)
        mat.diffuse_color = (0.1, 0.1, 0.1, 1.0)
    gp_obj.data.materials.append(mat)


def get_or_create_color_material(gp_obj, color):
    """Get or create a GP material with the given stroke color.

    GP materials must be created by copying an existing GP material
    (one with is_grease_pencil=True). Regular materials won't render
    as GP strokes.

    Returns the material slot index.
    """
    r, g, b, a = color

    # Check existing materials for a close color match
    for i, mat in enumerate(gp_obj.data.materials):
        if mat is None:
            continue
        if mat.is_grease_pencil and mat.grease_pencil:
            mc = mat.grease_pencil.color
            if (abs(mc[0] - r) < 0.02 and
                    abs(mc[1] - g) < 0.02 and
                    abs(mc[2] - b) < 0.02):
                return i

    # Find a GP material to copy from
    base_mat = None
    for mat in gp_obj.data.materials:
        if mat and mat.is_grease_pencil and mat.grease_pencil:
            base_mat = mat
            break

    if base_mat is None:
        # No GP material exists — can't create colored strokes properly
        log.error("[GP] No base GP material to copy from")
        return 0

    # Copy the base material and set the new color
    name = "BL_GP_{:.0f}_{:.0f}_{:.0f}".format(r * 255, g * 255, b * 255)
    existing = bpy.data.materials.get(name)
    if existing and existing.is_grease_pencil:
        gp_obj.data.materials.append(existing)
        return len(gp_obj.data.materials) - 1

    new_mat = base_mat.copy()
    new_mat.name = name
    new_mat.grease_pencil.color = (r, g, b, a)
    gp_obj.data.materials.append(new_mat)
    log.info("[GP] Created color material: {} ({:.1f},{:.1f},{:.1f})".format(name, r, g, b))
    return len(gp_obj.data.materials) - 1


def get_active_drawing(gp_obj):
    """Get the drawing for the current frame, creating if needed."""
    gp_data = gp_obj.data
    if len(gp_data.layers) == 0:
        gp_data.layers.new(GP_LAYER_NAME)

    layer = gp_data.layers.active
    if layer is None:
        layer = gp_data.layers[0]

    frame_num = bpy.context.scene.frame_current
    frame = None
    for f in layer.frames:
        if f.frame_number == frame_num:
            frame = f
            break

    if frame is None:
        frame = layer.frames.new(frame_num)

    return frame.drawing


def world_to_local(gp_obj, world_pos):
    """Convert world position to GP object local space."""
    return gp_obj.matrix_world.inverted_safe() @ world_pos


def local_to_world(gp_obj, local_pos):
    """Convert GP local space to world position."""
    return gp_obj.matrix_world @ Vector(local_pos)


def get_pressure(event_value):
    """Get pressure from MX Ink tip force or fallback."""
    tip_force = settings.get("mx_ink.tip_force", 0.0)
    if tip_force > 0.01:
        return tip_force
    return max(event_value, 0.3)


def get_stroke_count():
    """Get the number of strokes in the current drawing."""
    gp_obj = get_gp_object()
    if gp_obj is None:
        return 0
    try:
        drawing = get_active_drawing(gp_obj)
        return len(drawing.strokes)
    except Exception:
        return 0


def get_layer_names():
    """Get list of layer names from the GP object."""
    gp_obj = get_gp_object()
    if gp_obj is None:
        return []
    try:
        return [layer.name for layer in gp_obj.data.layers]
    except Exception:
        return []


def get_active_layer_name():
    """Get the active layer name."""
    gp_obj = get_gp_object()
    if gp_obj is None:
        return ""
    try:
        layer = gp_obj.data.layers.active
        return layer.name if layer else ""
    except Exception:
        return ""


def add_layer(name):
    """Add a new layer to the GP object."""
    gp_obj = get_or_create_gp_object()
    try:
        gp_obj.data.layers.new(name)
        log.info("[GP] Added layer: {}".format(name))
        return True
    except Exception as e:
        log.error("[GP] Error adding layer: {}".format(e))
        return False


def set_active_layer(name):
    """Set the active layer by name."""
    gp_obj = get_gp_object()
    if gp_obj is None:
        return False
    try:
        for i, layer in enumerate(gp_obj.data.layers):
            if layer.name == name:
                gp_obj.data.layers.active_index = i
                log.info("[GP] Active layer: {}".format(name))
                return True
    except Exception:
        pass
    return False
