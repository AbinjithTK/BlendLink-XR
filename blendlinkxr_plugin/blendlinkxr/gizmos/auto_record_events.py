from bl_xr import root
from bl_xr.utils.debug import event_recording_start, event_recording_stop


def on_xr_start(self, event_name, event):
    from blendlinkxr import settings

    if settings["app.debug.auto_record_events"]:
        if not settings["view.show_main_menu"]:
            from blendlinkxr.ui.main_menu import on_menu_toggle

            on_menu_toggle(None, None, None)

        event_recording_start()


def on_xr_end(self, event_name, event):
    import tempfile
    from os import path
    from shutil import copy
    from blendlinkxr import log_manager

    if hasattr(event_recording_start, "recorded_events"):
        event_recording_stop()

        # backup the app log
        fb_log_file = path.join(tempfile.gettempdir(), log_manager.LOG_FILE)
        copy(fb_log_file, fb_log_file + ".events.txt")


def enable_gizmo():
    root.add_event_listener("fb.xr_start", on_xr_start)
    root.add_event_listener("fb.xr_end", on_xr_end)


def disable_gizmo():
    root.remove_event_listener("fb.xr_start", on_xr_start)
    root.remove_event_listener("fb.xr_end", on_xr_end)
