"""
Clay Polish Core Algorithm
NumPy-accelerated planar smoothing with edge preservation
"""

import numpy as np
import bmesh
from mathutils import Vector


def build_adjacency_data(bm):
    """
    Build vertex adjacency map and face normals for the mesh.
    Returns:
        - vert_neighbors: dict mapping vert index to list of neighbor indices
        - vert_faces: dict mapping vert index to list of face indices
        - face_normals: numpy array of face normals
    """
    vert_neighbors = {v.index: [] for v in bm.verts}
    vert_faces = {v.index: [] for v in bm.verts}
    
    # Build neighbor map from edges
    for edge in bm.edges:
        v1, v2 = edge.verts[0].index, edge.verts[1].index
        vert_neighbors[v1].append(v2)
        vert_neighbors[v2].append(v1)
    
    # Build vertex-to-face map
    for face in bm.faces:
        for vert in face.verts:
            vert_faces[vert.index].append(face.index)
    
    # Get face normals as numpy array
    face_normals = np.array([list(f.normal) for f in bm.faces], dtype=np.float64)
    
    return vert_neighbors, vert_faces, face_normals


def detect_hard_edges(bm, edge_threshold_rad):
    """
    Detect hard edges based on angle between adjacent faces.
    Returns a set of frozensets representing hard edge vertex pairs.
    """
    hard_edges = set()
    
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            f1, f2 = edge.link_faces
            angle = f1.normal.angle(f2.normal)
            if angle > edge_threshold_rad:
                v1, v2 = edge.verts[0].index, edge.verts[1].index
                hard_edges.add(frozenset([v1, v2]))
    
    return hard_edges


def compute_local_plane_normal(positions, neighbor_indices):
    """
    Compute the average normal of the local neighborhood using covariance/PCA.
    This gives us the best-fit plane normal for the neighborhood.
    """
    if len(neighbor_indices) < 3:
        return None
    
    # Get neighbor positions
    neighbor_pos = positions[neighbor_indices]
    
    # Compute centroid
    centroid = np.mean(neighbor_pos, axis=0)
    
    # Center the points
    centered = neighbor_pos - centroid
    
    # Compute covariance matrix
    cov = np.dot(centered.T, centered)
    
    # Get eigenvectors - smallest eigenvalue's vector is the plane normal
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Smallest eigenvalue corresponds to the normal direction
        plane_normal = eigenvectors[:, 0]
        return plane_normal, centroid
    except:
        return None


def project_to_plane(point, plane_normal, plane_point):
    """Project a point onto a plane defined by normal and a point on the plane."""
    v = point - plane_point
    dist = np.dot(v, plane_normal)
    return point - dist * plane_normal


def compute_mesh_volume(bm):
    """
    Calculate the signed volume of a closed mesh using the divergence theorem.
    Works by summing signed tetrahedron volumes from origin to each face.
    """
    volume = 0.0
    for face in bm.faces:
        if len(face.verts) >= 3:
            # For each triangle in the face
            v0 = face.verts[0].co
            for i in range(1, len(face.verts) - 1):
                v1 = face.verts[i].co
                v2 = face.verts[i + 1].co
                # Signed volume of tetrahedron from origin
                volume += v0.dot(v1.cross(v2)) / 6.0
    return abs(volume)


def get_vertex_normals(bm, num_verts):
    """Get vertex normals as numpy array."""
    normals = np.zeros((num_verts, 3), dtype=np.float64)
    for v in bm.verts:
        normals[v.index] = list(v.normal)
    return normals


def clay_polish_mesh(bm, strength=0.5, iterations=3, edge_threshold=30.0, keep_volume=True):
    """
    Apply Clay Polish effect to a bmesh.
    
    Uses Taubin-style two-step method:
    1. Polish step - flatten toward local planes
    2. Inflate step - push outward along normals to restore volume
    
    Args:
        bm: BMesh object
        strength: Polish intensity (0.0 - 1.0)
        iterations: Number of polish passes
        edge_threshold: Angle in degrees to detect hard edges
        keep_volume: If True, apply volume preservation correction
    """
    if len(bm.verts) == 0:
        return
    
    # Ensure lookup tables
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # Convert threshold to radians
    edge_threshold_rad = np.radians(edge_threshold)
    
    # Build adjacency data
    vert_neighbors, vert_faces, face_normals = build_adjacency_data(bm)
    
    # Detect hard edges
    hard_edges = detect_hard_edges(bm, edge_threshold_rad)
    
    # Get vertex positions as numpy array
    num_verts = len(bm.verts)
    positions = np.array([list(v.co) for v in bm.verts], dtype=np.float64)
    
    # Track original volume and center
    if keep_volume:
        original_volume = compute_mesh_volume(bm)
        original_center = np.mean(positions, axis=0)
    
    # Taubin lambda/mu parameters for volume preservation
    # lambda = positive (shrinking), mu = negative (inflating)
    # |mu| > lambda ensures volume preservation
    taubin_lambda = strength * 0.5
    taubin_mu = -strength * 0.53  # Slightly stronger inflation
    
    # Iterative polish with Taubin two-step
    for iteration in range(iterations):
        # === STEP 1: Polish (shrinking step) ===
        new_positions = positions.copy()
        
        for vi in range(num_verts):
            neighbors = vert_neighbors[vi]
            if len(neighbors) < 3:
                continue
            
            # Filter neighbors - don't cross hard edges
            valid_neighbors = []
            for ni in neighbors:
                edge_key = frozenset([vi, ni])
                if edge_key not in hard_edges:
                    valid_neighbors.append(ni)
            
            if len(valid_neighbors) < 3:
                continue
            
            # Include the vertex itself in plane calculation
            all_indices = valid_neighbors + [vi]
            
            # Compute local plane
            result = compute_local_plane_normal(positions, np.array(all_indices))
            if result is None:
                continue
            
            plane_normal, plane_center = result
            
            # Project vertex to plane
            projected = project_to_plane(positions[vi], plane_normal, plane_center)
            
            # Blend based on taubin_lambda (shrinking)
            new_positions[vi] = positions[vi] + (projected - positions[vi]) * taubin_lambda
        
        positions = new_positions
        
        # === STEP 2: Inflate (expansion step) ===
        # Update bmesh temporarily to get accurate normals
        for i, vert in enumerate(bm.verts):
            vert.co = Vector(positions[i])
        bm.normal_update()
        
        # Get updated vertex normals
        vert_normals = get_vertex_normals(bm, num_verts)
        
        # Calculate Laplacian (average neighbor position - current position)
        inflate_positions = positions.copy()
        for vi in range(num_verts):
            neighbors = vert_neighbors[vi]
            if len(neighbors) < 1:
                continue
            
            # Compute Laplacian displacement
            neighbor_avg = np.mean(positions[neighbors], axis=0)
            laplacian = neighbor_avg - positions[vi]
            
            # Apply inflation (negative = outward movement)
            inflate_positions[vi] = positions[vi] + laplacian * taubin_mu
        
        positions = inflate_positions
    
    # === FINAL VOLUME CORRECTION ===
    if keep_volume and original_volume > 1e-10:
        # Apply positions to calculate new volume
        for i, vert in enumerate(bm.verts):
            vert.co = Vector(positions[i])
        bm.normal_update()
        
        new_volume = compute_mesh_volume(bm)
        
        if new_volume > 1e-10:
            # Scale uniformly around center to restore original volume
            scale_factor = (original_volume / new_volume) ** (1.0 / 3.0)
            new_center = np.mean(positions, axis=0)
            
            # Scale positions around center
            positions = new_center + (positions - new_center) * scale_factor
            
            # Also shift to original center
            adjusted_center = np.mean(positions, axis=0)
            positions += (original_center - adjusted_center)
    
    # Apply final positions back to bmesh
    for i, vert in enumerate(bm.verts):
        vert.co = Vector(positions[i])
    
    # Update normals
    bm.normal_update()


def clay_polish_object(obj, strength=0.5, iterations=3, edge_threshold=30.0, keep_volume=True):
    """
    Apply Clay Polish to a Blender mesh object.
    """
    if obj.type != 'MESH':
        return False
    
    # Create bmesh from object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # Apply polish
    clay_polish_mesh(bm, strength, iterations, edge_threshold, keep_volume)
    
    # Write back to mesh
    bm.to_mesh(obj.data)
    bm.free()
    
    # Update mesh
    obj.data.update()
    
    return True
