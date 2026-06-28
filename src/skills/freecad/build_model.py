#!/usr/bin/env python3
"""
FreeCAD Headless Model Builder — Generic Template

Usage:
    python3 build_model.py [output_dir]

Edit the PARAMETERS section and BUILD section for your specific geometry.
Everything else (document setup, save, verify) is handled automatically.
"""

import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
import math
import os


# ============================================================
# PARAMETERS (all in mm) — EDIT THESE FOR YOUR MODEL
# ============================================================
MODEL_NAME = "MyModel"
PART_NAME = "Part"

# Example parameters — replace with your own
# LENGTH = 100
# WIDTH = 50
# HEIGHT = 10


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def make_torus_segment(major_r, minor_r, angle_rad):
    """Create solid torus segment by revolving a disk face.
    
    Produces exact geometry with curved ends (no flat cutting surfaces).
    The disk is in the XZ plane, centered at (major_r, 0, 0), revolved around Z.
    
    Returns: Part.Solid
    """
    circle = Part.makeCircle(minor_r, App.Vector(major_r, 0, 0), App.Vector(0, 1, 0))
    wire = Part.Wire(circle.Edges)
    face = Part.Face(wire)  # disk face — CRITICAL: wire.revolve() creates Shell (wrong)
    solid = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), math.degrees(angle_rad))
    return solid


def make_hollow_torus_segment(major_r, r_outer, r_inner, angle_rad):
    """Create hollow torus segment by subtracting inner from outer.
    
    Returns: Part.Solid (4 faces: outer toroidal + inner toroidal + 2 end caps)
    """
    outer = make_torus_segment(major_r, r_outer, angle_rad)
    inner = make_torus_segment(major_r, r_inner, angle_rad)
    return outer.cut(inner)


def position_along_torus(shape, major_r, angle_rad):
    """Position and orient a shape tangent to a torus centerline at given angle.
    
    Shape should be a cylinder aligned along Z axis before calling.
    Rotates to align with torus tangent, then translates to centerline position.
    
    Returns: Transformed shape
    """
    # Rotate -90° around X to align cylinder from Z to Y
    shape = shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90)
    # Rotate around Z to align with torus tangent at angle
    shape = shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), math.degrees(angle_rad))
    # Translate to centerline position
    cx = major_r * math.cos(angle_rad)
    cy = major_r * math.sin(angle_rad)
    shape = shape.translate(App.Vector(cx, cy, 0))
    return shape


# ============================================================
# BUILD — EDIT THIS SECTION FOR YOUR GEOMETRY
# ============================================================

def build():
    """Build your geometry here. Returns a Part.Shape (Solid)."""
    
    # --- EXAMPLE: Solid torus segment with nudge ---
    # (Replace this with your own geometry)
    
    major_diameter = 1007
    tube_outer_diameter = 15
    arc_length = 200
    nudge_arc_length = 1
    nudge_outer_diameter = 20
    
    major_r = major_diameter / 2
    tube_outer_r = tube_outer_diameter / 2
    nudge_outer_r = nudge_outer_diameter / 2
    
    segment_angle = arc_length / major_r
    mid_angle = segment_angle / 2.0
    
    # Main body
    solid = make_torus_segment(major_r, tube_outer_r, segment_angle)
    
    # Nudge bulge
    nudge = Part.makeCylinder(nudge_outer_r, nudge_arc_length)
    nudge = position_along_torus(nudge, major_r, mid_angle)
    
    # Fuse into single object
    result = solid.fuse(nudge)
    
    # --- END EXAMPLE ---
    
    return result


# ============================================================
# SAVE AND VERIFY — DO NOT EDIT BELOW
# ============================================================

def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    
    print(f"Building {MODEL_NAME}...")
    result = build()
    
    # Verify shape
    if not result.isValid():
        print("ERROR: Resulting shape is invalid!")
        sys.exit(1)
    
    # Create document
    doc = App.newDocument(MODEL_NAME)
    part = doc.addObject("Part::Feature", PART_NAME)
    part.Shape = result
    doc.recompute()  # CRITICAL — always call before saving
    
    # Save
    fcstd_path = os.path.join(outdir, f"{MODEL_NAME}.FCStd")
    step_path = os.path.join(outdir, f"{MODEL_NAME}.step")
    
    doc.saveAs(fcstd_path)
    Part.export([part], step_path)
    
    # Verification
    bb = result.BoundBox
    print(f"\n=== VERIFICATION ===")
    print(f"Valid: {result.isValid()}")
    print(f"Volume: {abs(result.Volume):.1f} mm³")
    print(f"Faces: {result.Faces.__len__()}")
    print(f"BoundBox: {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} mm")
    print(f"Center: ({bb.Center.x:.1f}, {bb.Center.y:.1f}, {bb.Center.z:.1f})")
    print(f"\nSaved: {fcstd_path}")
    print(f"Exported: {step_path}")
    print("DONE")


if __name__ == '__main__':
    main()
