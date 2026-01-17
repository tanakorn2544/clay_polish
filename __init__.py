# Clay Polish
# ZBrush-style Clay Polish tool for Blender

bl_info = {
    "name": "Clay Polish",
    "author": "Korn Sensei",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-Panel > Clay Polish",
    "description": "ZBrush-style Clay Polish - flattens surfaces while preserving hard edges",
    "category": "Mesh",
}

import bpy

from . import operators
from . import ui

classes = []

def register():
    operators.register()
    ui.register()

def unregister():
    ui.unregister()
    operators.unregister()

if __name__ == "__main__":
    register()
