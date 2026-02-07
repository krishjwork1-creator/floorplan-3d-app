import cv2
import numpy as np
import trimesh
import math

def create_wall_segment(p1, p2, height, thickness=12):
    """
    Creates a 3D wall segment between two points using a simple Box.
    This looks exactly like an extruded wall but works without scipy.
    """
    # 1. Calculate distance between points
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.sqrt(dx*dx + dy*dy)
    
    if dist < 2: return None # Skip noise
        
    # 2. Create the Wall (Box)
    # extents = [length, thickness, height]
    box = trimesh.creation.box(extents=[dist, thickness, height])
    
    # 3. Position and Rotate the Wall
    # Move to the midpoint between p1 and p2
    midpoint = (p1 + p2) / 2
    
    # Calculate angle to rotate the box
    angle = np.arctan2(dy, dx)
    
    # Create transformation matrix (Translate + Rotate)
    # Z-position is height/2 because boxes are created at the origin
    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], height/2])
    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    
    # Apply transform
    box.apply_transform(transform @ rotate)
    
    # Set Color (Light Gray/Off-White)
    box.visual.face_colors = [240, 240, 240, 255]
    return box

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Invert: We want Walls to be White (255)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean up small noise dots
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Skeletonize: Thin lines to 1 pixel wide for clean tracing
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Find Contours (The lines to draw)
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # --- ADD FLOOR ---
    # A simple floor ensures the viewer has a reference point
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255] # Dark Gray Floor
    scene.add_geometry(floor)

    # Wall Settings
    wall_height = 50.0 
    
    # --- BUILD WALLS ---
    for cnt in contours:
        # Simplify the contour to remove jagged edges
        epsilon = 0.005 * cv2.arcLength(cnt, False)
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        points = approx.squeeze()
        
        # We need at least 2 points to draw a line
        if len(points.shape) < 2: continue

        # Iterate through points and build segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            
            wall = create_wall_segment(p1, p2, wall_height)
            if wall:
                scene.add_geometry(wall)

    # --- EXPORT ---
    # Export as GLB (Binary) to ensure it works in your web viewer
    # (Fixes the blank screen issue caused by OBJ text files)
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")