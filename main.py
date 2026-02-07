from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from engine import process_image_to_3d

app = FastAPI()

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for processing
os.makedirs("temp", exist_ok=True)

@app.get("/")
def home():
    return {"message": "FloorPlan AI API is Running"}

@app.post("/convert")
async def convert_plan(file: UploadFile = File(...)):
    # 1. Generate unique filenames to prevent conflicts
    unique_id = str(uuid.uuid4())[:8]
    input_filename = f"temp/{unique_id}_input.jpg"
    output_filename = f"temp/{unique_id}_model.glb" # We explicitly want GLB
    
    try:
        # 2. Save the uploaded file
        with open(input_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Run the 3D Engine
        # This function must create the .glb file at output_filename
        process_image_to_3d(input_filename, output_filename)
        
        # 4. Return the file
        if not os.path.exists(output_filename):
            raise HTTPException(status_code=500, detail="Failed to generate 3D model")
            
        return FileResponse(
            output_filename, 
            media_type="model/gltf-binary", 
            filename="floorplan.glb"
        )
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup: Delete files after sending (optional, keeps server clean)
        # We wrap in try/except so cleanup errors don't fail the request
        try:
            if os.path.exists(input_filename): os.remove(input_filename)
            # We don't delete output immediately so FileResponse can read it
        except:
            pass