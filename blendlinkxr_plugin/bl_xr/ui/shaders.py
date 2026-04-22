import bpy
import gpu


# Use modern API if Blender 5.0+ OR if Vulkan backend is enabled in Blender 4.5+
def _should_use_modern_api():
    from bl_xr.utils import log

    if bpy.app.version >= (5, 0, 0):
        return True
    # Check if Vulkan backend is enabled (Blender 4.5+)
    if bpy.app.version >= (4, 5, 0):
        prefs = bpy.context.preferences
        if hasattr(prefs, "system") and hasattr(prefs.system, "gpu_backend"):
            log.info(f"GPU Backend: {prefs.system.gpu_backend}")
            return prefs.system.gpu_backend == "VULKAN"
    return False


_USE_MODERN_API = _should_use_modern_api()

MVP_TYPEDEF = "struct ModelViewProjectionMatrixBlock { mat4 ModelViewProjectionMatrix; };"
MVP_UBO = [(0, "ModelViewProjectionMatrixBlock", "fb_mvp")]


def _build_legacy_declarations(shader_config, include_fragment_io=False):
    """Build GLSL declarations from shader config for legacy API."""
    lines = []

    # MVP is always required and injected automatically by Blender on the legacy path
    lines.append("uniform mat4 ModelViewProjectionMatrix;")

    # Uniforms
    type_map = {"MAT4": "mat4", "VEC4": "vec4", "VEC3": "vec3", "VEC2": "vec2", "FLOAT": "float", "INT": "int"}
    for uniform_name, uniform_type in shader_config.get("uniforms", []):
        glsl_type = type_map.get(uniform_type, uniform_type.lower())
        lines.append(f"uniform {glsl_type} {uniform_name};")

    # Samplers
    for sampler_name in shader_config.get("samplers", []):
        lines.append(f"uniform sampler2D {sampler_name};")

    # Vertex inputs (only for vertex shaders)
    for attr_name, attr_type in shader_config.get("vertex_in", []):
        glsl_type = type_map.get(attr_type, attr_type.lower())
        lines.append(f"in {glsl_type} {attr_name};")

    # Vertex outputs / Fragment inputs
    if include_fragment_io:
        for var_name, var_type in shader_config.get("vertex_out", []):
            glsl_type = type_map.get(var_type, var_type.lower())
            lines.append(f"in {glsl_type} {var_name};")
        lines.append("out vec4 fragColor;")
    else:
        for var_name, var_type in shader_config.get("vertex_out", []):
            glsl_type = type_map.get(var_type, var_type.lower())
            lines.append(f"out {glsl_type} {var_name};")

    return "\n".join(lines) + ("\n" if lines else "")


def _build_shader(shader_body, shader_config, is_fragment=False):
    """Build complete shader code with declarations for legacy API or clean code for modern API."""
    if _USE_MODERN_API:
        return shader_body

    declarations = _build_legacy_declarations(shader_config, include_fragment_io=is_fragment)
    shader_body = shader_body.replace("fb_mvp.ModelViewProjectionMatrix", "ModelViewProjectionMatrix")
    return declarations + shader_body


# Core shader functions (same for all versions)
flat_color_pixel_fn = """
vec4 getInsideColor(float distance, float isOutside) {
    // this is effectively: color = (isOutside ? fb_fillColor : vec4(0.0))
    return mix(fb_fillColor, vec4(0.0), isOutside);
}
"""

texture_pixel_fn = """
vec4 getInsideColor(float distance, float isOutside) {
    // fill transparent regions with color - https://gamedev.stackexchange.com/a/164523
    vec4 insideColor = texture(fb_image, fb_fragTexCoord);
    insideColor = (insideColor * insideColor.w) + (fb_fillColor * (1 - insideColor.w));
    insideColor *= fb_color;

    // this is effectively: color = (isOutside ? insideColor : vec4(0.0))
    return mix(insideColor, vec4(0.0), isOutside);
}
"""

fragment_shader_common = """
// from https://iquilezles.org/articles/distfunctions
float sdRoundBox(vec2 p, vec2 b, float r) {
    return length(max(abs(p) - b + r, 0.0)) - r;
}

float sdBox(vec2 p, vec2 b) {
    vec2 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
}

vec4 applyBorder(float distance, float isOutside, vec4 insideColor) {
    float w = mix(fb_borderWidth, fb_edgeSoftness, isOutside);

    float smoothedAlpha = 1.0 - smoothstep(-fb_edgeSoftness, fb_edgeSoftness, abs(distance) - w);
    return mix(insideColor, vec4(fb_borderColor.xyz, fb_borderColor.a * smoothedAlpha), smoothedAlpha);
}

vec4 drawBox(vec2 fragCoord) {
    float distance = 0.0;
    if (fb_borderRadius > 0.001) {
        distance = sdRoundBox(fb_boxLocation - fragCoord.xy, fb_size * 0.5, fb_borderRadius);
    } else {
        distance = sdBox(fb_boxLocation - fragCoord.xy, fb_size/2.0);
    }

    float isOutside = step(0, distance); // 1 if outside, 0 if inside

    vec4 finalColor = getInsideColor(distance, isOutside);
    if (fb_borderWidth > 0.001) {
        finalColor = applyBorder(distance, isOutside, finalColor);
    }

    return finalColor;
}

void main() {
    fragColor = drawBox(fb_pos.xy);
}
"""

# Complete shader definitions with code and configuration
FLAT_COLOR_RECT_SHADER = {
    "vertex_shader": """
void main() {
    fb_pos = fb_position;
    gl_Position = fb_mvp.ModelViewProjectionMatrix * vec4(fb_position, 1.0);
}
""",
    "fragment_shader": flat_color_pixel_fn + "\n" + fragment_shader_common,
    "vertex_in": [
        ("fb_position", "VEC3"),
    ],
    "vertex_out": [
        ("fb_pos", "VEC3"),
    ],
    "uniforms": [
        ("fb_fillColor", "VEC4"),
        ("fb_borderColor", "VEC4"),
        ("fb_borderWidth", "FLOAT"),
        ("fb_borderRadius", "FLOAT"),
        ("fb_edgeSoftness", "FLOAT"),
        ("fb_size", "VEC2"),
        ("fb_boxLocation", "VEC2"),
    ],
    "samplers": [],
    "typedef_source": MVP_TYPEDEF,
    "ubo": MVP_UBO,
}

TEXTURE_RECT_SHADER = {
    "vertex_shader": """
void main() {
    fb_pos = fb_position;
    gl_Position = fb_mvp.ModelViewProjectionMatrix * vec4(fb_position, 1.0);
    fb_fragTexCoord = fb_texCoord;
}
""",
    "fragment_shader": texture_pixel_fn + "\n" + fragment_shader_common,
    "vertex_in": [
        ("fb_position", "VEC3"),
        ("fb_texCoord", "VEC2"),
    ],
    "vertex_out": [
        ("fb_pos", "VEC3"),
        ("fb_fragTexCoord", "VEC2"),
    ],
    "uniforms": [
        ("fb_fillColor", "VEC4"),
        ("fb_borderColor", "VEC4"),
        ("fb_borderWidth", "FLOAT"),
        ("fb_borderRadius", "FLOAT"),
        ("fb_edgeSoftness", "FLOAT"),
        ("fb_size", "VEC2"),
        ("fb_boxLocation", "VEC2"),
        ("fb_color", "VEC4"),
    ],
    "samplers": ["fb_image"],
    "typedef_source": MVP_TYPEDEF,
    "ubo": MVP_UBO,
}

IMAGE_SHADER = {
    "vertex_shader": """
void main() {
    gl_Position = fb_mvp.ModelViewProjectionMatrix * vec4(fb_position, 1.0);
    fb_fragTexCoord = fb_texCoord;
}
""",
    "vertex_in": [
        ("fb_position", "VEC3"),
        ("fb_texCoord", "VEC2"),
    ],
    "vertex_out": [
        ("fb_fragTexCoord", "VEC2"),
    ],
    "uniforms": [],
    "samplers": [],
    "typedef_source": MVP_TYPEDEF,
    "ubo": MVP_UBO,
}


def build_shader_from_config(shader_config):
    """
    Build complete vertex and fragment shaders from a unified shader config.
    Returns dict with 'vertex' and 'fragment' keys containing complete shader code.
    """
    vertex = _build_shader(shader_config["vertex_shader"], shader_config, is_fragment=False)
    fragment = _build_shader(shader_config.get("fragment_shader", ""), shader_config, is_fragment=True)
    return {"vertex": vertex, "fragment": fragment}


class ImageFragmentShader:
    def __init__(self, shader_code, source_obj, inputs: list):
        self.shader_code = shader_code
        self.source_obj = source_obj
        self.inputs = inputs

        if not bpy.app.background:
            # Build vertex shader from IMAGE_SHADER config
            vertex_shader = _build_shader(IMAGE_SHADER["vertex_shader"], IMAGE_SHADER, is_fragment=False)

            self.shader = create_shader_from_code(
                vertex_shader, shader_code, f"image_shader_{id(source_obj)}", IMAGE_SHADER
            )
        else:
            self.shader = None

    def bind(self):
        self.shader.bind()

        for attr, attr_type in self.inputs:
            bind_fn = f"uniform_{attr_type}"
            bind_fn = getattr(self.shader, bind_fn)
            attr_val = getattr(self.source_obj, attr)

            bind_fn(attr, attr_val)


def create_shader_from_code(vertex_shader, fragment_shader, shader_name, shader_config):
    """
    Create a GPU shader using the appropriate API based on Blender version.
    For Blender 5.0+, uses gpu.shader.create_from_info() with shader info objects.
    For older versions, uses the legacy gpu.types.GPUShader() constructor.
    """
    from bl_xr.utils import log

    if not _USE_MODERN_API:
        log.info("Using the old shader creation API")
        return gpu.types.GPUShader(vertex_shader, fragment_shader)

    shader_info = gpu.types.GPUShaderCreateInfo()

    if shader_config:
        # Vertex inputs (attributes) - must be set before vertex source
        for location, (attr_name, attr_type) in enumerate(shader_config.get("vertex_in", [])):
            shader_info.vertex_in(location, attr_type, attr_name)

        # Vertex outputs / Fragment inputs - must be set before sources
        vertex_out_list = shader_config.get("vertex_out", [])
        if vertex_out_list:
            interface_info = gpu.types.GPUStageInterfaceInfo(f"{shader_name}_interface")
            for var_name, var_type in vertex_out_list:
                interface_info.smooth(var_type, var_name)
            shader_info.vertex_out(interface_info)

        # Fragment output - must be set before fragment source
        shader_info.fragment_out(0, "VEC4", "fragColor")

        # Typedef source (struct definitions for UBOs)
        if shader_config.get("typedef_source"):
            shader_info.typedef_source(shader_config["typedef_source"])

        # UBOs
        for slot, type_name, name in shader_config.get("ubo", []):
            shader_info.uniform_buf(slot, type_name, name)

        # Uniforms - can be set before or after sources
        for uniform_name, uniform_type in shader_config.get("uniforms", []):
            shader_info.push_constant(uniform_type, uniform_name)

        # Samplers - can be set before or after sources
        for slot, sampler_name in enumerate(shader_config.get("samplers", [])):
            shader_info.sampler(slot, "FLOAT_2D", sampler_name)

    # Set shader sources AFTER all interface info is configured
    shader_info.vertex_source(vertex_shader)
    shader_info.fragment_source(fragment_shader)

    log.info("Using the new shader creation API")

    shader = None

    try:
        shader = gpu.shader.create_from_info(shader_info)
    except Exception as e:
        print(f"Error creating shader {shader_name}: {e}")

    return shader
