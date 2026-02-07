import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString
import scipy.spatial # Essential for triangulation

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not load image. Check path.")

    # 2. Aggressive Pre-processing (The Fix)
    # Invert: Black walls become White (255), White background becomes Black (0)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Dilate: Thicken the white lines to close gaps and make walls solid
    # This is crucial for "sketchy" or thin-line floorplans
    kernel = np.ones((5,5), np.uint8)
    binary = cv2.dilate(binary, kernel, iterations=2)
    
    # Erode: Shrink back slightly to regain the approximate original shape, 
    # but keep the connections made by dilation.
    binary = cv2.erode(binary, kernel, iterations=1) 
    
    # 3. Extract Contours (External = Outer boundaries of walls)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # 4. Create Floor (Dark Gray Base)
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 2])
    floor.apply_translation([w/2, h/2, -1.0])
    floor.visual.face_colors = [40, 40, 40, 255] # Darker gray for contrast
    scene.add_geometry(floor)

    wall_height = 60.0 
    
    print(f"Fn DEBUG: Found {len(contours)} potential wall segments.")
    
    # 5. Build Walls
    for cnt in contours:
        # Simplify contour to reduce vertex count (Optimization)
        # Lower epsilon (0.002) = More detailed walls
        epsilon = 0.002 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # We need at least 3 points to make a closed shape
        if len(approx) >= 3:
            points = approx.squeeze()
            
            try:
                # Create a Shapely Polygon
                poly = Polygon(points)
                
                # Filter out tiny noise (area < 100 pixels)
                # Valid logic: Is it a valid polygon? Is it big enough to be a room/wall?
                if poly.is_valid and poly.area > 200:
                    # Extrude
                    wall_mesh = trimesh.creation.extrude_polygon(poly, height=wall_height)
                    wall_mesh.visual.face_colors = [240, 240, 240, 255] # White walls
                    scene.add_geometry(wall_mesh)
            except Exception as e:
                print(f"Skipping invalid shape: {e}")

    # 6. Export as GLB
    # We strip the process to ensure compatibility
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")