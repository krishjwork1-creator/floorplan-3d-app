# ==========================================
# 🛑 SYSTEM OVERRIDE: FAKE SCIPY 🛑
# This block runs before anything else.
# It tricks trimesh into thinking scipy exists.
# ==========================================
import sys
from unittest.mock import MagicMock
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.spatial'] = MagicMock()
sys.modules['scipy.spatial.transform'] = MagicMock()
# ==========================================

import cv2
import numpy as np
import trimesh
import math

def create_segment(p1, p2, height, thickness=12, color=[240, 240, 240, 255]):
    """
    Creates a simple 3D box connecting two points.
    Uses pure numpy math to avoid library crashes.
    """
    # 1. Calculate length and angle
    dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    
    if dist < 2: return None # Skip noise
        
    # 2. Create Box
    # This might trigger a scipy check, but our Fake Scipy handles it.
    box = trimesh.creation.box(extents=[dist, thickness, height])
    
    # 3. Position and Rotate
    midpoint = (p1 + p2) / 2
    vec = p2 - p1
    angle = np.arctan2(vec[1], vec[0])
    
    # Standard 3D transformation matrix
    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], height/2])
    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    
    box.apply_transform(transform @ rotate)
    box.visual.face_colors = color
    return box

def process_image_to_3d(image_path, output_path):
    print(f"Fn DEBUG: Processing {image_path}")
    
    # 1. Load Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # Clean Noise
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Skeletonize: Thin lines for accuracy
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Find Contours
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # Add Floor (Safety)
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 3.0       
    header_height = 0.8 # Size of the bit above the door
    door_height = 2.2
    
    all_points = []

    # --- A. BUILD WALLS ---
    for cnt in contours:
        epsilon = 0.005 * cv2.arcLength(cnt, False)
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        points = approx.squeeze()
        
        if len(points.shape) < 2: continue

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            all_points.append(p1)
            all_points.append(p2)
            
            wall = create_segment(p1, p2, wall_height)
            if wall: scene.add_geometry(wall)

    # --- B. DETECT DOORS ---
    if len(all_points) > 2:
        pts = np.array(all_points)
        # Check subset of points to save CPU
        for i in range(0, len(pts), 2):
            if i > 500: break 
            for j in range(i + 1, len(pts), 2):
                p1 = pts[i]
                p2 = pts[j]
                
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                
                # If gap is door-sized (25px - 90px)
                if 25 < dist < 90:
                    header = create_segment(p1, p2, header_height, thickness=12, color=[200, 200, 200, 255])
                    if header:
                        header.apply_translation([0, 0, door_height])
                        scene.add_geometry(header)

    scene.export(output_path)
    print(f"✅ 3D Model generated: {output_path}")