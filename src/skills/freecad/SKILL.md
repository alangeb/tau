---
category: cad
description: "Headless 3D modeling with FreeCAD Python API — parametric geometry, boolean ops, STEP export, volume verification (also load: shell_scripting, background, image, performance)"
keywords: freecad, 3D modeling, parametric geometry, boolean operations, STEP export, volume verification, headless CAD, FreeCAD Python API
name: freecad
---

# FreeCAD Headless 3D Modeling

## When
"create 3D model", "CAD", "FreeCAD", "generate STEP", "FCStd", "3D geometry", "parametric part", "freecad script"

## Verification
Describe geometry → Write script → Run headless → Export → Screenshot → see() → Verify → Iterate. Verify: volume (computed vs analytical ±1%), wireframe screenshots, bounding box.

## Environment
FreeCAD 1.0.0, lib at `/usr/lib/freecad/lib`
```python
import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
```

PartDesignGui crashes, PartDesign missing, Coin3D offscreen needs GL, `subgraphFromObject()` needs GUI.

## Critical Patterns

### Torus Segments (`makeTorus` Has No Angle Param)
```python
def make_torus_segment(major_r, minor_r, angle_deg):
    circle = Part.makeCircle(minor_r, App.Vector(major_r, 0, 0), App.Vector(0, 1, 0))
    face = Part.Face(Part.Wire(circle.Edges))
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
```
`face.revolve()` → Solid. `wire.revolve()` → Shell (wrong).

### Booleans
```python
hollow = outer.cut(inner)    # Subtract
merged = s1.fuse(s2)         # Union
overlap = s1.common(s2)      # Intersection
```

## Helpers
`skills/freecad/build_model.py`, `verify_model.py`, `screenshot.py`, `model_template.py`, `screenshot_template.py`

## Gotchas
- Volume = 0: `common()` on non-overlapping — check positions
- Negative volume: use `face.revolve()` not `wire.revolve()`
- Shape not saved: missing `doc.recompute()` before save
- Boolean fails: shapes touching — add gap or `fuse()`
- `makeTorus` no angle: use `face.revolve()`
- `.Axis`/`.Radius` missing: on surface, not Solid

## Related Skills
`background`, `image`, `performance`, `shell_scripting`