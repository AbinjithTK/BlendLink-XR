import bpy
import bmesh
from bpy.types import PoseBone
from bmesh.types import BMVert, BMEdge, BMFace

from bl_xr.utils import get_bmesh, get_bmesh_elements

import logging


def set_select_state_all(state):
    from blendlinkxr.utils import log

    ob = bpy.context.view_layer.objects.active
    if ob is None:
        return False

    if ob.mode == "OBJECT":
        for prev_ob in get_selected_objects():
            prev_ob.select_set(state)
    elif ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            mesh = ob.data
            el = get_bmesh_elements(ob)

            for e in el:
                e.select_set(state)
            bmesh.update_edit_mesh(mesh)
            log.debug(f"SET edit mesh select to: {state}")
        elif ob.type == "CURVE":
            curve = ob.data
            if len(curve.splines) == 0:
                return

            spline = curve.splines[0]
            for v in spline.points:
                v.select = state
        elif ob.type == "ARMATURE":
            if bpy.app.version >= (5, 0, 0):
                if ob.mode == "POSE":
                    for bone in ob.pose.bones:
                        bone.select = state
                else:
                    for bone in ob.data.edit_bones:
                        bone.select = state
                        bone.select_head = state
                        bone.select_tail = state
            else:
                bones = ob.data.edit_bones if ob.mode == "EDIT" else ob.data.bones

                for bone in bones:
                    bone.select = state
                    bone.select_head = state
                    bone.select_tail = state


def set_select_state(elements, state):
    from blendlinkxr.utils import log

    ob = bpy.context.view_layer.objects.active
    if ob is None:
        return False

    if ob.mode == "OBJECT":
        for prev_ob in elements:
            prev_ob.select_set(state)
    elif ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            mesh = ob.data
            bm = get_bmesh()

            for i, el_type in elements:
                if el_type == BMVert:
                    e = bm.verts[i]
                elif el_type == BMEdge:
                    e = bm.edges[i]
                elif el_type == BMFace:
                    e = bm.faces[i]

                e.select_set(state)
            bmesh.update_edit_mesh(mesh)
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"SET {[e.index for e in elements]} in edit mesh select to {state}")
        elif ob.type == "CURVE":
            for v in elements:
                v.select = state
        elif ob.type == "ARMATURE":
            for bone, el_type in elements:
                if bpy.app.version >= (5, 0, 0):
                    bone.select = state if el_type == "BOTH" else False
                    if not isinstance(bone, PoseBone):
                        bone.select_head = state if el_type in ("HEAD", "BOTH") else False
                        bone.select_tail = state if el_type in ("TAIL", "BOTH") else False
                else:
                    bone = bone.bone if isinstance(bone, PoseBone) else bone
                    bone.select = state if el_type == "BOTH" else False
                    bone.select_head = state if el_type in ("HEAD", "BOTH") else False
                    bone.select_tail = state if el_type in ("TAIL", "BOTH") else False


def get_selected_objects():
    if hasattr(bpy.context, "selected_objects"):
        return set(bpy.context.selected_objects)

    return set(o for o in bpy.context.scene.objects if o.select_get(view_layer=bpy.context.view_layer))
