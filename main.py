import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from engine import process_image_to_3d
import razorpay
from pydantic import BaseModel
import scipy

# --- CONFIGURATION ---
SUPABASE_URL = "https://lebfznhghxhddkmealtm.supabase.co"

# ⚠️ SECURITY: Use your SERVICE_ROLE_KEY here (starts with eyJhbGciOiJIUzI1NiIs...)
# This key is required to bypass RLS and write to the database from the backend.
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlYmZ6bmhnaHhoZGRrbWVhbHRtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDAyMDI0OSwiZXhwIjoyMDg1NTk2MjQ5fQ.iwdSuFtiHql8zC3aGGmYwpnwEqd6ex31hsYrhtEsaFk"

# --- RAZORPAY CONFIG ---
RAZORPAY_KEY_ID = "rzp_live_SBaCxRDBNkWaSr"
RAZORPAY_KEY_SECRET = "PcC2Bd02yCeNsljIN8Lb13G6"

# Initialize Clients
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
os.makedirs("temp", exist_ok=True)

@app.get("/")
def home():
    return {"message": "Floorplan 3D API (Cloud Powered) is Running"}

@app.post("/convert")
async def convert_floorplan(
    file: UploadFile = File(...), 
    user_email: str = Form(None)
):
    # --- DEBUG LOGS ---
    print(f"🚀 DEBUG: Request Received!")
    print(f"📧 DEBUG: User Email: {user_email}")
    print(f"Fn DEBUG: Filename: {file.filename}")

    clean_filename = file.filename.replace(" ", "_")
    input_path = f"temp/{clean_filename}"
    glb_filename = f"model_{clean_filename.split('.')[0]}.glb"
    output_path = f"temp/{glb_filename}"

    try:
        # 1. Save File Locally
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Process Image (Engine)
        process_image_to_3d(input_path, output_path)

        # 3. Upload GLB to Supabase Storage
        with open(output_path, "rb") as f:
            print("☁️ DEBUG: Uploading to Supabase Storage...")
            supabase.storage.from_("floorplans").upload(
                path=glb_filename,
                file=f,
                file_options={"content-type": "model/gltf-binary", "upsert": "true"}
            )

        # 4. Construct Public URL
        # Note: Ensure your bucket "floorplans" is set to Public in Supabase dashboard
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/floorplans/{glb_filename}"
        print(f"🔗 DEBUG: Generated URL: {public_url}")

        # 5. SAVE TO DATABASE (Critical Step)
        if user_email and user_email != "null":
            print(f"💾 DEBUG: Saving to DB for {user_email}...")
            
            data = {
                "user_email": user_email,
                "project_name": clean_filename,
                "model_url": public_url
            }
            
            # Using service_role key allows us to bypass RLS here
            response = supabase.table("user_projects").insert(data).execute()
            print("✅ DEBUG: DB Save Success!", response)
        else:
            print("⚠️ DEBUG: No valid email provided, skipping DB save.")

        return JSONResponse(content={"url": public_url})

    except Exception as e:
        print(f"❌ ERROR: {e}")
        # Return the error details to frontend for easier debugging
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 6. Cleanup (Runs even if error occurs)
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        print("🧹 DEBUG: Temp files cleaned up.")

# --- PAYMENT ENDPOINT ---
class OrderRequest(BaseModel):
    amount: int

@app.post("/create-order")
async def create_order(request: OrderRequest):
    try:
        data = {
            "amount": request.amount,
            "currency": "INR",
            "receipt": "order_rcptid_11",
            "payment_capture": 1
        }
        order = client.order.create(data=data)
        return JSONResponse(content=order)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))