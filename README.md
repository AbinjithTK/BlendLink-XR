# BlendLink XR

VR 3D modeling plugin for Blender with Logitech MX Ink stylus support.

BlendLink XR brings immersive VR creation to Blender — draw, sculpt, model, and animate in virtual reality using Meta Quest headsets and the Logitech MX Ink pressure-sensitive stylus.

## Features

- **Grease Pencil Drawing** — Freehand, line, erase, and smooth tools with pressure sensitivity
- **7 Brush Presets** — Pencil, Ink Pen, Ink Rough, Marker Bold, Marker Chisel, Airbrush, Dot
- **Color Wheel** — HSV color picker with brightness control in VR
- **NURBS Curve Drawing** — Pen and pipe tools with straight line mode
- **Shape Creation** — Cube, sphere, cylinder, cone, torus, monkey
- **Mesh Editing** — Bevel, inset, extrude, loop cut, merge, make face
- **Object Manipulation** — Select, grab, move, rotate, scale, clone
- **MX Ink Stylus** — Full pressure-sensitive input with 3D pen model in VR
- **Navigation** — Grab to pan/orbit, pinch to zoom, walk mode
- **Armature Posing** — Pose bones directly in VR
- **Animation** — Keyframe tools, auto-keying

## Requirements

- Windows 10/11
- Meta Quest 2/3/Pro with Quest Link (Air Link or USB)
- Logitech MX Ink stylus (optional — works with Touch controllers too)
- Patched Blender 5.2 build (see below)

## Quick Start

### Option 1: Download Pre-built (Recommended)

1. Download the latest release from [Releases](https://github.com/AbinjithTK/BlendLink-XR/releases)
2. Extract the Blender zip
3. Run `blender.exe`
4. Edit → Preferences → Add-ons → Install from Disk → select `blendlinkxr_plugin.zip`
5. Enable "BlendLink XR"
6. Connect Quest via Link, put on headset
7. Click **Start VR** in the 3D Viewport header

### Option 2: Build from Source

1. Clone Blender 5.2:
   ```
   git clone https://projects.blender.org/blender/blender.git
   cd blender
   git checkout v5.2.0
   ```

2. Apply the MX Ink patch:
   ```
   git apply /path/to/patches/blender-mx-ink-openxr.patch
   ```

3. Build Blender:
   ```
   make update
   make
   ```

4. Install the plugin from `blendlinkxr_plugin.zip`

## MX Ink Controls

| MX Ink Input | Action |
|---|---|
| Middle cluster force | Draw / Select / Erase (pressure-sensitive) |
| Front click | Grab / Navigate |
| Back click | Quicktools / Clone |
| Front double-tap | Undo |
| Back double-tap | Redo |
| Tip force | Stroke pressure (when touching surface) |
| Dock state | Pauses all input |

Left Touch controller is unchanged (thumbstick for undo/redo, squeeze for navigate, menu button for toolbar).

## VR Toolbar

The floating toolbar on your left hand has:
- Mode buttons (Object / Edit / Pose)
- Tool grid (Select, Pen, Erase, Shape, Hull, Text, Measure, GP Draw)
- GP submenu (Draw, Erase, Line, Smooth + brush presets)
- Color palette (10 preset colors + HSV color wheel)
- Utility buttons (3D Grid, Camera, Keyframe, Mirror, Walk, Clone, etc.)

## License

GPL-2.0-or-later

## Credits

Built on top of the open-source VR framework from the Blender community.
