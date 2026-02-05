import cv2
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from shapely.geometry import Polygon # <--- NEW IMPORT

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
            
            # FIX: Create a Shapely Polygon directly
            # This forces the shape to be closed and valid for extrusion
            poly_obj = Polygon(points)
            
            # Extrude the valid polygon
            wall_mesh = trimesh.creation.extrude_polygon(poly_obj, height=wall_height)
            wall_mesh.visual.face_colors = [240, 240, 240, 255]
            scene.add_geometry(wall_mesh)

            # Collect endpoints for door detection
            for p in points:
                wall_endpoints.append(p)

    # --- B. DETECT DOORS (THE BRIDGE) ---
    if len(wall_endpoints) > 2:
        points_array = np.array(wall_endpoints)
        tree = cKDTree(points_array)
        
        # Check pairs within 80px distance
        pairs = tree.query_pairs(r=80) 
        
        for (i, j) in pairs:
            p1 = points_array[i]
            p2 = points_array[j]
            dist = np.linalg.norm(p1 - p2)

            if dist > 25: 
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