#!/usr/bin/env python3
"""
FreeCAD Model Verification Tool

Loads an FCStd file and prints detailed geometry information for verification.
Use this after building a model to confirm it's correct before generating screenshots.

Usage:
    python3 verify_model.py model.FCStd
    python3 verify_model.py model.FCStd --expected-volume 12345.6
    python3 verify_model.py model.FCStd --expected-bbox 100 50 10
"""

import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
import os


def verify(fcstd_path, expected_volume=None, expected_bbox=None):
    """Verify an FCStd model's geometry."""
    if not os.path.exists(fcstd_path):
        print(f"ERROR: File not found: {fcstd_path}")
        return False
    
    doc = App.openDocument(fcstd_path)
    
    issues = []
    for obj in doc.Objects:
        if not hasattr(obj, 'Shape'):
            continue
        
        shape = obj.Shape
        print(f"\n=== Object: {obj.Name} ===")
        
        # Validity
        if not shape.isValid():
            issues.append(f"{obj.Name}: Shape is INVALID")
            print("  Valid: NO")
        else:
            print("  Valid: YES")
        
        # Type
        print(f"  Type: {shape.ShapeType}")
        print(f"  Solid: {shape.isSolid()}")
        print(f"  Closed: {shape.isClosed()}")
        
        # Topology
        print(f"  Vertices: {len(shape.Vertexes)}")
        print(f"  Edges: {len(shape.Edges)}")
        print(f"  Faces: {len(shape.Faces)}")
        print(f"  Shells: {len(shape.Shells)}")
        
        # Volume
        vol = abs(shape.Volume)
        print(f"  Volume: {vol:.1f} mm³")
        if expected_volume is not None:
            ratio = vol / expected_volume if expected_volume > 0 else 0
            if abs(ratio - 1.0) > 0.01:  # 1% tolerance
                issues.append(f"{obj.Name}: Volume {vol:.1f} vs expected {expected_volume:.1f} (ratio {ratio:.3f})")
            else:
                print(f"  Volume check: PASS (expected {expected_volume:.1f}, ratio {ratio:.4f})")
        
        # Bounding box
        bb = shape.BoundBox
        dims = (bb.XLength, bb.YLength, bb.ZLength)
        print(f"  BoundBox: {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm")
        print(f"  Center: ({bb.Center.x:.1f}, {bb.Center.y:.1f}, {bb.Center.z:.1f})")
        print(f"  Extents: X[{bb.XMin:.1f}, {bb.XMax:.1f}] Y[{bb.YMin:.1f}, {bb.YMax:.1f}] Z[{bb.ZMin:.1f}, {bb.ZMax:.1f}]")
        
        if expected_bbox is not None:
            for i, (actual, expected) in enumerate(zip(dims, expected_bbox)):
                if abs(actual - expected) > expected * 0.01:  # 1% tolerance
                    axis = 'XYZ'[i]
                    issues.append(f"{obj.Name}: BBox {axis} {actual:.1f} vs expected {expected:.1f}")
        
        # Mass properties (for solid shapes)
        if shape.isSolid():
            mass_data = shape.MassProperties
            print(f"  Center of mass: ({mass_data[0].x:.2f}, {mass_data[0].y:.2f}, {mass_data[0].z:.2f})")
    
    if issues:
        print(f"\n=== ISSUES FOUND ({len(issues)}) ===")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n=== ALL CHECKS PASSED ===")
        return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 verify_model.py model.FCStd [--expected-volume V] [--expected-bbox X Y Z]")
        sys.exit(1)
    
    fcstd_path = sys.argv[1]
    
    expected_volume = None
    expected_bbox = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--expected-volume':
            expected_volume = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--expected-bbox':
            expected_bbox = (float(sys.argv[i + 1]), float(sys.argv[i + 2]), float(sys.argv[i + 3]))
            i += 4
        else:
            i += 1
    
    verify(fcstd_path, expected_volume, expected_bbox)
