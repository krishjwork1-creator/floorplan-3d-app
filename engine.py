import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean Noise
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 2. Extract Contours
    # We re-enable approximation to keep the model light
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # Floor (Dark Gray)
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 50.0
    
    # 3. Build Walls using Extrusion (The Original Way)
    for cnt in contours:
        # Simplify contour
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # We need 3 points to make a shape
        if len(approx) >= 3:
            points = approx.squeeze()
            
            try:
                # Create a Shapely Polygon
                # This is critical: Trimesh uses Shapely to triangulate 
                # instead of Scipy if it's available.
                poly = Polygon(points)
                
                if poly.is_valid and poly.area > 50:
                    # Extrude
                    wall_mesh = trimesh.creation.extrude_polygon(poly, height=wall_height)
                    wall_mesh.visual.face_colors = [240, 240, 240, 255]
                    scene.add_geometry(wall_mesh)
            except Exception as e:
                print(f"Skipping invalid shape: {e}")

    # 4. Export as GLB
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")