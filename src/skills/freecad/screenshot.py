#!/usr/bin/env python3
"""
FreeCAD Headless Screenshot Generator (Matplotlib Wireframe)

Generates PNG wireframe views of FreeCAD models from multiple camera angles.
Uses matplotlib 3D plotting (no OpenGL required).

Usage:
    python3 screenshot.py model.FCStd [output_dir]
"""

import sys
sys.path.insert(0, '/usr/lib/freecad/lib')

import os
import math
import FreeCAD as App
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def generate_screenshots(fcstd_path, output_dir, angles=None):
    """Generate wireframe screenshots from an FCStd file."""
    if angles is None:
        angles = [
            (0, 30, 'Front-Top'),
            (45, 30, 'Front-Right-Top'),
            (90, 30, 'Right-Top'),
            (135, 30, 'Back-Right-Top'),
            (180, 30, 'Back-Top'),
            (225, 30, 'Back-Left-Top'),
            (270, 30, 'Left-Top'),
            (315, 30, 'Front-Left-Top'),
            (0, 60, 'Top-Down'),
            (45, 60, 'Front-Right-TopDown'),
            (90, 60, 'Right-TopDown'),
            (180, 60, 'Back-TopDown'),
            (270, 60, 'Left-TopDown'),
        ]

    # Open FCStd
    doc = App.open(fcstd_path)

    # Get the first valid shape
    shape = None
    for obj in doc.Objects:
        if hasattr(obj, 'Shape') and obj.Shape.isValid():
            shape = obj.Shape
            break
    if shape is None:
        print("ERROR: No valid shape found")
        return []

    # Tessellate
    verts, faces = shape.tessellate(1.0)
    vertices = np.array([[v.x, v.y, v.z] for v in verts])

    # Build unique edges for wireframe
    edge_set = set()
    for face in faces:
        for i in range(len(face)):
            a, b = face[i], face[(i + 1) % len(face)]
            edge_set.add((min(a, b), max(a, b)))
    edges = list(edge_set)

    # Render from multiple angles
    os.makedirs(output_dir, exist_ok=True)
    images = []
    for azim, elev, label in angles:
        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection='3d')

        # Plot edges
        for a, b in edges:
            xs = [vertices[a, 0], vertices[b, 0]]
            ys = [vertices[a, 1], vertices[b, 1]]
            zs = [vertices[a, 2], vertices[b, 2]]
            ax.plot(xs, ys, zs, c='steelblue', alpha=0.3, linewidth=0.5)

        # Plot vertices
        ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                   c='navy', s=0.5, alpha=0.3)

        # Set view angle
        ax.view_init(elev=elev, azim=azim)

        # Equal aspect ratio
        max_range = max(np.ptp(vertices[:, i]) for i in range(3)) / 2.0
        mid = [vertices[:, i].mean() for i in range(3)]
        ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
        ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
        ax.set_zlim(mid[2] - max_range, mid[2] + max_range)

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title(f'{doc.Label} - {label} View')

        path = os.path.join(output_dir, f"view_{azim:03d}_{elev:03d}.png")
        plt.savefig(path, dpi=100, bbox_inches='tight')
        plt.close()
        images.append(path)

    return images


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 screenshot.py model.FCStd [output_dir]")
        sys.exit(1)

    fcstd_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(fcstd_path), 'screenshots')

    print(f"Opening: {fcstd_path}")
    images = generate_screenshots(fcstd_path, output_dir)
    print(f"Generated {len(images)} screenshots in {output_dir}")
