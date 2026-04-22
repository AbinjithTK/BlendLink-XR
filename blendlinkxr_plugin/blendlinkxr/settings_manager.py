import bpy
import os
import json

from bpy.app.handlers import persistent

MODULE_ID = "blendlinkxr_plugin"
OPTIONS_SYNC_INTERVAL = 1  # seconds
SETTINGS_FILE = "settings.json"

settings = {}

BlendLinkAddonPreferences = None
sync_settings_with_desktop_panels = None
stop_syncing = False
on_settings_change_listener = None

"""
Basically we have two systems:
1. A `settings` dict, which is the true source of all knowledge inside BlendLink, and what every bit of code inside
  BlendLink should depend on.
2. A `BlendLinkAddonPreferences` class (that uses Blender's disk-persistence mechanism) to automatically save some of the
  settings to disk. This should be moved to the settings file instead.
3. A settings file.

All the code inside BlendLink reads and writes to the `settings` dict.

A timer periodically copies the values from `BlendLinkAddonPreferences` to the settings dict, to reflect the
changes in the UI (e.g. enabling the "mirror view" checkbox in the desktop UI). This timer also dispatches a
`fb.setting_change` event to `bl_xr.root` whenever a desktop UI-backed value is changed.
"""

SETTINGS_TO_SAVE_IN_FILE = ("view.show_info_panel", "view.show_main_menu")


def setup_blender_preferences():
    "This is used for saving some settings to disk (i.e. persisting across Blender restarts)"

    global BlendLinkAddonPreferences

    class BlendLinkAddonPreferencesPanel(bpy.types.AddonPreferences):
        """
        !!!! Important ***: Make sure that all fields have default values, otherwise tests will break
        """

        bl_idname = MODULE_ID

        main_hand: bpy.props.EnumProperty(
            items=[("left", "Left", "If you are left-handed"), ("right", "Right", "If you are right-handed")],
            name="Main Hand",
            default="right",
        )
        early_access: bpy.props.BoolProperty(name="Early Access to new features", default=False)
        auto_update: bpy.props.BoolProperty(name="Update automatically", default=False)
        sync_with_viewport: bpy.props.BoolProperty(name="Sync headset with desktop viewport", default=False)
        strict_viewport_sync: bpy.props.BoolProperty(name="Strict viewport synchronization", default=False)
        lock_z_rotation: bpy.props.BoolProperty(name="Lock Z axis rotation", default=True)
        show_tracking_empties: bpy.props.BoolProperty(
            name="Show XR Tracking Objects", default=False, update=on_show_tracking_empties_changed
        )
        grab_button: bpy.props.EnumProperty(
            items=[
                ("trigger", "Trigger", "Trigger"),
                ("squeeze", "Squeeze", "Squeeze"),
            ],
            name="Grab Button",
            default="squeeze",
        )

        log_level: bpy.props.EnumProperty(
            items=[
                ("DEBUG", "Debug", "Log everything"),
                ("INFO", "Info", "Information"),
                ("WARN", "Warn", "Warnings only"),
                ("ERROR", "Error", "Errors only"),
            ],
            name="Log Level",
            default="INFO",
        )
        show_dev_tools: bpy.props.BoolProperty(name="Show Developer Tools", default=False)

        auto_record_events: bpy.props.BoolProperty(name="Auto record events", default=False)

        log_filter_enabled: bpy.props.BoolProperty(name="Filter Logs", default=False)
        log_filter__move_events: bpy.props.BoolProperty(name="Move", default=True)
        log_filter__drag_events: bpy.props.BoolProperty(name="Drag", default=True)
        log_filter__pointer_events: bpy.props.BoolProperty(name="UI", default=True)

        headset_reverb_g2: bpy.props.BoolProperty(
            description="Enable bindings for the HP Reverb G2 controllers. Note that this may not be supported by all OpenXR runtimes",
            default=False,
        )
        headset_vive_cosmos: bpy.props.BoolProperty(
            description="Enable bindings for the HTC Vive Cosmos controllers. Note that this may not be supported by all OpenXR runtimes",
            default=False,
        )
        headset_vive_focus: bpy.props.BoolProperty(
            description="Enable bindings for the HTC Vive Focus 3 controllers. Note that this may not be supported by all OpenXR runtimes",
            default=False,
        )

        demo_cable_manager_enabled: bpy.props.BoolProperty(
            name="Enable Cable Manager (demo)", default=False
        )
        demo_cable_manager_use_fixed_diameter: bpy.props.BoolProperty(
            name="Use fixed diameter", default=False
        )
        demo_cable_manager_diameter: bpy.props.FloatProperty(name="Diameter", default=0.01, min=0.001, max=1, step=0.001, precision=4)

    bpy.utils.register_class(BlendLinkAddonPreferencesPanel)

    BlendLinkAddonPreferences = BlendLinkAddonPreferencesPanel


def setup_project_preferences():
    "This is used for storing settings that are specific to a project (e.g. the starting position of the viewer etc)"

    bpy.types.Scene.blendlinkxr_viewer_position = bpy.props.FloatVectorProperty(
        name="BlendLink viewer position", default=(0, 0, 0), size=3
    )
    bpy.types.Scene.blendlinkxr_viewer_rotation = bpy.props.FloatVectorProperty(
        name="BlendLink viewer rotation", default=(0, 0, 0, 0), size=4
    )
    bpy.types.Scene.blendlinkxr_viewer_scale = bpy.props.FloatProperty(name="BlendLink viewer scale", default=0)

    bpy.types.Scene.blendlinkxr_draw_collection = bpy.props.PointerProperty(
        type=bpy.types.Collection, name="Collection to draw in"
    )


def apply_saved_log_level_preference():
    "This needs to be called as early as possible, to ensure that we log at the user-specified log level"

    if bpy.app.background:
        return

    if MODULE_ID in bpy.context.preferences.addons:
        pref = bpy.context.preferences.addons[MODULE_ID].preferences
        _set_log_level(pref.log_level)
    else:
        _set_log_level("INFO")


def reset_settings():
    from bl_xr.consts import BLACK, WHITE, RED_MILD, VEC_ONE
    from mathutils import Vector

    settings.clear()

    # app
    settings["app.main_hand"] = "right"
    settings["app.log.level"] = "DEBUG"
    settings["app.log.log_filter_enabled"] = False
    settings["app.log.log_filter.move_events"] = True
    settings["app.log.log_filter.drag_events"] = True
    settings["app.log.log_filter.pointer_events"] = True
    settings["app.debug.auto_record_events"] = False
    settings["app.update.early_access"] = None
    settings["app.update.auto_update"] = False
    settings["app.headsets.reverb_g2"] = False
    settings["app.headsets.vive_cosmos"] = False
    settings["app.headsets.vive_focus"] = False

    # view
    settings["view.mirror_xr"] = False
    settings["view.sync_with_viewport"] = False
    settings["view.strict_viewport_sync"] = False
    settings["view.mouse_visible_threshold_distance"] = 5  # pixels
    settings["view.mouse_hide_threshold_time"] = 5  # seconds
    settings["view.mouse_pointer_offset"] = Vector((0.1, 0.1, 0.2))  # from viewport camera
    settings["view.mouse_default_laser_length"] = 2
    settings["view.show_info_panel"] = True
    settings["view.show_main_menu"] = True

    # world nav
    settings["world_nav.interpolate_movement"] = True
    settings["world_nav.interpolation_factor"] = 0.35
    settings["world_nav.lock_rotation.single_handed"] = True
    # settings["world_nav.lock_rotation.two_handed"] = True  # not implemented yet
    settings["world_nav.nav_mode"] = "GRAB"  # or GRAB, WALK or FLY
    settings["world_nav.walk_speed"] = 0.025  # units per joystick unit
    settings["world_nav.rotation_speed"] = 2  # degrees per joystick unit

    # transform
    settings["transform.alt_trigger_debounce_time"] = 0.1  # seconds
    settings["transform.grab_button"] = "squeeze"  # or "trigger"
    settings["transform.check_for_fov"] = True

    # select
    settings["select.default_cursor_size"] = 0.01
    settings["select.default_cursor_color"] = WHITE

    # erase
    settings["erase.default_cursor_size"] = 0.01
    settings["erase.default_cursor_color"] = RED_MILD

    # stroke
    settings["stroke.type"] = "pen"
    settings["stroke.straight_line"] = False
    settings["stroke.extend"] = False
    settings["stroke.fixed_thickness"] = False
    settings["stroke.min_stroke_distance"] = 0.015
    settings["stroke.angle_threshold_for_dir_change"] = 30  # degrees
    settings["stroke.pen.default_cursor_size"] = 0.002
    settings["stroke.pen.bevel_mode"] = "PROFILE"
    settings["stroke.pen.bevel_resolution"] = 1
    settings["stroke.pen.use_fill_caps"] = True
    settings["stroke.pen.color"] = BLACK
    settings["stroke.pipe.default_cursor_size"] = 0.008
    settings["stroke.pipe.bevel_mode"] = "ROUND"
    settings["stroke.pipe.bevel_resolution"] = 4
    settings["stroke.pipe.use_fill_caps"] = True
    settings["stroke.pipe.color"] = None

    # shape
    settings["shape.type"] = "cube"
    settings["shape.constraint.cube"] = "XY"
    settings["shape.constraint.sphere"] = "XYZ"
    settings["shape.constraint.torus"] = "XY"
    settings["shape.constraint.cylinder"] = "XY"
    settings["shape.constraint.cone"] = "XY"
    settings["shape.constraint.monkey"] = "XYZ"
    settings["shape.mirror.cube"] = None
    settings["shape.mirror.sphere"] = "XYZ"
    settings["shape.mirror.torus"] = "XY"
    settings["shape.mirror.cylinder"] = "XY"
    settings["shape.mirror.cone"] = "XY"
    settings["shape.mirror.monkey"] = "XYZ"
    settings["shape.default_cursor_size"] = 0.002

    # hull
    settings["hull.min_stroke_distance"] = 0.003

    # grease pencil
    settings["gp.default_cursor_size"] = 0.002
    settings["gp.active_brush"] = "pencil"
    settings["gp.active_color"] = (0.0, 0.0, 0.0, 1.0)
    settings["gp.color_brightness"] = 1.0
    settings["gp.last_hue"] = 0.0
    settings["gp.last_saturation"] = 0.0

    # edit mesh operations
    settings["bevel.default_rounded_segments"] = 5
    # settings["loop_cut.num_cuts"] = 1
    # settings["loop_cut.follow_cursor"] = True
    settings["edit.perform_extrude"] = False

    # timeline
    settings["timeline.long_press_repeat_threshold_time"] = 0.35  # seconds
    settings["timeline.long_press_repeat_interval"] = 0.12  # seconds

    # clone
    settings["clone.long_press_threshold_time"] = 0.35  # seconds
    settings["clone.linked_duplicates"] = False

    # gizmos
    settings["gizmo.edit_handle.length"] = 0.12
    settings["gizmo.edit_handle.knob_radius"] = 0.015
    settings["gizmo.planar_handle.size"] = 0.03
    settings["gizmo.single_handle.size"] = 0.02
    settings["gizmo.transform_handles.type"] = None  # or "translate", "rotate", "scale"
    settings["gizmo.transform_handles.length"] = 0.1
    settings["gizmo.transform_handles.knob_radius"] = 0.015
    settings["gizmo.transform_handles.ring_thickness"] = 0.0075
    settings["gizmo.3d_grid.line_spacing"] = 0.1  # in local coordinates of the 3D grid
    settings["gizmo.3d_grid.line_count"] = 3
    settings["gizmo.cursor.min_size"] = 0.002
    settings["gizmo.cursor.max_size"] = 0.036
    settings["gizmo.cursor.default_size"] = 0.01
    settings["gizmo.cursor.resize_speed"] = 0.00012
    settings["gizmo.cursor.resize_speed_small_multiplier"] = 1
    settings["gizmo.cursor.resize_speed_large_multiplier"] = 6.5
    settings["gizmo.camera_preview.preview_scale"] = 0.15 * VEC_ONE
    settings["gizmo.camera_preview.preview_offset"] = Vector((-0.14, 0.5, 0.04))
    settings["gizmo.fps_counter.preview_offset"] = Vector((-0.14, 0.5, 0.02))
    settings["gizmo.camera_preview_on_grab.preview_duration_after_release"] = 0.7  # seconds
    settings["gizmo.joystick_for_keyframe.long_press_repeat_threshold_time"] = 0.35  # seconds
    settings["gizmo.joystick_for_keyframe.long_press_repeat_interval"] = 0.08  # seconds
    settings["gizmo.joystick_for_keyframe.long_press_repeat_frame_acceleration"] = 1
    settings["gizmo.joystick_for_keyframe.camera_preview_offset"] = Vector((-0.14, 0.5, 0.04))
    settings["gizmo.mirror.enabled"] = False
    settings["gizmo.mirror.axis_x"] = True
    settings["gizmo.mirror.axis_y"] = False
    settings["gizmo.mirror.axis_z"] = False
    settings["gizmo.desktop_viewer.viewer_scale"] = 0.6 * VEC_ONE
    settings["gizmo.desktop_viewer.viewer_offset"] = Vector((-0.44, 0.7, 0.08))

    # quicktools
    settings["quicktools.min_move_distance"] = 0.02

    # demo extensions
    settings["demo.cable_manager_enabled"] = False
    settings["demo.cable_manager_use_fixed_diameter"] = False
    settings["demo.cable_manager_diameter"] = 0.01


def apply_saved_settings_from_file():
    bl_dir = os.path.join(os.path.expanduser("~"), ".blendlinkxr")
    os.makedirs(bl_dir, exist_ok=True)

    settings_file = os.path.join(bl_dir, SETTINGS_FILE)
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            settings_from_file = json.load(f)
            settings.update(settings_from_file)


def save_settings_to_file():
    bl_dir = os.path.join(os.path.expanduser("~"), ".blendlinkxr")
    os.makedirs(bl_dir, exist_ok=True)

    settings_to_file = {k: v for k, v in settings.items() if k in SETTINGS_TO_SAVE_IN_FILE}

    settings_file = os.path.join(bl_dir, SETTINGS_FILE)
    with open(settings_file, "w") as f:
        json.dump(settings_to_file, f)


def setup_settings_change_listener():
    global on_settings_change_listener

    import bl_xr
    from bl_xr import root
    from bl_input.bindings import DISABLED_PROFILES

    from .gizmos import enable_gizmo, disable_gizmo, toggle_gizmo
    from .utils import set_viewport_mirror_state, log
    from .log_manager import enable_log_filter, _dev_log_filter
    from .updater import check_update

    def on_settings_change(self, event_name, changes):
        if "app.main_hand" in changes:
            bl_xr.main_hand = changes["app.main_hand"]
        if "app.log.level" in changes:
            log_level = changes["app.log.level"]
            _set_log_level(log_level)
        if "view.sync_with_viewport" in changes:
            sync_enabled = changes["view.sync_with_viewport"]
            if sync_enabled:
                enable_gizmo("viewport_sync")
            else:
                disable_gizmo("viewport_sync")
        if "demo.cable_manager_enabled" in changes:
            if changes["demo.cable_manager_enabled"]:
                enable_gizmo("cable_manager")
            else:
                disable_gizmo("cable_manager")

        # developer log filter
        if "app.log.log_filter_enabled" in changes:
            enable_log_filter(changes["app.log.log_filter_enabled"])
        if "app.log.log_filter.move_events" in changes:
            _dev_log_filter.move_events = changes["app.log.log_filter.move_events"]
        if "app.log.log_filter.drag_events" in changes:
            _dev_log_filter.drag_events = changes["app.log.log_filter.drag_events"]
        if "app.log.log_filter.pointer_events" in changes:
            _dev_log_filter.pointer_events = changes["app.log.log_filter.pointer_events"]

        # experimental headsets
        for headset_name in ("reverb_g2", "vive_cosmos", "vive_focus"):
            key = f"app.headsets.{headset_name}"
            if key in changes:
                enable_headset = changes[key]

                if enable_headset and headset_name in DISABLED_PROFILES:
                    DISABLED_PROFILES.remove(headset_name)
                elif not enable_headset and headset_name not in DISABLED_PROFILES:
                    DISABLED_PROFILES.append(headset_name)

        # app infrastructure
        if "app.update.early_access" in changes:
            check_update()

    on_settings_change_listener = on_settings_change

    root.add_event_listener("fb.setting_change", on_settings_change_listener)


def remove_settings_change_listener():
    from bl_xr import root

    root.remove_event_listener("fb.setting_change", on_settings_change_listener)


def setup_preferences_to_settings_synchronization():
    """
    Check the values in `BlendLinkAddonPreferences` periodically and copy them to BlendLink's `settings` dict.
    This will setup the dispatch of `fb.setting_change` events to the `bl_xr.root` object, whenever the user
    makes a change in the UI.
    """
    global sync_settings_with_desktop_panels

    from bl_xr import root
    from .utils import log, desktop_viewport
    from .gizmos import toggle_gizmo

    settings_to_preferences_key_mappings = {
        "app.main_hand": "main_hand",
        "view.mirror_xr": "mirror_xr_viewport",
        "view.sync_with_viewport": "sync_with_viewport",
        "view.strict_viewport_sync": "strict_viewport_sync",
        "world_nav.lock_rotation.single_handed": "lock_z_rotation",
        "transform.grab_button": "grab_button",
        "app.update.early_access": "early_access",
        "app.update.auto_update": "auto_update",
        "app.log.level": "log_level",
        "app.log.log_filter_enabled": "log_filter_enabled",
        "app.log.log_filter.move_events": "log_filter__move_events",
        "app.log.log_filter.drag_events": "log_filter__drag_events",
        "app.log.log_filter.pointer_events": "log_filter__pointer_events",
        "app.debug.auto_record_events": "auto_record_events",
        "app.headsets.reverb_g2": "headset_reverb_g2",
        "app.headsets.vive_cosmos": "headset_vive_cosmos",
        "app.headsets.vive_focus": "headset_vive_focus",
        "demo.cable_manager_enabled": "demo_cable_manager_enabled",
        "demo.cable_manager_use_fixed_diameter": "demo_cable_manager_use_fixed_diameter",
        "demo.cable_manager_diameter": "demo_cable_manager_diameter",
    }

    def _sync_settings_with_desktop_panels():
        "Copy changes made in `BlendLinkAddonPreferences` to the `settings` dict, and dispatch `fb.setting_change` events (if necessary)"

        if stop_syncing:
            return

        changes = {}
        pref = _get_preferences()
        if pref is None:
            return  # blendlinkxr isn't installed. maybe running via puppetry

        for option_id, attr in settings_to_preferences_key_mappings.items():
            old_val = settings[option_id]
            if option_id == "view.mirror_xr":
                new_val = desktop_viewport.get_space().mirror_xr_session
            else:
                new_val = getattr(pref, attr, None)

            if old_val != new_val:
                settings[option_id] = new_val
                changes[option_id] = new_val
                log.info(f"changed {option_id} from: {old_val} to: {new_val}")

        if len(changes) > 0:
            log.debug(f"Sending fb.setting_change event with changes: {changes}")
            root.dispatch_event("fb.setting_change", changes)

        return OPTIONS_SYNC_INTERVAL

    if not bpy.app.background:
        bpy.app.timers.register(_sync_settings_with_desktop_panels, persistent=True)

    sync_settings_with_desktop_panels = _sync_settings_with_desktop_panels


def on_show_tracking_empties_changed(self, context):
    from .gizmos import enable_gizmo, disable_gizmo

    pref = _get_preferences()
    if pref.show_tracking_empties:
        enable_gizmo("track_xr_device_empties")
    else:
        disable_gizmo("track_xr_device_empties")


def _get_preferences():
    if MODULE_ID not in bpy.context.preferences.addons:
        return
    return bpy.context.preferences.addons[MODULE_ID].preferences


def _set_log_level(log_level):
    import logging

    logging.getLogger("BlendLink").setLevel(log_level)
    logging.getLogger("bl_xr").setLevel(log_level)


@persistent
def on_file_load(scene):
    if bpy.app.background:
        return

    on_show_tracking_empties_changed(None, None)


def init():
    bpy.app.handlers.load_post.append(on_file_load)

    setup_blender_preferences()
    setup_project_preferences()
    apply_saved_log_level_preference()

    reset_settings()

    if not bpy.app.background:
        apply_saved_settings_from_file()

    setup_preferences_to_settings_synchronization()


def register():
    setup_settings_change_listener()


def unregister():
    remove_settings_change_listener()


init()
