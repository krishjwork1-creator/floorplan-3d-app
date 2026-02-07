import cv2
import numpy as np
import trimesh
import math

def create_wall_segment(p1, p2, height, thickness=12):
    """
    Standard Trimesh Box Logic.
    """
    # 1. Calculate length
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.sqrt(dx*dx + dy*dy)
    
    if dist < 2: return None
        
    # 2. Create Box
    # This creates a box centered at the origin
    box = trimesh.creation.box(extents=[dist, thickness, height])
    
    # 3. Position and Rotate
    midpoint = (p1 + p2) / 2
    angle = np.arctan2(dy, dx)
    
    # Create transformation matrix
    # Move to midpoint
    # Z is height/2 because box starts centered at 0
    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], height/2])
    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    
    # Apply standard transform
    box.apply_transform(transform @ rotate)
    
    # Color: Off-white
    box.visual.face_colors = [240, 240, 240, 255]
    return box

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean Noise
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Skeletonize
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Find Contours
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # Add Floor
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 50.0 
    
    # --- BUILD WALLS ---
    for cnt in contours:
        epsilon = 0.005 * cv2.arcLength(cnt, False)
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        points = approx.squeeze()
        
        if len(points.shape) < 2: continue

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            
            wall = create_wall_segment(p1, p2, wall_height)
            if wall:
                scene.add_geometry(wall)

    # --- EXPORT ---
    # Standard GLB export
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")