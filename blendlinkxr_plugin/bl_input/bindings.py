# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
from typing import Union


@dataclass
class Binding:
    component_path: Union[str, list] = None
    num_components: int = 1
    threshold: float = 0.0
    suffix: str = ""
    axis_region: str = "ANY"
    type: str = "BASIC"  # or "AXIS" or "POSE"


class AxisBinding(Binding):
    def __init__(self, component_path, **kwargs):
        super().__init__(component_path, **kwargs)

        self.type = "AXIS"


PROFILES = {
    "index": "/interaction_profiles/valve/index_controller",
    "oculus": "/interaction_profiles/oculus/touch_controller",
    "reverb_g2": "/interaction_profiles/hp/mixed_reality_controller",
    "vive": "/interaction_profiles/htc/vive_controller",
    "vive_cosmos": "/interaction_profiles/htc/vive_cosmos_controller",
    "vive_focus": "/interaction_profiles/htc/vive_focus3_controller",
    "wmr": "/interaction_profiles/microsoft/motion_controller",
    "mx_ink": "/interaction_profiles/logitech/mx_ink_stylus_logitech",
}
DISABLED_PROFILES = ["reverb_g2", "vive_cosmos", "vive_focus"]

# MX Ink is right-hand only — it replaces the right controller while the
# left hand keeps using a Touch controller.  Bindings that target both hands
# (num_components=2) will get left=standard path, right=MX Ink path via the
# per-profile dicts below.  Left-hand-only actions (joystick, left buttons)
# simply omit "mx_ink" from their path dict so no MX Ink binding is created.

GRIP_COMPONENT_PATH = "/input/grip/pose"
AIM_COMPONENT_PATH = "/input/aim/pose"
TRIGGER_COMPONENT_PATH = "/input/trigger/value"
HAPTIC_COMPONENT_PATH = "/output/haptic"

# --- MX Ink component paths ---
#
# Physical layout (index finger, front-to-back):
#   Front click  — closest to pen tip, natural "trigger" finger position
#   Back click   — behind front click, secondary button
#   Middle force — grip squeeze area on the barrel
#   Tip force    — pen tip pressure sensor (0.0–1.0 analog)
#
# Mapping rationale:
#   Front click  → SQUEEZE  (grab / navigate — like gripping the pen firmly)
#   Back click   → A BUTTON (quicktools / clone — secondary action)
#   Middle force → TRIGGER  (draw / select / erase — pressure-sensitive primary)
#   Tip force    → separate pressure action (for pressure-sensitive stroke width)
#   Front double-tap → undo  (replaces missing left-stick-left)
#   Back double-tap  → redo  (replaces missing left-stick-right)
#
MX_INK_TIP_FORCE_PATH = "/input/tip_logitech/force"
MX_INK_TIP_POSE_PATH = "/input/tip_logitech/pose"
MX_INK_MIDDLE_FORCE_PATH = "/input/cluster_middle_logitech/force"
MX_INK_FRONT_CLICK_PATH = "/input/cluster_front_logitech/click"
MX_INK_BACK_CLICK_PATH = "/input/cluster_back_logitech/click"
MX_INK_FRONT_DOUBLE_TAP_PATH = "/input/cluster_front_logitech/double_tap_logitech"
MX_INK_BACK_DOUBLE_TAP_PATH = "/input/cluster_back_logitech/double_tap_logitech"
MX_INK_DOCK_STATE_PATH = "/input/dock_logitech/docked_logitech"

SQUEEZE_COMPONENT_PATHS = {
    "index": "/input/squeeze/force",
    "oculus": "/input/squeeze/value",
    "reverb_g2": "/input/squeeze/value",
    "vive": "/input/squeeze/click",
    "vive_cosmos": "/input/squeeze/click",
    "vive_focus": "/input/squeeze/click",
    "wmr": "/input/squeeze/click",
    "mx_ink": MX_INK_FRONT_CLICK_PATH,
}
JOYSTICK_COMPONENT_PATHS = {
    "index": "/input/thumbstick",
    "oculus": "/input/thumbstick",
    "reverb_g2": "/input/thumbstick",
    "vive": "/input/trackpad",
    "vive_cosmos": "/input/thumbstick",
    "vive_focus": "/input/thumbstick",
    "wmr": "/input/thumbstick",
    # MX Ink has no joystick — left-hand-only actions omit it,
    # right-hand joystick actions will simply not bind for mx_ink.
}
BUTTON_A_LEFTHAND_COMPONENT_PATHS = {
    "index": "/input/a/click",
    "oculus": "/input/x/click",
    "reverb_g2": "/input/x/click",
    "vive_cosmos": "/input/x/click",
    "vive_focus": "/input/x/click",
    # No mx_ink entry — left hand stays on Touch controller
}
BUTTON_B_LEFTHAND_COMPONENT_PATHS = {
    "index": "/input/b/click",
    "oculus": "/input/y/click",
    "reverb_g2": "/input/y/click",
    "vive_cosmos": "/input/y/click",
    "vive_focus": "/input/y/click",
}
BUTTON_A_RIGHTHAND_COMPONENT_PATHS = {
    "index": "/input/a/click",
    "oculus": "/input/a/click",
    "reverb_g2": "/input/a/click",
    "vive_cosmos": "/input/a/click",
    "vive_focus": "/input/a/click",
    "mx_ink": MX_INK_BACK_CLICK_PATH,
}
BUTTON_B_RIGHTHAND_COMPONENT_PATHS = {
    "index": "/input/b/click",
    "oculus": "/input/b/click",
    "reverb_g2": "/input/b/click",
    "vive_cosmos": "/input/b/click",
    "vive_focus": "/input/b/click",
    # MX Ink has no B button equivalent — only 2 cluster buttons
    # Back click is used for A button, front click for trigger
}
BUTTON_A_LEFTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/a/touch",
    "oculus": "/input/x/touch",
}
BUTTON_B_LEFTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/b/touch",
    "oculus": "/input/y/touch",
}
BUTTON_A_RIGHTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/a/touch",
    "oculus": "/input/a/touch",
    # MX Ink has no touch sensors — omitted
}
BUTTON_B_RIGHTHAND_TOUCH_COMPONENT_PATHS = {
    "index": "/input/b/touch",
    "oculus": "/input/b/touch",
}

# --- Trigger: front click on MX Ink (index finger button = primary action) ---
TRIGGER_COMPONENT_PATHS = {
    "index": TRIGGER_COMPONENT_PATH,
    "oculus": TRIGGER_COMPONENT_PATH,
    "reverb_g2": TRIGGER_COMPONENT_PATH,
    "vive": TRIGGER_COMPONENT_PATH,
    "vive_cosmos": TRIGGER_COMPONENT_PATH,
    "vive_focus": TRIGGER_COMPONENT_PATH,
    "wmr": TRIGGER_COMPONENT_PATH,
    "mx_ink": MX_INK_MIDDLE_FORCE_PATH,
}

# --- Aim pose: tip pose on MX Ink for pen-tip precision ---
AIM_POSE_COMPONENT_PATHS = {
    "index": AIM_COMPONENT_PATH,
    "oculus": AIM_COMPONENT_PATH,
    "reverb_g2": AIM_COMPONENT_PATH,
    "vive": AIM_COMPONENT_PATH,
    "vive_cosmos": AIM_COMPONENT_PATH,
    "vive_focus": AIM_COMPONENT_PATH,
    "wmr": AIM_COMPONENT_PATH,
    "mx_ink": MX_INK_TIP_POSE_PATH,
}

# --- Grip pose: standard grip on all profiles including MX Ink ---
GRIP_POSE_COMPONENT_PATHS = {
    "index": GRIP_COMPONENT_PATH,
    "oculus": GRIP_COMPONENT_PATH,
    "reverb_g2": GRIP_COMPONENT_PATH,
    "vive": GRIP_COMPONENT_PATH,
    "vive_cosmos": GRIP_COMPONENT_PATH,
    "vive_focus": GRIP_COMPONENT_PATH,
    "wmr": GRIP_COMPONENT_PATH,
    "mx_ink": GRIP_COMPONENT_PATH,
}

# --- Haptic: same output path on all profiles including MX Ink ---
HAPTIC_COMPONENT_PATHS = {
    "index": HAPTIC_COMPONENT_PATH,
    "oculus": HAPTIC_COMPONENT_PATH,
    "reverb_g2": HAPTIC_COMPONENT_PATH,
    "vive": HAPTIC_COMPONENT_PATH,
    "vive_cosmos": HAPTIC_COMPONENT_PATH,
    "vive_focus": HAPTIC_COMPONENT_PATH,
    "wmr": HAPTIC_COMPONENT_PATH,
    "mx_ink": HAPTIC_COMPONENT_PATH,
}

THRESHOLD = {
    "trigger": 0.05,
    "squeeze": 0.3,
    "joystick": 0.3,
    "button": 0.01,
    "tip_force": 0.03,
    "middle_force": 0.25,
}


bindings: dict[str, Binding] = {
    "GRIP_POSE": Binding(GRIP_POSE_COMPONENT_PATHS, num_components=2, type="POSE"),
    "AIM_POSE": Binding(AIM_POSE_COMPONENT_PATHS, num_components=2, type="POSE"),
    "TRIGGER": Binding(TRIGGER_COMPONENT_PATHS, num_components=2, threshold=THRESHOLD["trigger"]),
    "SQUEEZE": Binding(SQUEEZE_COMPONENT_PATHS, num_components=2, threshold=THRESHOLD["squeeze"]),
    "HAPTIC": Binding(HAPTIC_COMPONENT_PATHS, num_components=2),
    # "JOYSTICK": Binding(JOYSTICK_COMPONENT_PATHS, threshold=JOYSTICK_DIR_THRESHOLD),
    "JOYSTICK_X": AxisBinding(JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x"),
    "JOYSTICK_Y": AxisBinding(JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y"),
    "JOYSTICK_LEFT": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x", axis_region="NEGATIVE"
    ),
    "JOYSTICK_RIGHT": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/x", axis_region="POSITIVE"
    ),
    "JOYSTICK_DOWN": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y", axis_region="NEGATIVE"
    ),
    "JOYSTICK_UP": AxisBinding(
        JOYSTICK_COMPONENT_PATHS, threshold=THRESHOLD["joystick"], suffix="/y", axis_region="POSITIVE"
    ),
    "BUTTON_A_LEFTHAND": AxisBinding(BUTTON_A_LEFTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_LEFTHAND": AxisBinding(BUTTON_B_LEFTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_RIGHTHAND": AxisBinding(BUTTON_A_RIGHTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_RIGHTHAND": AxisBinding(BUTTON_B_RIGHTHAND_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_TOUCH_LEFTHAND": AxisBinding(BUTTON_A_LEFTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_TOUCH_LEFTHAND": AxisBinding(BUTTON_B_LEFTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_A_TOUCH_RIGHTHAND": AxisBinding(BUTTON_A_RIGHTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    "BUTTON_B_TOUCH_RIGHTHAND": AxisBinding(BUTTON_B_RIGHTHAND_TOUCH_COMPONENT_PATHS, threshold=THRESHOLD["button"]),
    # --- MX Ink exclusive bindings ---
    "MX_INK_DOCK_STATE": AxisBinding(
        {"mx_ink": MX_INK_DOCK_STATE_PATH}, threshold=THRESHOLD["button"]
    ),
    "MX_INK_FRONT_DOUBLE_TAP": AxisBinding(
        {"mx_ink": MX_INK_FRONT_DOUBLE_TAP_PATH}, threshold=THRESHOLD["button"]
    ),
    "MX_INK_BACK_DOUBLE_TAP": AxisBinding(
        {"mx_ink": MX_INK_BACK_DOUBLE_TAP_PATH}, threshold=THRESHOLD["button"]
    ),
    "MX_INK_TIP_FORCE": AxisBinding(
        {"mx_ink": MX_INK_TIP_FORCE_PATH}, threshold=THRESHOLD["tip_force"]
    ),
}


def make_bindings(action, binding_name: str):
    b = bindings[binding_name]

    for platform_name in PROFILES.keys():
        if isinstance(b.component_path, dict) and platform_name not in b.component_path:
            continue

        binding = action.bindings.new(platform_name, True)
        binding.profile = PROFILES[platform_name]

        path = b.component_path[platform_name] if isinstance(b.component_path, dict) else b.component_path
        path += b.suffix
        paths = [path] * b.num_components

        if hasattr(binding, "component_paths"):  # introduced in Blender 3.2
            for path in paths:
                binding.component_paths.new(path)
        else:
            binding.component_path0 = paths[0]
            if len(paths) > 1:
                binding.component_path1 = paths[1]

        if b.type != "POSE":
            binding.threshold = b.threshold

        if b.type == "AXIS":
            binding.axis0_region = b.axis_region
        elif b.type == "POSE":
            binding.pose_location = [0.0, 0.0, 0.0]
            binding.pose_rotation = [0.0, 0.0, 0.0]
