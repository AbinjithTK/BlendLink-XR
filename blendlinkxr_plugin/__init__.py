# SPDX-License-Identifier: GPL-2.0-or-later
#
# BlendLink XR — VR modeling with MX Ink stylus support
# Copyright (C) 2026 BlendLink Team, GPL-2.0-or-later

# <pep8 compliant>

bl_info = {
    "name": "BlendLink XR",
    "author": "BlendLink Team",
    "version": (3, 0, 0),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > BlendLink XR",
    "description": "VR-based 3D modeling with MX Ink stylus support",
    "category": "3D View",
}

import bpy
import sys
import os

sys.path.append(os.path.dirname(__file__))

import blendlinkxr


def register():
    if (5, 0, 1) <= bpy.app.version < (5, 2):
        raise Exception("BlendLink XR is not compatible with Blender 5.0.1 or 5.1. Please use Blender 5.2, 5.0.0 or Blender 4!")

    blendlinkxr.register()


def unregister():
    blendlinkxr.unregister()
