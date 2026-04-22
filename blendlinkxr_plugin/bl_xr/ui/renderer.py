# SPDX-License-Identifier: GPL-2.0-or-later

from ..dom import Node, root
from bl_xr import xr_session
from bl_xr.consts import WHITE, BLACK

import bpy
import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader
import traceback
import time
from mathutils import Matrix

from .shaders import (
    ImageFragmentShader,
    create_shader_from_code,
    build_shader_from_config,
    FLAT_COLOR_RECT_SHADER,
    TEXTURE_RECT_SHADER,
    _USE_MODERN_API,
)
from ..utils import log

draw_handle = None

texture_rect_shader = None
flat_color_rect_shader = None
flat_color_misc_shader = None
_mvp_ubo = None

EDGE_SOFTNESS = 0.001

if not bpy.app.background:
    # Build complete shaders from unified configs
    flat_color_shaders = build_shader_from_config(FLAT_COLOR_RECT_SHADER)
    texture_rect_shaders = build_shader_from_config(TEXTURE_RECT_SHADER)

    flat_color_rect_shader = create_shader_from_code(
        flat_color_shaders["vertex"],
        flat_color_shaders["fragment"],
        "flat_color_rectangle_shader",
        FLAT_COLOR_RECT_SHADER,
    )

    texture_rect_shader = create_shader_from_code(
        texture_rect_shaders["vertex"],
        texture_rect_shaders["fragment"],
        "texture_rectangle_shader",
        TEXTURE_RECT_SHADER,
    )

    flat_color_misc_shader = "UNIFORM_COLOR" if bpy.app.version >= (4, 0, 0) else "3D_UNIFORM_COLOR"
    flat_color_misc_shader = gpu.shader.from_builtin(flat_color_misc_shader)


def _update_mvp_ubo(shader):
    """Upload the current GPU matrix stack MVP into the UBO and bind it. No-op on legacy API."""
    global _mvp_ubo
    if not _USE_MODERN_API:
        return
    mvp = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    data = np.array(mvp, dtype="f4").T.tobytes()
    if _mvp_ubo is None:
        _mvp_ubo = gpu.types.GPUUniformBuf(data)
    else:
        _mvp_ubo.update(data)
    shader.uniform_block("fb_mvp", _mvp_ubo)


even_frame = True
animation_frame_listeners = {}  # ordered dict of (frame_id, callback)
last_animation_listener_id = 0
last_animation_frame_timestamp = 0  # ms


def draw_frame(context):
    global even_frame, last_animation_frame_timestamp

    if bpy.app.version < (5, 1):  # hack: Blender 5.0 and older didn't set a context in XR
        bpy.context = context

    if even_frame:
        call_animation_frame_listeners()
        update(root)

    if not bpy.app.background:
        draw(root)

    even_frame = not even_frame
    last_animation_frame_timestamp = time.time() * 1000


def request_animation_frame(callback):
    global last_animation_listener_id

    last_animation_listener_id += 1
    animation_frame_listeners[last_animation_listener_id] = callback

    return last_animation_listener_id


def cancel_animation_frame(request_id):
    global last_animation_listener_id

    if request_id in animation_frame_listeners:
        del animation_frame_listeners[request_id]

    if request_id == last_animation_listener_id:
        last_animation_listener_id -= 1


def call_animation_frame_listeners():
    if not animation_frame_listeners:
        return

    listeners_this_frame = list(animation_frame_listeners.items())
    for request_id, callback in listeners_this_frame:
        try:
            callback(last_animation_frame_timestamp)
        except Exception as e:
            log.error(f"Error in animation frame listener {request_id}: {''.join(traceback.format_exc())}")
        finally:
            del animation_frame_listeners[request_id]


def update(node: Node):
    if not node.get_computed_style("visible", True):
        return

    try:
        if hasattr(node, "update") and callable(node.update):
            node.update()

        for child in node.child_nodes:
            update(child)
    except:
        log.error(traceback.format_exc())


def draw(node: Node):
    if not node.get_computed_style("visible", True):
        return

    try:
        with gpu.matrix.push_pop():
            matrix_local = node.matrix_local
            if node.get_computed_style("fixed_scale", False):
                loc, rot, scale = matrix_local.decompose()
                matrix_local = Matrix.LocRotScale(loc, rot, scale * xr_session.viewer_scale)

            gpu.matrix.multiply_matrix(matrix_local)

            if node.get_computed_style("depth_test", True):
                gpu.state.depth_test_set("LESS_EQUAL")
                gpu.state.depth_mask_set(True)
            else:
                gpu.state.depth_test_set("NONE")
                gpu.state.depth_mask_set(False)

            gpu.state.blend_set("ALPHA")

            draw_node(node)

            for child in node.child_nodes:
                draw(child)
    except Exception as e:
        log.error(traceback.format_exc())


def draw_node(node: Node):
    if hasattr(node, "draw") and callable(node.draw):
        node.draw()
    elif hasattr(node, "mesh"):
        if hasattr(node, "_shader"):
            shader = node._shader
            shader.bind()
        else:
            shader = flat_color_misc_shader
            shader.bind()
            shader.uniform_float(
                "color", node.get_computed_style("color", WHITE)[:3] + (node.get_computed_style("opacity", 1),)
            )

        if not hasattr(node, "_batch"):
            if len(node.mesh.faces) > 0:
                node._batch = batch_for_shader(shader, "TRIS", {"pos": node.mesh.vertices}, indices=node.mesh.faces)
            else:
                node._batch = batch_for_shader(shader, "LINES", {"pos": node.mesh.vertices})

        node._batch.draw(shader)
    elif hasattr(node, "_shader") and isinstance(node._shader, ImageFragmentShader):
        node._shader.bind()
        shader = node._shader.shader
        _update_mvp_ubo(shader)

        bounds = node.bounds_local.size
        W, H = bounds.x, bounds.y

        if not hasattr(node, "_batch"):
            node._batch = batch_for_shader(
                shader,
                "TRIS",
                {
                    "fb_position": [(0, 0, 0), (0, H, 0), (W, H, 0), (W, H, 0), (W, 0, 0), (0, 0, 0)],
                    "fb_texCoord": ((0, 0), (0, 1), (1, 1), (1, 1), (1, 0), (0, 0)),
                },
            )

        node._batch.draw(shader)
    else:
        background = node.get_computed_style("background")
        border = node.get_computed_style("border")
        border_radius = node.get_computed_style("border_radius")

        if not background and not border and not border_radius and not hasattr(node, "_texture"):
            return

        shader = texture_rect_shader if hasattr(node, "_texture") else flat_color_rect_shader
        shader.bind()
        _update_mvp_ubo(shader)

        if hasattr(node, "_texture"):
            shader.uniform_sampler("fb_image", node._texture)
            shader.uniform_float(
                "fb_color", node.get_computed_style("color", WHITE)[:3] + (node.get_computed_style("opacity", 1),)
            )

        if background:
            shader.uniform_float("fb_fillColor", background[:3] + (node.get_computed_style("opacity", 1),))
        else:
            shader.uniform_float("fb_fillColor", (0.0, 0.0, 0.0, 0.0))

        if border:
            if isinstance(border, tuple) and len(border) == 2:
                border_width, border_color = border
            elif isinstance(border, tuple):
                border_width = 0.01
                border_color = border
            else:
                border_width = border
                border_color = BLACK

            shader.uniform_float("fb_borderWidth", border_width)
            shader.uniform_float("fb_borderColor", border_color)
        else:
            shader.uniform_float("fb_borderWidth", 0)
            shader.uniform_float("fb_borderColor", (0.0, 0.0, 0.0, 0.0))

        if border_radius:
            shader.uniform_float("fb_borderRadius", border_radius)
        else:
            shader.uniform_float("fb_borderRadius", 0)

        bounds = node.bounds_local.size
        W, H = bounds.x, bounds.y

        shader.uniform_float("fb_edgeSoftness", EDGE_SOFTNESS)
        shader.uniform_float("fb_size", (W - 2 * EDGE_SOFTNESS, H - 2 * EDGE_SOFTNESS))
        shader.uniform_float("fb_boxLocation", (W * 0.5, H * 0.5))

        if not hasattr(node, "_batch"):
            if shader == texture_rect_shader:
                # this will be a quad, with the pos
                node._batch = batch_for_shader(
                    shader,
                    "TRIS",
                    {
                        "fb_position": [(0, 0, 0), (0, H, 0), (W, H, 0), (W, H, 0), (W, 0, 0), (0, 0, 0)],
                        "fb_texCoord": ((0, 0), (0, 1), (1, 1), (1, 1), (1, 0), (0, 0)),
                    },
                )
            else:
                node._batch = batch_for_shader(
                    shader,
                    "TRIS",
                    {
                        "fb_position": [(0, 0, 0), (0, H, 0), (W, H, 0), (W, H, 0), (W, 0, 0), (0, 0, 0)],
                    },
                    indices=[(0, 1, 2), (3, 4, 5)],
                )

        node._batch.draw(shader)


def on_draw_start(context):
    global draw_handle

    if bpy.app.background:
        return

    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, "XR")

    draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_frame, (context,), "XR", "POST_VIEW")
