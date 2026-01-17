"""
Geometry Nodes Clay Polish - Curvature Based
Smooths curved areas while preserving flat/planar regions
Now with Pinch Tips to sharpen pointy areas
Compatible with Blender 4.0+
"""

import bpy
import math


def get_or_create_clay_polish_node_group():
    """Get or create the Clay Polish node group."""
    name = "Clay Polish"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    
    ng = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    create_clay_polish_interface(ng)
    create_clay_polish_nodes(ng)
    return ng


def create_clay_polish_interface(node_group):
    """Create node group interface with parameters."""
    interface = node_group.interface
    interface.clear()
    
    # Inputs
    interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    
    # Strength: overall smoothing intensity
    strength = interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    strength.default_value = 1.0
    strength.min_value = 0.0
    strength.max_value = 5.0
    
    # Iterations: smoothing passes
    iterations = interface.new_socket(name="Iterations", in_out='INPUT', socket_type='NodeSocketInt')
    iterations.default_value = 5
    iterations.min_value = 1
    iterations.max_value = 50
    
    # Curvature Threshold: how much curvature before smoothing kicks in
    curvature_thresh = interface.new_socket(name="Curvature Threshold", in_out='INPUT', socket_type='NodeSocketFloat')
    curvature_thresh.default_value = 0.1
    curvature_thresh.min_value = 0.0
    curvature_thresh.max_value = 1.0
    
    # Pinch Tips: sharpen/exaggerate pointy areas
    pinch = interface.new_socket(name="Pinch Tips", in_out='INPUT', socket_type='NodeSocketFloat')
    pinch.default_value = 0.0  # Off by default
    pinch.min_value = -1.0  # Negative = anti-pinch (round tips)
    pinch.max_value = 1.0   # Positive = pinch inward
    
    # Keep Volume: blend with original
    volume = interface.new_socket(name="Keep Volume", in_out='INPUT', socket_type='NodeSocketFloat')
    volume.default_value = 0.3
    volume.min_value = 0.0
    volume.max_value = 1.0
    
    # Output
    interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')


def create_clay_polish_nodes(node_group):
    """Create curvature-based clay polish nodes with pinch tips."""
    nodes = node_group.nodes
    links = node_group.links
    nodes.clear()
    
    # === INPUT/OUTPUT ===
    g_in = nodes.new('NodeGroupInput')
    g_in.location = (-1600, 0)
    
    g_out = nodes.new('NodeGroupOutput')
    g_out.location = (1400, 0)
    
    # === ORIGINAL POSITION & NORMAL ===
    pos = nodes.new('GeometryNodeInputPosition')
    pos.location = (-1400, -100)
    pos.label = "Original Position"
    
    normal = nodes.new('GeometryNodeInputNormal')
    normal.location = (-1400, -300)
    normal.label = "Vertex Normal"
    
    # === CURVATURE DETECTION ===
    # Blur normals to get neighborhood average
    blur_normal = nodes.new('GeometryNodeBlurAttribute')
    blur_normal.location = (-1200, -300)
    blur_normal.data_type = 'FLOAT_VECTOR'
    blur_normal.label = "Blur Normal"
    blur_normal.inputs['Iterations'].default_value = 3
    blur_normal.inputs['Weight'].default_value = 1.0
    
    links.new(normal.outputs['Normal'], blur_normal.inputs['Value'])
    
    # Calculate difference (curvature)
    subtract_normals = nodes.new('ShaderNodeVectorMath')
    subtract_normals.location = (-1000, -300)
    subtract_normals.operation = 'SUBTRACT'
    subtract_normals.label = "Normal Diff"
    
    links.new(normal.outputs['Normal'], subtract_normals.inputs[0])
    links.new(blur_normal.outputs['Value'], subtract_normals.inputs[1])
    
    # Get curvature magnitude
    curvature_length = nodes.new('ShaderNodeVectorMath')
    curvature_length.location = (-800, -300)
    curvature_length.operation = 'LENGTH'
    curvature_length.label = "Curvature"
    
    links.new(subtract_normals.outputs['Vector'], curvature_length.inputs[0])
    
    # Curvature factor (Inverted: Smooth LOW curvature, Preserve HIGH curvature)
    # Map Curvature: 0.0 -> Threshold returns 1.0 -> 0.0
    map_range = nodes.new('ShaderNodeMapRange')
    map_range.location = (-400, -300)
    map_range.label = "Curvature Weight"
    map_range.interpolation_type = 'SMOOTHSTEP'
    map_range.inputs['From Min'].default_value = 0.0
    map_range.inputs['To Min'].default_value = 1.0
    map_range.inputs['To Max'].default_value = 0.0
    
    links.new(curvature_length.outputs['Value'], map_range.inputs['Value'])
    links.new(g_in.outputs['Curvature Threshold'], map_range.inputs['From Max'])
    
    # Store result for weight mult
    curvature_weight_socket = map_range.outputs['Result']
    
    # === SMOOTHING WEIGHT ===
    weight_mult = nodes.new('ShaderNodeMath')
    weight_mult.location = (0, -200)
    weight_mult.operation = 'MULTIPLY'
    weight_mult.label = "Smooth Weight"
    
    links.new(g_in.outputs['Strength'], weight_mult.inputs[0])
    links.new(curvature_weight_socket, weight_mult.inputs[1])
    
    # === BLUR POSITION (SMOOTHING) ===
    blur_pos = nodes.new('GeometryNodeBlurAttribute')
    blur_pos.location = (200, 0)
    blur_pos.data_type = 'FLOAT_VECTOR'
    blur_pos.label = "Smooth Positions"
    
    links.new(pos.outputs['Position'], blur_pos.inputs['Value'])
    links.new(g_in.outputs['Iterations'], blur_pos.inputs['Iterations'])
    links.new(weight_mult.outputs['Value'], blur_pos.inputs['Weight'])
    
    # === PINCH TIPS ===
    # Detect convex tips using Edge Angle (signed)
    edge_angle = nodes.new('GeometryNodeInputMeshEdgeAngle')
    edge_angle.location = (-1200, -550)
    edge_angle.label = "Edge Angle"
    
    # Signed angle: positive = convex (tip), negative = concave (valley)
    # We want to pinch convex tips inward along their normal
    
    # Scale pinch by edge convexity
    # Positive signed angle = convex tip → push inward (opposite of normal)
    pinch_scale = nodes.new('ShaderNodeMath')
    pinch_scale.location = (-800, -550)
    pinch_scale.operation = 'MULTIPLY'
    pinch_scale.label = "Pinch Scale"
    
    links.new(edge_angle.outputs['Signed Angle'], pinch_scale.inputs[0])
    links.new(g_in.outputs['Pinch Tips'], pinch_scale.inputs[1])
    
    # Scale factor for displacement
    pinch_mult = nodes.new('ShaderNodeMath')
    pinch_mult.location = (-600, -550)
    pinch_mult.operation = 'MULTIPLY'
    pinch_mult.inputs[1].default_value = 0.1  # Scale down for reasonable effect
    pinch_mult.label = "Pinch Amount"
    
    links.new(pinch_scale.outputs['Value'], pinch_mult.inputs[0])
    
    # Create pinch offset vector (along normal)
    pinch_offset = nodes.new('ShaderNodeVectorMath')
    pinch_offset.location = (-400, -550)
    pinch_offset.operation = 'SCALE'
    pinch_offset.label = "Pinch Offset"
    
    links.new(normal.outputs['Normal'], pinch_offset.inputs[0])
    links.new(pinch_mult.outputs['Value'], pinch_offset.inputs['Scale'])
    
    # Add pinch offset to smoothed position
    add_pinch = nodes.new('ShaderNodeVectorMath')
    add_pinch.location = (400, 0)
    add_pinch.operation = 'ADD'
    add_pinch.label = "Apply Pinch"
    
    links.new(blur_pos.outputs['Value'], add_pinch.inputs[0])
    links.new(pinch_offset.outputs['Vector'], add_pinch.inputs[1])
    
    # === VOLUME PRESERVATION MIX ===
    vol_mix = nodes.new('ShaderNodeMix')
    vol_mix.location = (600, 0)
    vol_mix.data_type = 'VECTOR'
    vol_mix.blend_type = 'MIX'
    vol_mix.label = "Volume Mix"
    
    links.new(g_in.outputs['Keep Volume'], vol_mix.inputs['Factor'])
    links.new(add_pinch.outputs['Vector'], vol_mix.inputs['A'])  # Effect
    links.new(pos.outputs['Position'], vol_mix.inputs['B'])  # Original
    
    # === SET POSITION ===
    set_pos = nodes.new('GeometryNodeSetPosition')
    set_pos.location = (800, 0)
    
    links.new(g_in.outputs['Geometry'], set_pos.inputs['Geometry'])
    links.new(vol_mix.outputs['Result'], set_pos.inputs['Position'])
    
    # === OUTPUT ===
    links.new(set_pos.outputs['Geometry'], g_out.inputs['Geometry'])


# =============================================================================
# MODIFIER FUNCTIONS
# =============================================================================

def add_clay_polish_modifier(obj, variant="curvature"):
    """Add Clay Polish modifier to object."""
    if obj.type != 'MESH':
        return None
    
    node_group = get_or_create_clay_polish_node_group()
    
    # Check if already exists
    for mod in obj.modifiers:
        if mod.type == 'NODES' and mod.node_group == node_group:
            return mod
    
    # Add modifier
    mod = obj.modifiers.new(name="Clay Polish", type='NODES')
    mod.node_group = node_group
    
    return mod


def remove_clay_polish_modifier(obj):
    """Remove Clay Polish modifier."""
    if obj.type != 'MESH':
        return False
    
    for mod in list(obj.modifiers):
        if mod.type == 'NODES' and mod.node_group and "Clay Polish" in mod.node_group.name:
            obj.modifiers.remove(mod)
            return True
    
    return False
