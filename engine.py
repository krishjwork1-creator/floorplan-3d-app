import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon
import scipy.spatial

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not load image. Check path.")

    # 2. "Canny" Edge Detection (The Heavy Artillery)
    # This finds edges regardless of lighting or color (black-on-white OR white-on-black)
    # 50, 150 are standard thresholds for structure detection
    edges = cv2.Canny(img, 50, 150)

    # 3. Thicken the Edges
    # We dilate the edges to turn thin lines into thick, solid "walls"
    kernel = np.ones((5,5), np.uint8)
    binary = cv2.dilate(edges, kernel, iterations=3)
    
    # Close any remaining small gaps
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # 4. Extract Contours
    # RETR_LIST: Gets ALL shapes, not just the outer ones (Handles internal rooms better)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # 5. Create Floor (Dark Gray)
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 2])
    floor.apply_translation([w/2, h/2, -1.0])
    floor.visual.face_colors = [40, 40, 40, 255]
    scene.add_geometry(floor)

    wall_height = 60.0 
    
    print(f"Fn DEBUG: Found {len(contours)} potential wall segments.")
    
    # Calculate total image area to filter out the "border" of the image itself
    image_area = h * w
    
    # 6. Build Walls
    for cnt in contours:
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        if len(approx) >= 3:
            points = approx.squeeze()
            try:
                poly = Polygon(points)
                
                # LOGIC UPDATE:
                # 1. Area > 100: Must be bigger than a dot
                # 2. Area < image_area * 0.9: Must NOT be the entire image border
                if poly.is_valid and poly.area > 100 and poly.area < (image_area * 0.90):
                    
                    wall_mesh = trimesh.creation.extrude_polygon(poly, height=wall_height)
                    wall_mesh.visual.face_colors = [240, 240, 240, 255]
                    scene.add_geometry(wall_mesh)
                    
            except Exception as e:
                # Silently skip invalid geometry
                pass

    # 7. Export
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")