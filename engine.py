import cv2
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def process_image_to_3d(image_path, output_path):
    # 1. Load and Preprocess
    # Read grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Invert if necessary (Plan should be black lines on white bg)
    # We want Walls = 255 (White), Background = 0 (Black) for processing
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Denoise (Remove small dots)
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 2. Extract Wall Contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    wall_height = 3.0       # Total wall height
    door_height = 2.2       # Height of the door opening
    header_height = wall_height - door_height # The bit above the door

    # Store all wall endpoints for "Door Detection"
    wall_endpoints = []
    
    # --- A. BUILD MAIN WALLS ---
    for cnt in contours:
        # Simplify contour to remove jagged edges
        epsilon = 0.005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # We need at least 3 points to make a 3D shape
        if len(approx) >= 3:
            # Squeeze to Nx2 array of points
            points = approx.squeeze()
            
            # Create the Wall Mesh (Floor to Ceiling)
            # We flip Y because images are Y-down, 3D is Y-up
            polygon = trimesh.creation.extrude_polygon(trimesh.load_path(points).polygons[0], height=wall_height)
            polygon.visual.face_colors = [240, 240, 240, 255] # Off-white walls
            scene.add_geometry(polygon)

            # Collect endpoints (approximation: use all points for now)
            # In a pro version, we'd skeletonize the image to find true tips.
            # For this MVP, we use the contour points as "potential connection spots"
            for p in points:
                wall_endpoints.append(p)

    # --- B. DETECT DOORS (THE BRIDGE) ---
    # We look for gaps between wall segments that are "Door Sized" (e.g., 20-80 pixels)
    if len(wall_endpoints) > 2:
        points_array = np.array(wall_endpoints)
        
        # Use KDTree to find close points efficiently
        tree = cKDTree(points_array)
        
        # Query pairs within distance (20px to 80px)
        # Note: These values depend on image resolution. 
        # 50px is a guess for a standard door in a 1000x1000 image.
        pairs = tree.query_pairs(r=80) 
        
        for (i, j) in pairs:
            p1 = points_array[i]
            p2 = points_array[j]
            dist = np.linalg.norm(p1 - p2)

            # Filter: Don't connect points that are TOO close (cracks) or too far
            if dist > 25: 
                # Create the "Header" (The wall above the door)
                # We make a box connecting p1 and p2
                
                # Vector from p1 to p2
                vec = p2 - p1
                angle = np.arctan2(vec[1], vec[0])
                
                # Create a box of size (distance, thickness, header_height)
                # Thickness is hardcoded to 10px or derived
                thickness = 10 
                header = trimesh.creation.box(extents=[dist, thickness, header_height])
                
                # Position the header
                midpoint = (p1 + p2) / 2
                # Z position: It sits on top of the door (2.2m + half its own height)
                z_pos = door_height + (header_height / 2.0)
                
                # Matrix magic to rotate and place the box
                transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], z_pos])
                rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                
                header.apply_transform(transform @ rotate)
                header.visual.face_colors = [200, 200, 200, 255] # Slightly darker for contrast
                scene.add_geometry(header)

    # 3. Export
    scene.export(output_path)
    print(f"✅ 3D Model generated with smart headers: {output_path}")