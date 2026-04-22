# SPDX-License-Identifier: GPL-2.0-or-later

"""MX Ink stylus 3D model gizmo — glossy rendered pen model.

Renders the MX Ink mesh with a custom Blinn-Phong shader that gives
a glossy, reflective appearance. Normals are computed from face geometry
at load time. The shader uses a fixed light direction relative to the
camera for consistent specular highlights.
"""

import json
import os
import bpy

from bl_xr import root, xr_session
from bl_xr import Node
from bl_xr.ui.components import Mesh
from bl_xr.consts import VEC_ONE

from mathutils import Vector, Quaternion
import gpu
from gpu_extras.batch import batch_for_shader

# --- Colors ---
MX_INK_BASE_COLOR = (0.08, 0.08, 0.10)  # dark charcoal base
MX_INK_SPEC_COLOR = (0.6, 0.65, 0.75)   # cool white specular
MX_INK_AMBIENT = 0.15
MX_INK_DIFFUSE = 0.55
MX_INK_SPECULAR = 0.8
MX_INK_SHININESS = 48.0

_mesh_data = None
_pen_node = None
_glossy_shader = None
_glossy_batch = None


def _load_mesh_data():
    """Load the pre-exported mesh data from JSON."""
    global _mesh_data

    if _mesh_data is not None:
        return _mesh_data

    json_path = os.path.join(os.path.dirname(__file__), "mx_ink_mesh_data.json")
    if not os.path.exists(json_path):
        print("[MX Ink Model] Mesh data not found: {}".format(json_path))
        return None

    with open(json_path, "r") as f:
        _mesh_data = json.load(f)

    print("[MX Ink Model] Loaded {} verts, {} faces".format(
        _mesh_data["vert_count"], _mesh_data["face_count"]))
    return _mesh_data


def _compute_normals(verts, faces):
    """Compute per-vertex normals by averaging adjacent face normals."""
    from mathutils import Vector as V

    normals = [V((0, 0, 0)) for _ in range(len(verts))]
    counts = [0] * len(verts)

    for f in faces:
        if len(f) < 3:
            continue
        v0 = V(verts[f[0]])
        v1 = V(verts[f[1]])
        v2 = V(verts[f[2]])
        edge1 = v1 - v0
        edge2 = v2 - v0
        face_normal = edge1.cross(edge2)
        if face_normal.length > 1e-8:
            face_normal.normalize()
        for idx in f:
            normals[idx] = normals[idx] + face_normal
            counts[idx] += 1

    for i in range(len(normals)):
        if counts[i] > 0:
            normals[i] = normals[i] / counts[i]
            if normals[i].length > 1e-8:
                normals[i].normalize()
            else:
                normals[i] = V((0, 0, 1))

    return [tuple(n) for n in normals]


def _build_glossy_shader():
    """Build the Blinn-Phong glossy shader."""
    global _glossy_shader

    if _glossy_shader is not None:
        return _glossy_shader

    if bpy.app.background:
        return None

    vert_src = """
void main() {
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
    frag_normal = normal;
    frag_pos = pos;
}
"""
    frag_src = """
void main() {
    vec3 N = normalize(frag_normal);
    vec3 L = normalize(vec3(0.3, 0.5, 1.0));
    vec3 V = normalize(vec3(0.0, 0.0, 1.0));
    vec3 H = normalize(L + V);

    float diff = max(dot(N, L), 0.0);
    float spec = pow(max(dot(N, H), 0.0), shininess);

    vec3 ambient_c = base_color * ambient;
    vec3 diffuse_c = base_color * diffuse * diff;
    vec3 spec_c = spec_color * specular * spec;

    vec3 color = ambient_c + diffuse_c + spec_c;
    fragColor = vec4(color, 1.0);
}
"""

    try:
        from bl_xr.ui.shaders import _USE_MODERN_API

        if _USE_MODERN_API:
            shader_info = gpu.types.GPUShaderCreateInfo()
            shader_info.vertex_in(0, 'VEC3', 'pos')
            shader_info.vertex_in(1, 'VEC3', 'normal')

            iface = gpu.types.GPUStageInterfaceInfo("mx_ink_iface")
            iface.smooth('VEC3', 'frag_normal')
            iface.smooth('VEC3', 'frag_pos')
            shader_info.vertex_out(iface)

            shader_info.fragment_out(0, 'VEC4', 'fragColor')

            shader_info.push_constant('VEC3', 'base_color')
            shader_info.push_constant('VEC3', 'spec_color')
            shader_info.push_constant('FLOAT', 'ambient')
            shader_info.push_constant('FLOAT', 'diffuse')
            shader_info.push_constant('FLOAT', 'specular')
            shader_info.push_constant('FLOAT', 'shininess')

            shader_info.vertex_source(
                "uniform mat4 ModelViewProjectionMatrix;\n" + vert_src
                if not hasattr(shader_info, 'typedef_source') else vert_src
            )

            # For modern API, we need the MVP UBO
            shader_info.typedef_source(
                "struct ModelViewProjectionMatrixBlock { mat4 ModelViewProjectionMatrix; };")
            shader_info.uniform_buf(0, "ModelViewProjectionMatrixBlock", "fb_mvp")

            # Rewrite shader to use UBO
            vert_modern = """
void main() {
    gl_Position = fb_mvp.ModelViewProjectionMatrix * vec4(pos, 1.0);
    frag_normal = normal;
    frag_pos = pos;
}
"""
            shader_info.vertex_source(vert_modern)
            shader_info.fragment_source(frag_src)

            _glossy_shader = gpu.shader.create_from_info(shader_info)
        else:
            # Legacy path
            legacy_vert = """
uniform mat4 ModelViewProjectionMatrix;
in vec3 pos;
in vec3 normal;
out vec3 frag_normal;
out vec3 frag_pos;
""" + vert_src

            legacy_frag = """
in vec3 frag_normal;
in vec3 frag_pos;
out vec4 fragColor;
uniform vec3 base_color;
uniform vec3 spec_color;
uniform float ambient;
uniform float diffuse;
uniform float specular;
uniform float shininess;
""" + frag_src

            _glossy_shader = gpu.types.GPUShader(legacy_vert, legacy_frag)

        print("[MX Ink Model] Glossy shader compiled")

    except Exception as e:
        print("[MX Ink Model] Shader compilation failed: {}".format(e))
        print("[MX Ink Model] Falling back to flat color")
        _glossy_shader = None

    return _glossy_shader


def _build_glossy_batch(verts, faces, normals):
    """Build the GPU batch with positions and normals."""
    global _glossy_batch

    shader = _build_glossy_shader()
    if shader is None:
        return None

    # Expand to per-face-vertex (unindexed) for correct normals
    positions = []
    norms = []
    for f in faces:
        for idx in f:
            positions.append(verts[idx])
            norms.append(normals[idx])

    _glossy_batch = batch_for_shader(
        shader, 'TRIS',
        {"pos": positions, "normal": norms},
    )
    return _glossy_batch


class MXInkPenNode(Node):
    """Node that renders the MX Ink stylus model with glossy shading."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        data = _load_mesh_data()
        if data is None:
            self.mesh = Mesh(vertices=[], faces=[])
            return

        verts = [tuple(v) for v in data["vertices"]]
        faces = [tuple(f) for f in data["faces"]]

        # Compute normals for glossy shading
        normals = _compute_normals(verts, faces)

        # Store for batch building (deferred to first draw)
        self._verts = verts
        self._faces = faces
        self._normals = normals

        # Don't set self.mesh — we'll use custom draw()
        self.style["fixed_scale"] = True
        self.intersects = None

    def draw(self):
        """Custom draw using the glossy shader."""
        global _glossy_batch

        if not hasattr(self, '_verts'):
            return

        shader = _build_glossy_shader()
        if shader is None:
            # Fallback: draw as flat color
            self.mesh = Mesh(vertices=self._verts, faces=self._faces)
            self.style["color"] = MX_INK_BASE_COLOR + (1.0,)
            del self._verts
            return

        if _glossy_batch is None:
            _build_glossy_batch(self._verts, self._faces, self._normals)

        if _glossy_batch is None:
            return

        shader.bind()

        # Upload MVP UBO for modern API
        try:
            from bl_xr.ui.renderer import _update_mvp_ubo
            _update_mvp_ubo(shader)
        except Exception:
            pass

        shader.uniform_float("base_color", MX_INK_BASE_COLOR)
        shader.uniform_float("spec_color", MX_INK_SPEC_COLOR)
        shader.uniform_float("ambient", MX_INK_AMBIENT)
        shader.uniform_float("diffuse", MX_INK_DIFFUSE)
        shader.uniform_float("specular", MX_INK_SPECULAR)
        shader.uniform_float("shininess", MX_INK_SHININESS)

        _glossy_batch.draw(shader)

    def update(self):
        """Track the main hand aim pose (= tip pose on MX Ink)."""
        from math import pi

        self.position = Vector(xr_session.controller_main_aim_position)
        base_rot = Quaternion(xr_session.controller_main_aim_rotation)
        flip = Quaternion((0, 0, 1), pi)
        self.rotation = base_rot @ flip


def enable_gizmo():
    global _pen_node

    if _pen_node is not None:
        return

    _pen_node = MXInkPenNode(id="mx_ink_pen_model")
    root.append_child(_pen_node)
    _hide_default_controller_visual()
    print("[MX Ink Model] Glossy pen model enabled")


def disable_gizmo():
    global _pen_node, _glossy_batch

    if _pen_node is None:
        return

    root.remove_child(_pen_node)
    _pen_node = None
    _glossy_batch = None
    _show_default_controller_visual()
    print("[MX Ink Model] Pen model disabled")


def _hide_default_controller_visual():
    controller_main = root.q("#controller_main")
    if controller_main:
        controller_main.style["visible"] = False
    controller_bg = root.q("#controller_main_bg")
    if controller_bg:
        controller_bg.style["visible"] = False
    try:
        import bpy
        right_ctrl = bpy.data.objects.get("BL-Controller-Right")
        if right_ctrl:
            right_ctrl.hide_viewport = True
            right_ctrl.empty_display_size = 0
    except Exception:
        pass


def _show_default_controller_visual():
    controller_main = root.q("#controller_main")
    if controller_main:
        controller_main.style["visible"] = True
    controller_bg = root.q("#controller_main_bg")
    if controller_bg:
        controller_bg.style["visible"] = True
    try:
        import bpy
        right_ctrl = bpy.data.objects.get("BL-Controller-Right")
        if right_ctrl:
            right_ctrl.empty_display_size = 1
    except Exception:
        pass
