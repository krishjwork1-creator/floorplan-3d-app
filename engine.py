import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon
# We don't need to import mapbox_earcut explicitly, 
# but installing it allows trimesh to find it.

def process_image_to_3d(image_path, output_path):
    print(f"--- Processing {image_path} ---")

    # 1. READ IMAGE
    img = cv2.imread(image_path, 0)
    
    if img is None:
        print("Error: Could not read image. Check the filename!")
        return

    # 2. PRE-PROCESSING
    # Blur slightly to merge small cracks
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    
    # Threshold (200 is the sensitivity, adjust if needed)
    _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)

    # 3. WALL DETECTION
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"Found {len(contours)} potential shapes.")

    meshes = []

    # 4. FILTERING & EXTRUSION
    for i, cnt in enumerate(contours):
        
        # Filter small noise
        if cv2.contourArea(cnt) < 500: 
            continue
            
        # Simplify shape
        epsilon = 0.01 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        points = approx.reshape(-1, 2)
        
        if len(points) >= 3:
            try:
                poly = Polygon(points)
                
                # --- THE FIX IS HERE ---
                # We explicitly tell it to use 'earcut' engine
                mesh = trimesh.creation.extrude_polygon(
                    poly, 
                    height=50,
                    engine='earcut'  # <--- THIS SOLVES YOUR ERROR
                )
                
                meshes.append(mesh)
                print(f" - Wall {i}: Extruded successfully.")
            except Exception as e:
                # If earcut fails, it might be a weird shape (self-intersecting)
                print(f" - Wall {i}: Skipped (Error: {e})")

    # 5. EXPORT
    if meshes:
        combined = trimesh.util.concatenate(meshes)
        combined.export(output_path)
        print(f"SUCCESS! 3D Model saved to: {output_path}")
    else:
        print("Failed: No walls were detected. Try a clearer image.")

if __name__ == "__main__":
    process_image_to_3d("sample.jpg", "output.glb")