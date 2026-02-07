import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon
import scipy

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not load image. Check path.")

    # Threshold: Convert to binary (Black walls on White background assumed)
    # THRESH_BINARY_INV turns White(255) background to Black(0), and Black lines to White(255)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # 2. Pre-processing (CRITICAL FIX)
    # Use Dilation to thicken walls and close small gaps (doors/windows)
    # This ensures walls are detected as solid shapes rather than broken lines.
    kernel = np.ones((5,5), np.uint8)
    binary = cv2.dilate(binary, kernel, iterations=2)
    binary = cv2.erode(binary, kernel, iterations=1) # Erode back slightly to keep shape
    
    # 3. Extract Contours
    # RETR_EXTERNAL gets the outer boundaries of the thickened walls
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # Floor (Dark Gray) - Sized to image dimensions
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 2])
    floor.apply_translation([w/2, h/2, -1.0])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 60.0 # Increased slightly for better visual
    
    # 4. Build Walls
    print(f"Fn DEBUG: Found {len(contours)} potential wall segments.")
    
    for cnt in contours:
        # Simplify contour to reduce vertex count (Optimization)
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # We need at least 3 points to make a closed shape (triangle or more)
        if len(approx) >= 3:
            points = approx.squeeze()
            
            try:
                # Create a Shapely Polygon
                poly = Polygon(points)
                
                # Filter out tiny noise (area < 100 pixels)
                if poly.is_valid and poly.area > 100:
                    # Extrude
                    wall_mesh = trimesh.creation.extrude_polygon(poly, height=wall_height)
                    wall_mesh.visual.face_colors = [240, 240, 240, 255] # White walls
                    scene.add_geometry(wall_mesh)
            except Exception as e:
                print(f"Skipping invalid shape: {e}")

    # 5. Export as GLB
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")