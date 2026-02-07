import cv2
import numpy as np
import trimesh
import math

def create_wall_mesh(p1, p2, height, thickness=12):
    """
    Manually calculates vertices and faces for a wall segment.
    Returns: (vertices, faces)
    """
    # 1. Vector math to find corners
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx*dx + dy*dy)
    
    if length < 1: return None, None

    # Calculate perpendicular vector for thickness
    # (Normalize direction * thickness/2)
    nx = -dy / length * (thickness / 2)
    ny = dx / length * (thickness / 2)

    # 2. Define the 8 Corners (Vertices)
    # v0-v3: Bottom corners (z=0)
    v0 = [p1[0] + nx, p1[1] + ny, 0]
    v1 = [p1[0] - nx, p1[1] - ny, 0]
    v2 = [p2[0] - nx, p2[1] - ny, 0]
    v3 = [p2[0] + nx, p2[1] + ny, 0]

    # v4-v7: Top corners (z=height)
    v4 = [p1[0] + nx, p1[1] + ny, height]
    v5 = [p1[0] - nx, p1[1] - ny, height]
    v6 = [p2[0] - nx, p2[1] - ny, height]
    v7 = [p2[0] + nx, p2[1] + ny, height]

    vertices = np.array([v0, v1, v2, v3, v4, v5, v6, v7])

    # 3. Define the 12 Triangles (Faces)
    # Each face connects 3 vertex indices
    faces = np.array([
        # Bottom
        [0, 2, 1], [0, 3, 2],
        # Top
        [4, 5, 6], [4, 6, 7],
        # Front
        [0, 1, 5], [0, 5, 4],
        # Right
        [1, 2, 6], [1, 6, 5],
        # Back
        [2, 3, 7], [2, 7, 6],
        # Left
        [3, 0, 4], [3, 4, 7]
    ])

    return vertices, faces

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load & Preprocess
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Skeletonize (Thin lines)
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Contours
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Master lists for the entire building
    all_vertices = []
    all_faces = []
    vertex_offset = 0

    wall_height = 50.0 
    
    # 2. Build Walls (Manual Math)
    for cnt in contours:
        epsilon = 0.005 * cv2.arcLength(cnt, False)
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        points = approx.squeeze()
        
        if len(points.shape) < 2: continue

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            
            # Get data for one wall segment
            verts, faces = create_wall_mesh(p1, p2, wall_height)
            
            if verts is not None:
                # Add to master list
                all_vertices.append(verts)
                # Offset faces indices so they point to the new vertices
                all_faces.append(faces + vertex_offset)
                vertex_offset += 8

    # 3. Create Single Mesh
    # Combine all walls into one big object
    if all_vertices:
        combined_vertices = np.vstack(all_vertices)
        combined_faces = np.vstack(all_faces)
        
        # Create mesh directly from data (Bypasses creation logic)
        mesh = trimesh.Trimesh(vertices=combined_vertices, faces=combined_faces)
        mesh.visual.face_colors = [240, 240, 240, 255]
        
        # Create Scene
        scene = trimesh.Scene(mesh)
        
        # Add Floor
        h, w = img.shape
        floor = trimesh.creation.box(extents=[w, h, 1])
        floor.apply_translation([w/2, h/2, -0.5])
        floor.visual.face_colors = [50, 50, 50, 255]
        scene.add_geometry(floor)
        
        # Export GLB
        scene.export(output_path, file_type='glb')
        print(f"✅ 3D Model generated: {output_path}")
    else:
        # Fallback if no walls found (saves empty floor)
        print("⚠️ No walls found, generating empty floor.")
        h, w = img.shape
        floor = trimesh.creation.box(extents=[w, h, 1])
        scene = trimesh.Scene(floor)
        scene.export(output_path, file_type='glb')