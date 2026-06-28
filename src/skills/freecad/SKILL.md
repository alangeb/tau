---
name: freecad
description: Headless FreeCAD 3D modeling — build geometry via Python, verify with screenshots and volume checks, export FCStd/STEP. CAD, 3D modeling, FreeCAD, parametric, closed-loop verification (also load: background, image)
category: cad
keywords: freecad, CAD, 3D, modeling, geometry, STEP, FCStd, parametric, volume, screenshot
---

# FreeCAD Headless 3D Modeling

## When
"create 3D model", "CAD", "FreeCAD", "generate STEP", "FCStd", "3D geometry", "parametric part", "freecad script"

## Closed-Loop Verification
```
Describe geometry → Write Python script → Run headless → Export → Screenshot → see() → Verify → Iterate
```

Cannot see 3D directly. Verify via THREE methods:
1. **Volume**: Compare computed vs analytical (±1%)
2. **Wireframe screenshots**: Multiple angles confirm topology
3. **Bounding box**: Dimensions match expected

All three agree → model correct. Any disagree → investigate.

## Environment
- Version: FreeCAD 1.0.0, lib at `/usr/lib/freecad/lib`
- Run: `python3 script.py` (with `sys.path.insert`)

```python
import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
```

### Works Headlessly
Part workbench, Sketcher, File I/O (FCStd/STEP/STL/IGES/BREP), Matplotlib wireframe

### Does NOT Work
PartDesignGui (crashes), PartDesign module (missing), Coin3D offscreen (needs GL), `subgraphFromObject()` (needs GUI)

## Primitives
```python
Part.makeBox(l, w, h)
Part.makeCylinder(radius, height)  # Along Z
Part.makeSphere(radius)
Part.makeCone(r_bottom, r_top, height)
```

## Critical Patterns

### Torus Segments (`makeTorus` Has No Angle Param)
```python
def make_torus_segment(major_r, minor_r, angle_deg):
    circle = Part.makeCircle(minor_r, App.Vector(major_r, 0, 0), App.Vector(0, 1, 0))
    face = Part.Face(Part.Wire(circle.Edges))
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
```
`face.revolve()` → Solid (correct). `wire.revolve()` → Shell (wrong).

### Booleans
```python
hollow = outer.cut(inner)    # Subtract
merged = s1.fuse(s2)         # Union
overlap = s1.common(s2)      # Intersection
```

### Transforms
```python
shape = shape.translate(App.Vector(dx, dy, dz))
shape = shape.rotate(center, axis, angle_deg)
shape = shape.scale(factor)
```

## Workflow
```bash
python3 skills/freecad/build_model.py          # Build
python3 skills/freecad/verify_model.py m.FCStd # Verify volume/bbox
python3 skills/freecad/screenshot.py m.FCStd screenshots/
see(path="screenshots/view_045_030.png")       # Inspect
```

## Gotchas
| Problem | Cause | Fix |
|---------|-------|-----|
| Volume = 0 | `common()` on non-overlapping | Check positions |
| Negative volume | `wire.revolve()` → shell | Use `face.revolve()` |
| Shape not saved | Missing `doc.recompute()` | Always call before save |
| Boolean fails | Shapes touching | Add gap or `fuse()` |
| `makeTorus` no angle | API limitation | Use `face.revolve()` |
| `.Axis`/`.Radius` missing | On surface, not Solid | Use surface object |

## Checklist
1. [ ] Parameters defined (mm)
2. [ ] Shape objects (not document)
3. [ ] `face.revolve()` for torus segments
4. [ ] Fuse overlapping shapes
5. [ ] `Part::Feature` + `doc.recompute()`
6. [ ] Save FCStd + export STEP
7. [ ] Verify volume/bbox
8. [ ] Screenshots via `see` tool
9. [ ] Compare volume vs analytical

## Helpers
```bash
python3 skills/freecad/build_model.py          # Build model
python3 skills/freecad/model_template.py       # Template script
python3 skills/freecad/screenshot.py           # Wireframe screenshots
python3 skills/freecad/screenshot_template.py  # Screenshot template
python3 skills/freecad/verify_model.py         # Volume/bbox verification
```

## Related Skills
- `image` — image loading and vision models
- `background` — run FreeCAD scripts in background
- `shell_scripting` — automate build/verify pipeline
