import cv2
import numpy as np
import trimesh
import mapbox_earcut
from shapely.geometry import Polygon
import math

# --- HELPER: MANUAL EXTRUSION (Robust) ---
def create_wall_mesh(polygon_points, height):
    # 1. CLEAN DATA (The Critical Fix)
    # mapbox_earcut is picky. Data MUST be float32 and contiguous in memory.
    points_2d = np.ascontiguousarray(polygon_points, dtype=np.float32)
    flat_points = points_2d.flatten()
    
    # 2. Triangulate
    try:
        # returns indices of triangles: [0, 1, 2, 0, 2, 3...]
        triangle_indices = mapbox_earcut.triangulate_float32(flat_points, None, 2)
        top_faces = triangle_indices.reshape(-1, 3)
    except Exception as e:
        print(f"⚠️ Triangulation failed for a wall segment: {e}")
        return None 

    # 3. Create 3D Vertices
    n_points = len(points_2d)
    # Bottom (z=0) and Top (z=height)
    bottom_verts = np.column_stack((points_2d, np.zeros(n_points)))
    top_verts = np.column_stack((points_2d, np.full(n_points, height)))
    vertices = np.vstack((bottom_verts, top_verts))
    
    # 4. Create Faces
    # Bottom faces (flipped)
    bottom_faces = np.fliplr(top_faces) 
    # Top faces (offset by n_points)
    top_faces_offset = top_faces + n_points
    
    # Side Faces (Quads -> 2 Triangles each)
    side_faces = []
    for i in range(n_points):
        next_i = (i + 1) % n_points
        # Triangle 1
        side_faces.append([i, next_i, next_i + n_points])
        # Triangle 2
        side_faces.append([i, next_i + n_points, i + n_points])
        
    side_faces = np.array(side_faces)
    all_faces = np.vstack((bottom_faces, top_faces_offset, side_faces))
    
    return trimesh.Trimesh(vertices=vertices, faces=all_faces)

# --- MAIN PROCESS ---
def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load and Preprocess
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # Invert: Walls should be white (255), Background black (0)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean up noise
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 2. Extract Wall Contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Fn DEBUG: Found {len(contours)} potential walls")

    scene = trimesh.Scene()
    
    # --- SAFETY FLOOR (Prevents 'Empty Scene' Crash) ---
    # Adds a thin dark gray plate at z=-0.1 so there's always *something* to export
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 0.1])
    floor.apply_translation([w/2, h/2, -0.05]) # Center it
    floor.visual.face_colors = [50, 50, 50, 255] # Dark Gray
    scene.add_geometry(floor)

    wall_height = 3.0       
    door_height = 2.2       
    header_height = wall_height - door_height 

    wall_endpoints = []
    
    # --- A. BUILD MAIN WALLS ---
    for i, cnt in enumerate(contours):
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        if len(approx) >= 3:
            points = approx.squeeze()
            
            # Use robust manual extruder
            wall_mesh = create_wall_mesh(points, wall_height)
            
            if wall_mesh is not None:
                wall_mesh.visual.face_colors = [240, 240, 240, 255]
                scene.add_geometry(wall_mesh)
                
                # Save points for door detection
                for p in points:
                    wall_endpoints.append(p)
            else:
                print(f"⚠️ Could not build mesh for contour {i}")

    # --- B. DETECT DOORS ---
    if len(wall_endpoints) > 2:
        points_array = np.array(wall_endpoints)
        # Naive distance check (Fast & Lite)
        for i in range(len(points_array)):
            for j in range(i + 1, len(points_array)):
                p1 = points_array[i]
                p2 = points_array[j]
                
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

                if 25 < dist < 90:
                    vec = p2 - p1
                    angle = np.arctan2(vec[1], vec[0])
                    
                    header = trimesh.creation.box(extents=[dist, 10, header_height])
                    midpoint = (p1 + p2) / 2
                    z_pos = door_height + (header_height / 2.0)
                    
                    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], z_pos])
                    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                    
                    header.apply_transform(transform @ rotate)
                    header.visual.face_colors = [200, 200, 200, 255] 
                    scene.add_geometry(header)

    # 3. Export
    scene.export(output_path)
    print(f"✅ 3D Model generated: {output_path}")