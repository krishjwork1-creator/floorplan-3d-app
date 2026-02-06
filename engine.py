import cv2
import numpy as np
import trimesh
import mapbox_earcut
from shapely.geometry import Polygon
import math

# --- HELPER: MANUAL EXTRUSION (Bypasses Scipy) ---
def create_wall_mesh(polygon_points, height):
    """
    Manually builds a 3D wall from 2D points using mapbox_earcut.
    This avoids trimesh.creation.extrude_polygon's dependency on scipy.
    """
    # 1. Prepare data for Earcut (Triangulate the floor)
    # Earcut expects a flat array of coordinates: [x0, y0, x1, y1, ...]
    points_2d = polygon_points.astype(np.float32)
    flat_points = points_2d.flatten()
    
    # Run triangulation (returns indices of triangles: [0, 1, 2, 0, 2, 3...])
    # 2nd arg is holes (None), 3rd is dimensions (2)
    try:
        triangle_indices = mapbox_earcut.triangulate_float32(flat_points, None, 2)
        top_faces = triangle_indices.reshape(-1, 3)
    except:
        return None # Skip if triangulation fails

    # 2. Create 3D Vertices
    # Bottom vertices (z=0)
    n_points = len(points_2d)
    bottom_verts = np.column_stack((points_2d, np.zeros(n_points)))
    # Top vertices (z=height)
    top_verts = np.column_stack((points_2d, np.full(n_points, height)))
    
    # Combine all vertices: [Bottom 0...N, Top 0...N]
    vertices = np.vstack((bottom_verts, top_verts))
    
    # 3. Create Faces
    # A. Top and Bottom faces
    # Bottom faces need to be flipped to face down
    bottom_faces = np.fliplr(top_faces) 
    # Top faces need to be offset by n_points (since they use the 2nd half of vertices)
    top_faces_offset = top_faces + n_points
    
    # B. Side Faces (The Walls)
    # We connect Point I (bottom) to I+1 (bottom) to I+1 (top) to I (top)
    side_faces = []
    for i in range(n_points):
        next_i = (i + 1) % n_points # Wrap around to 0 at the end
        
        # Two triangles make a quad (the wall segment)
        # Triangle 1: Bottom-Current -> Bottom-Next -> Top-Next
        side_faces.append([i, next_i, next_i + n_points])
        # Triangle 2: Bottom-Current -> Top-Next -> Top-Current
        side_faces.append([i, next_i + n_points, i + n_points])
        
    side_faces = np.array(side_faces)
    
    # Combine all faces
    all_faces = np.vstack((bottom_faces, top_faces_offset, side_faces))
    
    # 4. Create Mesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=all_faces)
    return mesh

# --- MAIN PROCESS ---
def process_image_to_3d(image_path, output_path):
    # 1. Load and Preprocess
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 2. Extract Wall Contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    wall_height = 3.0       
    door_height = 2.2       
    header_height = wall_height - door_height 

    wall_endpoints = []
    
    # --- A. BUILD MAIN WALLS ---
    for cnt in contours:
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        if len(approx) >= 3:
            points = approx.squeeze()
            
            # Use our custom manual extruder
            wall_mesh = create_wall_mesh(points, wall_height)
            
            if wall_mesh is not None:
                wall_mesh.visual.face_colors = [240, 240, 240, 255]
                scene.add_geometry(wall_mesh)

                for p in points:
                    wall_endpoints.append(p)

    # --- B. DETECT DOORS (LITE MATH) ---
    if len(wall_endpoints) > 2:
        points_array = np.array(wall_endpoints)
        
        for i in range(len(points_array)):
            for j in range(i + 1, len(points_array)):
                p1 = points_array[i]
                p2 = points_array[j]
                
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

                if 25 < dist < 90:
                    vec = p2 - p1
                    angle = np.arctan2(vec[1], vec[0])
                    
                    # Headers are simple boxes, they don't crash
                    header = trimesh.creation.box(extents=[dist, 10, header_height])
                    
                    midpoint = (p1 + p2) / 2
                    z_pos = door_height + (header_height / 2.0)
                    
                    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], z_pos])
                    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                    
                    header.apply_transform(transform @ rotate)
                    header.visual.face_colors = [200, 200, 200, 255] 
                    scene.add_geometry(header)

    scene.export(output_path)
    print(f"✅ 3D Model generated: {output_path}")