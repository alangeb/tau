#!/usr/bin/env python3
"""FreeCAD model script template — edit PARAMETERS and build() for your model."""

import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
import math
import os


# === PARAMETERS (all in mm) ===
# Define your geometry parameters here


# === BUILD ===
def build():
    """Build geometry — return a Shape object."""
    # Build geometry (Shape objects, NOT document objects)
    # ... your geometry code ...
    raise NotImplementedError("Edit build() to define your geometry")


def main():
    doc = App.newDocument("ModelName")

    result_shape = build()

    # Place in document
    part = doc.addObject("Part::Feature", "PartName")
    part.Shape = result_shape
    doc.recompute()  # CRITICAL — always call before saving

    # === SAVE ===
    outdir = os.path.dirname(os.path.abspath(__file__)) or "."
    os.makedirs(outdir, exist_ok=True)
    fcstd_path = os.path.join(outdir, "model.FCStd")
    step_path = os.path.join(outdir, "model.step")

    doc.saveAs(fcstd_path)
    Part.export([part], step_path)

    # === VERIFY ===
    bb = result_shape.BoundBox
    print(f"Volume: {abs(result_shape.Volume):.1f} mm³")
    print(f"Bounding box: {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} mm")
    print(f"Center: ({bb.Center.x:.1f}, {bb.Center.y:.1f}, {bb.Center.z:.1f})")
    print("DONE")


if __name__ == "__main__":
    main()
