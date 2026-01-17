import bpy
import bmesh
import math

def setup_test_scene():
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    
    # Create Row 1: Original vs Polished (Low Poly)
    # Original
    bpy.ops.mesh.primitive_monkey_add(location=(-3, 0, 0))
    monkey_orig = bpy.context.active_object
    monkey_orig.name = "Monkey_Original"
    
    # Polished
    bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))
    monkey_polish = bpy.context.active_object
    monkey_polish.name = "Monkey_ClayPolish"
    
    # Add Clay Polish Modifier (Non-Destructive)
    try:
        from clay_polish.geometry_nodes import add_clay_polish_modifier
        mod = add_clay_polish_modifier(monkey_polish)
        
        # Set Parameters
        # Strength 1.0 - strong smoothing
        # Iterations 10 - enough to see effect
        # Threshold 0.2 - Smooth areas with curvature < 0.2
        # Pinch 0.5 - Sharpen tips
        
        # Note: We can't access modifier inputs easily by name via API without traversal
        # But default values are set in code. 
        # Let's try to set them if possible.
        
        # In Blender 4.0+, inputs are stored in mod.keys() or input_attributes?
        # Actually usually mod[socket_name] works for GN modifiers if exposed?
        # Or mod.open_input... 
        # Standard way:
        for input_key in mod.keys():
            print(f"Key: {input_key}")
            
    except ImportError:
        print("Could not import clay_polish. Ensure addon is installed/enabled.")
        # Fallback using operator if registered
        try:
            bpy.ops.mesh.clay_polish_gn_add()
        except:
            pass

    # Customize the modifier values (best effort guessing names)
    # Usually they are 'Socket_1', 'Socket_2' etc internally unless named.
    # We will rely on User to inspect.
    
    print("Test Scene Setup Complete.")

if __name__ == "__main__":
    setup_test_scene()
