import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse # Changed from FileResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from engine import process_image_to_3d

# --- CONFIGURATION ---
SUPABASE_URL = "https://lebfznhghxhddkmealtm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlYmZ6bmhnaHhoZGRrbWVhbHRtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDAyMDI0OSwiZXhwIjoyMDg1NTk2MjQ5fQ.iwdSuFtiHql8zC3aGGmYwpnwEqd6ex31hsYrhtEsaFk"

# Create Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("temp", exist_ok=True)

@app.get("/")
def home():
    return {"message": "Floorplan 3D API (Cloud Powered)"}

@app.post("/convert")
async def convert_floorplan(file: UploadFile = File(...)):
    try:
        # 1. Define filenames
        clean_filename = file.filename.replace(" ", "_")
        input_path = f"temp/{clean_filename}"
        glb_filename = f"model_{clean_filename.split('.')[0]}.glb"
        output_path = f"temp/{glb_filename}"

        # 2. Save input locally to process it
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Run the Engine
        process_image_to_3d(input_path, output_path)

        # 4. UPLOAD TO SUPABASE (The New Part)
        # We read the generated binary file
        with open(output_path, "rb") as f:
            # Upload to 'floorplans' bucket
            supabase.storage.from_("floorplans").upload(
                path=glb_filename,
                file=f,
                file_options={"content-type": "model/gltf-binary", "upsert": "true"}
            )

        # 5. Get the Public URL
        # This URL works anywhere on the internet
        project_url = SUPABASE_URL
        public_url = f"{project_url}/storage/v1/object/public/floorplans/{glb_filename}"

        # 6. Clean up (Delete local temp files)
        os.remove(input_path)
        os.remove(output_path)

        # Return the URL instead of the file blob
        return JSONResponse(content={"url": public_url})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))