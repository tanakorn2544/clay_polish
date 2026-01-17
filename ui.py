"""
Clay Polish UI Panel
"""

import bpy


def has_clay_polish_modifier(obj):
    """Check if object has Clay Polish GN modifier."""
    if obj is None or obj.type != 'MESH':
        return False
    node_group = bpy.data.node_groups.get("Clay Polish")
    if not node_group:
        return False
    return any(mod.type == 'NODES' and mod.node_group == node_group for mod in obj.modifiers)


class VIEW3D_PT_clay_polish(bpy.types.Panel):
    """Clay Polish panel in the N-Panel"""
    bl_label = "Clay Polish"
    bl_idname = "VIEW3D_PT_clay_polish"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Clay Polish"
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH':
            layout.label(text="Select a mesh object", icon='ERROR')
            return
        
        # Info
        col = layout.column(align=True)
        col.label(text=f"Object: {obj.name}", icon='MESH_DATA')
        vert_count = len(obj.data.vertices)
        col.label(text=f"Vertices: {vert_count:,}")
        
        # Check for modifiers
        has_multires = any(mod.type == 'MULTIRES' for mod in obj.modifiers)
        has_subsurf = any(mod.type == 'SUBSURF' for mod in obj.modifiers)
        has_cp_mod = has_clay_polish_modifier(obj)
        
        layout.separator()
        
        # === NON-DESTRUCTIVE (Geometry Nodes) ===
        box = layout.box()
        box.label(text="Non-Destructive (Recommended)", icon='MODIFIER')
        
        if has_cp_mod:
            # Already has modifier
            box.label(text="✓ Clay Polish modifier active", icon='CHECKMARK')
            row = box.row(align=True)
            row.operator("mesh.clay_polish_gn_remove", text="Remove", icon='X')
            if context.mode == 'OBJECT':
                row.operator("mesh.clay_polish_gn_apply", text="Apply", icon='CHECKMARK')
            box.label(text="Adjust settings in Modifier panel", icon='INFO')
        else:
            # Can add modifier
            box.operator("mesh.clay_polish_gn_add", text="Add Clay Polish Modifier", icon='ADD')
            if has_multires or has_subsurf:
                box.label(text="✓ Works with Multires!", icon='CHECKMARK')
        
        layout.separator()
        
        # === DESTRUCTIVE (Direct Apply) ===
        box2 = layout.box()
        box2.label(text="Direct Apply (Destructive)", icon='MESH_DATA')
        
        if context.mode != 'OBJECT':
            box2.label(text="Switch to Object Mode", icon='ERROR')
        else:
            box2.operator("mesh.clay_polish", text="Apply Clay Polish", icon='BRUSH_CLAY_STRIPS')
            if has_multires or has_subsurf:
                box2.label(text="⚠ Will apply modifiers", icon='ERROR')
        
        layout.separator()
        
        # Tips
        tips = layout.box()
        tips.label(text="Tips:", icon='INFO')
        col = tips.column(align=True)
        col.scale_y = 0.8
        col.label(text="• Non-destructive = adjust anytime")
        col.label(text="• Lower edge threshold = more edges preserved")
        col.label(text="• Higher strength = more planar surfaces")


classes = [
    VIEW3D_PT_clay_polish,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

