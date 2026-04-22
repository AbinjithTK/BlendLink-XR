# BlendLink XR

## Inspiration

We watched artists create incredible 3D work in Blender — characters, environments, entire animated films — and every single one of them did it by staring at a flat screen and dragging a mouse. Orbiting, zooming, guessing at depth. There's always a layer of glass between the artist and their work.

Then we held the MX Ink. A pen that knows exactly where its tip is in 3D space, how hard you're pressing, and which way it's pointing. The same natural instrument artists already know how to use — except it works in mid-air.

Nobody had connected it to professional 3D software. Blender has 4.2 million monthly users and a fully open architecture. The MX Ink has sub-millimeter tracking and analog pressure. The bridge between them didn't exist. So we built it.

## What it does

BlendLink XR is a Blender plugin that lets artists create 3D art in VR using the Logitech MX Ink stylus. Put on a Quest headset, press Start VR in Blender, and your scene opens around you with the pen in your hand.

**Draw** — Pressure-sensitive Grease Pencil strokes with seven brush presets (Pencil, Ink, Marker, Airbrush, Dot), an HSV color wheel, proximity erase, and stroke smoothing. Every mark is native Blender data.

**Build** — Drop shapes, draw NURBS curves, create convex hulls by moving your hand through space.

**Edit** — Bevel, inset, extrude, loop cut, merge, make face. Grab vertices and pull. Point at it, click it, move it.

**Navigate** — Squeeze to grab the world. Both hands to zoom. Walk mode. One-button scale reset.

**Pose** — Grab a bone, move it. The chain follows. Like posing a figure on your desk.

Every MX Ink input maps to a meaningful action. Middle cluster force is your pressure-sensitive trigger. Front click grabs objects. Back click opens a radial tool menu. Double-tap for undo. Dock the pen and input pauses. A glossy 3D model of the actual MX Ink renders in the headset so you see your real tool while you work.

Take the headset off — your .blend file is right there on the desktop. Same session. No export. No conversion.

## How we built it

We started by patching Blender's C++ OpenXR layer (GHOST_XrSession.cc) to gracefully handle the MX Ink interaction profile (`XR_LOGITECH_mx_ink_stylus_interaction`). Without this, Blender crashes when it encounters an unsupported profile.

On top of that, we built the plugin in three layers:

**Input layer** (`bl_input/`) — OpenXR action bindings that map every MX Ink component (tip force, tip pose, cluster buttons, dock state, double-taps) to Blender's action system. Falls back to Touch controllers automatically if MX Ink isn't connected.

**XR framework** (`bl_xr/`) — A DOM-based UI system with GPU-rendered nodes, event dispatch, intersection testing, and a custom shader pipeline. Buttons, panels, images, and text all rendered directly in the XR viewport using `gpu.shader` and `batch_for_shader`.

**Application layer** (`blendlinkxr/`) — Tools (GP draw, erase, smooth, line, shapes, mesh editing, select, grab, clone), gizmos (cursor, laser pointer, MX Ink 3D model, color wheel, transform handles), navigation (grab, zoom, walk), and a complete settings system.

The Grease Pencil integration uses Blender 5.x's GP v3 Python API — `drawing.add_strokes()`, `stroke.add_points()`, per-point radius/opacity/color — creating native GP data that's fully editable on desktop.

The MX Ink 3D model was exported from the official FBX, triangulated, normals computed, and rendered with a custom Blinn-Phong shader for a glossy appearance. The tip aligns perfectly with the cursor.

## Challenges we ran into

**The MX Ink trigger mapping.** Our first attempt mapped tip force to the trigger action. It worked for clicking toolbar buttons but not for drawing — because tip force only activates on surface contact, not in mid-air. We had to rethink the entire control scheme: middle cluster force became the trigger (pressure-sensitive drawing), front click became squeeze (grab), and tip force became a separate pressure channel that feeds into stroke width.

**GP materials in Blender 5.x.** Regular materials created with `bpy.data.materials.new()` don't render as GP strokes — they show up white. GP materials require `is_grease_pencil=True` with a `MaterialGPencilStyle`, which can only be created by copying an existing GP material from an object made with `bpy.ops.object.grease_pencil_add()`. Took us hours to figure out why every stroke was white.

**The rename from Freebird XR.** We forked an open-source VR framework (GPL-2.0) and renamed every reference across 80+ Python files — module names, operator IDs, settings keys, collection names, scene properties, UI strings. One missed `fb_dir` variable in `save_settings_to_file()` crashed the entire plugin on menu toggle. Finding it took longer than the rename itself.

**Node tree mutation during draw.** The GPU renderer iterates the node tree every frame. Adding or removing children during the draw callback crashes Blender instantly. We learned to pre-create all UI nodes at module import time and only toggle visibility at runtime.

**Image loading in timers.** Calling `bpy.data.images.load()` inside an XR callback or application timer crashes Blender. Every image must be loaded at module import time. This constraint shaped the entire UI architecture.

## Accomplishments that we're proud of

**Daniel Martínez Lara noticed.** The creator of Blender's Grease Pencil toolset — Goya Award-winning director, 2026 Premio Segundo de Chomón recipient — shared BlendLink XR in Blender's official XR development channel. He called it "Interesting one of the projects from the Logitech Hackathon about Grease Pencil XR." This was in the same thread where Jeroen Bakker and Jonas Holzman, Blender's core XR developers, are working on controller model extensions. The people building Blender's future saw our work and took note.

**It actually works.** Not as a demo. As a tool. Artists have drawn with it, edited meshes, posed characters, and navigated scenes. The GP strokes are real Blender data. The mesh edits are real geometry. Take the headset off and everything is there on the desktop.

**The MX Ink control mapping feels right.** After three iterations of button remapping, the final scheme — middle cluster for pressure drawing, front click for grab, back click for tools, double-tap for undo — feels natural. Artists pick it up and start drawing without instructions.

**Seven brush presets with a color wheel in VR.** Pencil, Ink, Marker, Airbrush, Dot — each with distinct pressure curves, opacity, jitter, and softness. Plus an HSV color wheel rendered with a custom SMOOTH_COLOR shader. Artists can pick any color and any brush without leaving VR.

**A glossy 3D pen in your hand.** The MX Ink model renders with a custom Blinn-Phong shader — computed normals, specular highlights, dark charcoal finish. It looks like the real pen. The tip aligns with the cursor to the millimeter.

## What we learned

The MX Ink isn't a controller with extra buttons. It's a fundamentally different input device that requires a fundamentally different control architecture. You can't just map it to existing controller bindings and call it done. Every physical gesture needs to map to exactly one creative action, and every creative action needs exactly one gesture. Getting that mapping right took three complete rewrites.

Blender's Python API is remarkably powerful for VR addon development. The GP v3 stroke API, the XR session state, the GPU shader system — they're all accessible from Python. The limitations are real (no sculpt mode context in XR, no fill tool without screen projection) but the amount you can build without touching C++ is impressive.

The hardest bugs aren't the ones that throw errors. They're the ones where everything looks like it works but the strokes are white, or the pen points backward, or the trigger fires but nothing draws. Understanding the full pipeline — from OpenXR action to event dispatch to tool handler to Blender data — is the only way to debug these.

## What's next for BlendLink XR

**Core Blender contributions.** We're preparing patches for Blender's upstream codebase — MX Ink OpenXR profile support in GHOST, GP drawing context for XR sessions, viewport overlay controls exposed to Python. These go through Blender's standard review process and benefit the entire XR ecosystem.

**Horizon Link PC VR application.** Once the core changes land, we build a dedicated companion app on Meta Quest through Horizon Link. A Unity-based VR environment that captures MX Ink input at full fidelity and connects to Blender over a low-latency localhost bridge at 72–120Hz. The artist works in VR. Blender runs on the PC. The MX Ink connects the two.

**Sculpt mode integration.** Push, pull, smooth, and carve mesh surfaces with real pen pressure. This needs Blender-side context changes but the architecture is ready.

**Rotatable panel system.** Open Brush-style cylindrical tool panels that rotate with the joystick — three panels for Object, Edit, and Grease Pencil modes.

**GP stroke-level editing.** Select individual strokes, grab and reshape them, cut them at intersection points. Requires extending the intersection system to understand GP geometry.

The plugin is the proof of concept. The Horizon Link app is how it ships. The MX Ink is the reason both exist.

---

**GitHub:** [github.com/AbinjithTK/BlendLink-XR](https://github.com/AbinjithTK/BlendLink-XR)
