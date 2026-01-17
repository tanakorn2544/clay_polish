"""
Clay Polish Operators
"""

import bpy
import bmesh
from bpy.props import FloatProperty, IntProperty, BoolProperty

from .polish import clay_polish_mesh
from .geometry_nodes import add_clay_polish_modifier, remove_clay_polish_modifier, get_or_create_clay_polish_node_group


class MESH_OT_clay_polish(bpy.types.Operator):
    """Apply ZBrush-style Clay Polish - flattens surfaces while preserving hard edges (destructive)"""
    bl_idname = "mesh.clay_polish"
    bl_label = "Clay Polish (Apply)"
    bl_options = {'REGISTER', 'UNDO'}
    
    strength: FloatProperty(
        name="Strength",
        description="Polish intensity - higher values create more planar surfaces",
        default=0.5,
        min=0.0,
        max=1.0,
        step=1,
        precision=2,
    )
    
    iterations: IntProperty(
        name="Iterations",
        description="Number of polish passes - more iterations = stronger effect",
        default=3,
        min=1,
        max=20,
    )
    
    edge_threshold: FloatProperty(
        name="Edge Threshold",
        description="Angle in degrees to detect hard edges (edges sharper than this are preserved)",
        default=30.0,
        min=0.0,
        max=180.0,
        step=100,
        precision=1,
        subtype='ANGLE',
    )
    
    keep_volume: BoolProperty(
        name="Keep Volume",
        description="Prevent mesh shrinkage by maintaining center of mass",
        default=True,
    )
    
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply Multires/Subdiv modifiers before polishing (creates high-poly result)",
        default=False,
    )
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == 'OBJECT'
    
    def execute(self, context):
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Check for Multires modifier
        has_multires = any(mod.type == 'MULTIRES' for mod in obj.modifiers)
        has_subsurf = any(mod.type == 'SUBSURF' for mod in obj.modifiers)
        
        if (has_multires or has_subsurf) and self.apply_modifiers:
            # Use evaluated mesh (with modifiers applied)
            success = self.polish_with_modifiers(context, obj)
        else:
            # Direct base mesh polish
            success = self.polish_base_mesh(obj)
        
        if success:
            self.report({'INFO'}, f"Clay Polish applied: {self.iterations} iterations, strength {self.strength:.2f}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to apply Clay Polish")
            return {'CANCELLED'}
    
    def polish_base_mesh(self, obj):
        """Polish the base mesh directly (no modifiers)."""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        clay_polish_mesh(
            bm,
            strength=self.strength,
            iterations=self.iterations,
            edge_threshold=self.edge_threshold,
            keep_volume=self.keep_volume
        )
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        return True
    
    def polish_with_modifiers(self, context, obj):
        """
        Polish mesh with modifiers applied.
        This creates a high-poly result but allows polishing of Multires/Subdiv meshes.
        """
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        
        # Get evaluated mesh
        mesh_eval = obj_eval.to_mesh()
        
        if mesh_eval is None:
            return False
        
        # Create bmesh from evaluated mesh
        bm = bmesh.new()
        bm.from_mesh(mesh_eval)
        
        # Apply polish
        clay_polish_mesh(
            bm,
            strength=self.strength,
            iterations=self.iterations,
            edge_threshold=self.edge_threshold,
            keep_volume=self.keep_volume
        )
        
        # Create new mesh data
        new_mesh = bpy.data.meshes.new(name=obj.data.name + "_polished")
        bm.to_mesh(new_mesh)
        bm.free()
        
        # Clean up evaluated mesh
        obj_eval.to_mesh_clear()
        
        # Remove modifiers that were applied
        modifiers_to_remove = []
        for mod in obj.modifiers:
            if mod.type in {'MULTIRES', 'SUBSURF'}:
                modifiers_to_remove.append(mod.name)
        
        for mod_name in modifiers_to_remove:
            obj.modifiers.remove(obj.modifiers[mod_name])
        
        # Replace mesh data
        old_mesh = obj.data
        obj.data = new_mesh
        
        # Remove old mesh if not used elsewhere
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        
        obj.data.update()
        return True
    
    def invoke(self, context, event):
        # Check for modifiers and show dialog if needed
        obj = context.active_object
        has_multires = any(mod.type == 'MULTIRES' for mod in obj.modifiers)
        has_subsurf = any(mod.type == 'SUBSURF' for mod in obj.modifiers)
        
        if has_multires or has_subsurf:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "strength")
        layout.prop(self, "iterations")
        layout.prop(self, "edge_threshold")
        layout.prop(self, "keep_volume")
        
        # Check for modifiers
        obj = context.active_object
        has_multires = any(mod.type == 'MULTIRES' for mod in obj.modifiers)
        has_subsurf = any(mod.type == 'SUBSURF' for mod in obj.modifiers)
        
        if has_multires or has_subsurf:
            layout.separator()
            box = layout.box()
            box.label(text="Modifiers Detected", icon='MODIFIER')
            box.prop(self, "apply_modifiers")
            if self.apply_modifiers:
                box.label(text="⚠ This will apply modifiers!", icon='ERROR')


class MESH_OT_clay_polish_gn_add(bpy.types.Operator):
    """Add non-destructive Clay Polish modifier - Curvature-based smoothing"""
    bl_idname = "mesh.clay_polish_gn_add"
    bl_label = "Add Clay Polish (Non-Destructive)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        mod = add_clay_polish_modifier(obj)
        
        if mod:
            self.report({'INFO'}, "Clay Polish added - adjust Curvature Threshold in modifier panel")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to add Clay Polish modifier")
            return {'CANCELLED'}



class MESH_OT_clay_polish_gn_remove(bpy.types.Operator):
    """Remove Clay Polish modifier"""
    bl_idname = "mesh.clay_polish_gn_remove"
    bl_label = "Remove Clay Polish Modifier"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        # Check if Clay Polish modifier exists
        node_group = bpy.data.node_groups.get("Clay Polish")
        if not node_group:
            return False
        return any(mod.type == 'NODES' and mod.node_group == node_group for mod in obj.modifiers)
    
    def execute(self, context):
        obj = context.active_object
        
        if remove_clay_polish_modifier(obj):
            self.report({'INFO'}, "Clay Polish modifier removed")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No Clay Polish modifier found")
            return {'CANCELLED'}


class MESH_OT_clay_polish_gn_apply(bpy.types.Operator):
    """Apply Clay Polish modifier to mesh"""
    bl_idname = "mesh.clay_polish_gn_apply"
    bl_label = "Apply Clay Polish Modifier"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        if context.mode != 'OBJECT':
            return False
        # Check if Clay Polish modifier exists
        node_group = bpy.data.node_groups.get("Clay Polish")
        if not node_group:
            return False
        return any(mod.type == 'NODES' and mod.node_group == node_group for mod in obj.modifiers)
    
    def execute(self, context):
        obj = context.active_object
        node_group = bpy.data.node_groups.get("Clay Polish")
        
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_group:
                bpy.ops.object.modifier_apply(modifier=mod.name)
                self.report({'INFO'}, "Clay Polish applied to mesh")
                return {'FINISHED'}
        
        self.report({'WARNING'}, "No Clay Polish modifier found")
        return {'CANCELLED'}


classes = [
    MESH_OT_clay_polish,
    MESH_OT_clay_polish_gn_add,
    MESH_OT_clay_polish_gn_remove,
    MESH_OT_clay_polish_gn_apply,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


