# ==========================================
# 🛡️ SYSTEM OVERRIDE: SCIPY MOCK 🛡️
# This block runs before trimesh loads.
# It creates a fake package structure so trimesh 
# (and the server) never crash looking for scipy.
# ==========================================
import sys
import types
from unittest.mock import MagicMock

# 1. Create the main fake module
fake_scipy = types.ModuleType("scipy")
sys.modules["scipy"] = fake_scipy

# 2. Create fake submodules (Fixes "scipy is not a package" error)
fake_sparse = types.ModuleType("scipy.sparse")
sys.modules["scipy.sparse"] = fake_sparse
fake_scipy.sparse = fake_sparse

fake_spatial = types.ModuleType("scipy.spatial")
sys.modules["scipy.spatial"] = fake_spatial
fake_scipy.spatial = fake_spatial

# 3. Add MagicMocks for specific functions
fake_spatial.cKDTree = MagicMock()
# ==========================================

import cv2
import numpy as np
import trimesh
import math

def create_wall_segment(p1, p2, height, thickness=12):
    """
    Creates a simple 3D rectangular block (wall) between two points.
    """
    # 1. Calculate length
    dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    if dist < 2: return None # Skip tiny noise
        
    # 2. Create Box
    # This is safe and doesn't require advanced math libraries
    try:
        box = trimesh.creation.box(extents=[dist, thickness, height])
    except Exception:
        return None
    
    # 3. Position and Rotate
    midpoint = (p1 + p2) / 2
    vec = p2 - p1
    angle = np.arctan2(vec[1], vec[0])
    
    # Move to position
    transform = trimesh.transformations.translation_matrix([midpoint[0], midpoint[1], height/2])
    # Rotate to align with the wall line
    rotate = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    
    box.apply_transform(transform @ rotate)
    
    # Color: Off-white for walls
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
    
    # Skeletonize (Thin lines for better tracing)
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, skeleton = cv2.threshold(dist_transform, 5, 255, cv2.THRESH_BINARY)
    skeleton = skeleton.astype(np.uint8)

    # Find Contours
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    scene = trimesh.Scene()
    
    # --- ADD FLOOR (Critical for Visuals) ---
    # We add a dark floor so the model isn't floating in void
    h, w = img.shape
    floor = trimesh.creation.box(extents=[w, h, 1])
    floor.apply_translation([w/2, h/2, -0.5])
    floor.visual.face_colors = [50, 50, 50, 255]
    scene.add_geometry(floor)

    wall_height = 50.0 # Standard wall height
    
    # --- BUILD WALLS ---
    for cnt in contours:
        # Simplify the curve
        epsilon = 0.005 * cv2.arcLength(cnt, False)
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        points = approx.squeeze()
        
        # Need at least 2 points to make a wall
        if len(points.shape) < 2: continue

        # Connect every point to the next point
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            
            wall = create_wall_segment(p1, p2, wall_height)
            if wall:
                scene.add_geometry(wall)

    # --- EXPORT ---
    # We force .glb format because that's what your frontend viewer expects.
    # This prevents the "Black Screen" issue.
    scene.export(output_path, file_type='glb')
    print(f"✅ 3D Model generated: {output_path}")