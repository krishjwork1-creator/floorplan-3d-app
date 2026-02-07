import cv2
import numpy as np
import trimesh
import math

def create_segment(p1, p2, height, thickness=12, color=[240, 240, 240, 255]):
    """
    Creates a simple 3D box connecting two points.
    Used for both Walls and Door Headers.
    """
    # 1. Calculate length and angle
    dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    
    # Ignore tiny segments (noise)
    if dist < 2: 
        return None
        
    # 2. Create the Box
    # Size: [Length, Thickness, Height]
    box = trimesh.creation.box(extents=[dist, thickness, height])
    
    # 3. Position it
    midpoint = (p1 + p2) / 2
    # Z-position: Center of the box is at height/2
    # If it's a header (floating), we'll adjust Z later
    
    vec = p2 - p1
    angle = np.arctan2(vec[1], vec[0])
    
    # 4. Apply Transforms (Rotate then Move)
    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], height/2])
    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    
    box.apply_transform(transform @ rotate)
    box.visual.face_colors = color
    return box

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # Invert: Walls = White
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean Noise
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Skeletonize: Thin the walls to single lines so we can trace them easily
    # This makes the "Lego" placement much more accurate
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Find Contours of these thin lines
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # Add Floor (Safety)
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 3.0       
    door_height = 2.2       
    header_height = wall_height - door_height 
    
    # We collect all endpoints to find doors later
    all_points = []

    # --- A. BUILD WALLS (LEGO STYLE) ---
    for cnt in contours:
        # Simplify line
        epsilon = 0.005 * cv2.arcLength(cnt, False) # False = Open curve
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        
        points = approx.squeeze()
        if len(points.shape) < 2: continue # Skip single points

        # Iterate through points and build segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            all_points.append(p1)
            all_points.append(p2)
            
            # Create Wall Segment
            wall = create_segment(p1, p2, wall_height)
            if wall:
                scene.add_geometry(wall)

    # --- B. DETECT DOORS ---
    # Convert list to numpy for fast distance check
    if len(all_points) > 2:
        pts = np.array(all_points)
        
        # Check every 10th point to save time (Optimization)
        for i in range(0, len(pts), 2):
            p1 = pts[i]
            
            # Look for partners
            for j in range(i + 1, len(pts), 2):
                p2 = pts[j]
                
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                
                # Door width: 20px to 90px
                if 25 < dist < 90:
                    # Create Header
                    header = create_segment(p1, p2, header_height, thickness=12, color=[200, 200, 200, 255])
                    
                    if header:
                        # Move it UP to sit above the door
                        header.apply_translation([0, 0, door_height])
                        scene.add_geometry(header)

    # 3. Export
    scene.export(output_path)
    print(f"✅ 3D Model generated: {output_path}")