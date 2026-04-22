import bpy
import gpu

from blendlinkxr import settings
from blendlinkxr.utils import log

from bl_xr import Node, Bounds, root, xr_session, Image
from bl_xr.consts import VEC_ZERO, BLUE_MS

from mathutils import Vector, Quaternion
from math import radians

from .screenshot_manager import ScreenshotManager
from .input import InputTracker


class UpdateOperator(bpy.types.Operator):
    bl_idname = "fb.update_view_operator"
    bl_label = "VR Update View"

    FPS = 2
    RUNNING = False

    _timer = None

    def modal(self, context, event):
        xr_session = context.window_manager.xr_session_state
        if not self.RUNNING or not xr_session or not xr_session.is_running:
            self.cancel(context)
            return {"FINISHED"}

        if event.type == "TIMER":
            screen_capture.draw_screen()

        return {"PASS_THROUGH"}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / self.FPS, window=context.window)
        wm.modal_handler_add(self)

        UpdateOperator.RUNNING = True

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

        UpdateOperator.RUNNING = False


class Screen(Node):
    def __init__(self, width, height, **kwargs):
        super().__init__(**kwargs)

        self.width = width
        self.height = height

        self.aspect_ratio = width / height

        # cursor
        self.input = InputTracker()
        self.cursor = Node(position=Vector((0, 0, -0.0001)))
        self.cursor.scale = 0.015
        self.cursor_img = Image(src="images/cursor.png", width=1, position=Vector((0, 1, 0)), intersects=None)
        self.cursor_img.rotation = Quaternion((1, 0, 0), radians(180))

        self.cursor.append_child(self.cursor_img)
        self.append_child(self.cursor)

    def update(self):
        mouse_pos = self.input.get_mouse_pos()
        x, y = mouse_pos
        rel_x = x / self.width
        rel_y = y / self.height

        rel_x *= self.aspect_ratio

        self.cursor.position.x = rel_x
        self.cursor.position.y = rel_y + 0.008

    @property
    def bounds_local(self) -> Bounds:
        return Bounds(VEC_ZERO, Vector((self.aspect_ratio, 1, 0)))


class ScreenCapture(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.screenshot_manager = ScreenshotManager()
        self.screen = Screen(self.screenshot_manager.width, self.screenshot_manager.height, intersects=None)
        self.append_child(self.screen)

    def start_capture(self):
        if not bpy.app.background:
            bpy.ops.fb.update_view_operator()

            self.screenshot_manager.start_capture()

    def stop_capture(self):
        UpdateOperator.RUNNING = False
        self.screenshot_manager.cleanup()

        log.info(f"stopped camera preview")

    def draw_screen(self):
        # t0 = time.time()

        pixels = self.screenshot_manager.get_frame()

        # t = time.time()
        # self.image.pixels.foreach_set(self.pixels)
        # log.info(f"set pixels: {1000 * (time.time() - t):.1f} ms")

        # t = time.time()
        # self._texture = gpu.texture.from_image(self.image)
        # log.info(f"texture: {1000 * (time.time() - t):.1f} ms")

        # t = time.time()
        buffer = gpu.types.Buffer("FLOAT", pixels.shape, pixels)
        # log.info(f"buffer: {1000 * (time.time() - t):.1f} ms")

        # t = time.time()
        setattr(
            self.screen,
            "_texture",
            gpu.types.GPUTexture((pixels.shape[1], pixels.shape[0]), format="SRGB8_A8", data=buffer),
        )
        # log.info(f"texture: {1000 * (time.time() - t):.1f} ms")

        # log.info(f"******* overall DRAW: {1000 * (time.time() - t0):.1f} ms")


# Create global instance
screen_capture = ScreenCapture(
    id="screen_capture",
    style={
        "scale": Vector(settings["gizmo.desktop_viewer.viewer_scale"]),
        "fixed_scale": True,
        # "border": (0.01, BLUE_MS),
        # "border_radius": (0.01),
    },
    intersects=None,
)


def on_navigate_start(self, event_name, event):
    screen_capture.style["visible"] = False


def on_navigate_end(self, event_name, event):
    screen_capture.style["visible"] = True

    update_camera_pose()


def update_camera_pose():
    rot = xr_session.viewer_camera_rotation

    offset = Vector(settings["gizmo.desktop_viewer.viewer_offset"])
    offset = rot @ offset
    offset *= xr_session.viewer_scale

    screen_capture.position = xr_session.viewer_camera_position + offset
    screen_capture.rotation = rot @ Quaternion((1, 0, 0), radians(-90))


bpy.utils.register_class(UpdateOperator)


def enable_gizmo():
    root.append_child(screen_capture)

    root.add_event_listener("fb.navigate_start", on_navigate_start)
    root.add_event_listener("fb.navigate_end", on_navigate_end)

    screen_capture.style["visible"] = True

    update_camera_pose()

    screen_capture.start_capture()


def disable_gizmo():
    root.remove_child(screen_capture)

    root.remove_event_listener("fb.navigate_start", on_navigate_start)
    root.remove_event_listener("fb.navigate_end", on_navigate_end)

    screen_capture.stop_capture()
