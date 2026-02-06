import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon
import math

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
            
            try:
                poly_obj = Polygon(points)
                
                if poly_obj.is_valid and poly_obj.area > 100:
                    wall_mesh = trimesh.creation.extrude_polygon(poly_obj, height=wall_height)
                    wall_mesh.visual.face_colors = [240, 240, 240, 255]
                    scene.add_geometry(wall_mesh)

                    for p in points:
                        wall_endpoints.append(p)
            except Exception as e:
                print(f"Skipping invalid shape: {e}")

    # --- B. DETECT DOORS (LITE MATH) ---
    if len(wall_endpoints) > 2:
        points_array = np.array(wall_endpoints)
        
        # Simple loop to find close points (No heavy libraries)
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

    scene.export(output_path)
    print(f"✅ 3D Model generated: {output_path}")