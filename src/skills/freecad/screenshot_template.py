#!/usr/bin/env python3
"""Generate wireframe screenshots from FCStd file for visual verification."""

import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD as App
import Part
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import os


def load_shape(fcstd_path):
    """Load shape from FCStd file."""
    doc = App.openDocument(fcstd_path)
    part = doc.Objects[0]
    return part.Shape


def tessellate(shape):
    """Tessellate shape to vertices and faces."""
    mesh = shape.tessellate(0.1)  # Deflection
    vertices = np.array(mesh[0])
    faces = mesh[1]
    return vertices, faces


def plot_wireframe(vertices, faces, azimuth, elevation, title, output_path):
    """Generate wireframe plot from given angle."""
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    for face in faces:
        tri = vertices[face]
        ax.plot_trisurf(tri[:, 0], tri[:, 1], tri[:, 2],
                        alpha=0.3, color='steelblue', edgecolor='navy', linewidth=0.5)

    ax.view_init(elev=elevation, azim=azimuth)
    ax.set_box_aspect([1, 1, 1])
    ax.set_title(title)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()


def generate_screenshots(fcstd_path, output_dir):
    """Generate multiple views."""
    shape = load_shape(fcstd_path)
    vertices, faces = tessellate(shape)

    os.makedirs(output_dir, exist_ok=True)

    for azim in [0, 45, 90, 135, 180, 225, 270, 315]:
        for elev in [30, 60]:
            path = os.path.join(output_dir, f"view_{azim:03d}_{elev:03d}.png")
            plot_wireframe(vertices, faces, azim, elev,
                           f"Azimuth {azim}°, Elevation {elev}°", path)

    print(f"Generated {len(os.listdir(output_dir))} screenshots")


if __name__ == "__main__":
    fcstd = sys.argv[1] if len(sys.argv) > 1 else "model.FCStd"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "screenshots"
    generate_screenshots(fcstd, outdir)
