# BlendLink XR

**The first integration of the Logitech MX Ink with professional 3D creation software.**

---

4.2 million people use Blender every month. They sculpt characters, paint textures, animate films, and build game worlds — all by dragging a mouse across a flat screen. The depth they create is real. The way they create it is not.

The MX Ink is a spatial stylus that tracks tip position, rotation, and analog pressure in 3D space. It was built for precision work. But right now, no professional creative tool uses it as one.

We built the bridge.

---

## What BlendLink XR Does

BlendLink XR is a Blender plugin that maps every MX Ink input directly to Blender's creation tools through OpenXR. No companion app. No streaming middleware. Press Start VR in Blender, put on a Quest headset, and your scene opens around you with the MX Ink in your hand.

The middle cluster is your pressure-sensitive trigger — squeeze harder, draw thicker. Front click grabs objects and moves them through space. Back click opens a radial tool menu. Double-tap to undo. Dock the pen and all input pauses. Every gesture maps to exactly one creative action. Every action has exactly one gesture.

A glossy 3D model of the actual MX Ink renders in the headset. You see what you're holding. You work with what you see.

---

## What Artists Can Do Right Now

**Draw.** Grease Pencil strokes with seven brush presets, an HSV color wheel, pressure-sensitive width, proximity erase, and stroke smoothing. Every mark is native Blender data — editable on desktop the moment the headset comes off.

**Build.** Shapes, NURBS curves, convex hulls — created by moving your hand through space. Straight lines between two points. Pipes with adjustable thickness.

**Edit.** Bevel, inset, extrude, loop cut, merge, make face. Grab a vertex and pull. No keyboard shortcuts. No menu diving. Point at it, click it, move it.

**Navigate.** Squeeze to grab the world. Both hands to zoom. Walk mode with the thumbstick. Reset scale with one button. Lock Z rotation so nobody gets sick.

**Pose.** Grab a bone, move it. The chain follows. Like posing a figure on your desk — except the figure is your rigged character inside the scene you built.

---

## Why MX Ink Makes This Possible

Touch controllers work with BlendLink XR. But the MX Ink is why it exists.

A controller gives you a trigger and a thumbstick. The MX Ink gives you analog pressure on the barrel, sub-millimeter tip tracking, two cluster buttons with double-tap, and a dock sensor. That is not more buttons. That is a different input language — one that matches how artists already think. Press harder for thicker lines. Angle the pen for direction. Lift to stop.

No other input device available on Quest delivers this. The MX Ink is the only hardware that makes pressure-sensitive 3D drawing, precision mesh editing, and natural object manipulation possible in a single tool. BlendLink XR is the software that proves it.

---

## Recognized by Blender's Core Developers

Daniel Martínez Lara — the creator of Blender's Grease Pencil toolset, Goya Award-winning director of *Alike*, and 2026 Premio Segundo de Chomón recipient for technical contributions to the film industry — shared BlendLink XR in Blender's official XR development channel:

> *"Interesting one of the projects from the Logitech Hackathon about Grease Pencil XR"*

This was posted in the same thread where Jeroen Bakker and Jonas Holzman — Blender's core XR developers — are actively working on controller model extensions and OpenXR improvements. The project sits directly in the path of where Blender's XR infrastructure is heading.

When the person who built the tool you're extending notices your work and shares it with the team building the platform you're targeting — that's not marketing. That's signal.

---

## Where This Goes Next

The plugin proves the concept. The next step is a dedicated **Horizon Link PC VR application**.

We are contributing core changes upstream to Blender — MX Ink OpenXR profile support in GHOST, GP drawing context for XR sessions, viewport overlay controls. These patches go through Blender's standard review process and benefit the entire XR ecosystem.

Once those land, we build a purpose-built companion app on Meta Quest through Horizon Link. A Unity-based VR environment that captures MX Ink input at full fidelity and connects to Blender over a low-latency localhost bridge at 72–120Hz. The artist works in VR. Blender runs on the PC. The MX Ink connects the two — with no compromise on either side.

**The plugin is the proof. The Horizon Link app is how it ships.**

---

## Current Status

- Working alpha, publicly released on GitHub
- Open-source, GPL-2.0 licensed
- Patched Blender 5.2 build with native MX Ink OpenXR profile support
- Full VR toolbar with GP drawing, mesh editing, object manipulation
- Seven brush presets with HSV color wheel
- Custom glossy MX Ink 3D model rendered in-headset
- Validated by Blender's creative community and XR developers

---

## What We Are Looking For

BlendLink XR puts the MX Ink in front of the largest open-source 3D community in the world. We are looking to work with Logitech to refine the integration, expand the toolset, and make the MX Ink the default creative input device for spatial 3D work in Blender.

4.2 million artists. One pen. The software to connect them exists. It works today.

---

**GitHub:** [github.com/AbinjithTK/BlendLink-XR](https://github.com/AbinjithTK/BlendLink-XR)
