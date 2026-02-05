import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from engine import process_image_to_3d
import razorpay
from pydantic import BaseModel

# --- CONFIGURATION ---
SUPABASE_URL = "https://lebfznhghxhddkmealtm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlYmZ6bmhnaHhoZGRrbWVhbHRtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDAyMDI0OSwiZXhwIjoyMDg1NTk2MjQ5fQ.iwdSuFtiHql8zC3aGGmYwpnwEqd6ex31hsYrhtEsaFk" # Must be the Service Role (Admin) Key

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

os.makedirs("temp", exist_ok=True)

@app.get("/")
def home():
    return {"message": "Floorplan 3D API (Cloud Powered)"}

@app.post("/convert")
async def convert_floorplan(
    file: UploadFile = File(...), 
    user_email: str = Form(None)
):
    # --- DEBUG LOGS ---
    print(f"🚀 DEBUG: Request Received!")
    print(f"📧 DEBUG: User Email: {user_email}")
    print(f"Fn DEBUG: Filename: {file.filename}")
    # ------------------

    try:
        # 1. Save and Process File
        clean_filename = file.filename.replace(" ", "_")
        input_path = f"temp/{clean_filename}"
        glb_filename = f"model_{clean_filename.split('.')[0]}.glb"
        output_path = f"temp/{glb_filename}"

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        process_image_to_3d(input_path, output_path)

        # 2. Upload GLB to Storage
        with open(output_path, "rb") as f:
            supabase.storage.from_("floorplans").upload(
                path=glb_filename,
                file=f,
                file_options={"content-type": "model/gltf-binary", "upsert": "true"}
            )

        # 3. Get Public URL
        project_url = SUPABASE_URL
        public_url = f"{project_url}/storage/v1/object/public/floorplans/{glb_filename}"

        # 4. SAVE TO DATABASE
        if user_email:
            print(f"💾 DEBUG: Saving to DB for {user_email}...")
            response = supabase.table("user_projects").insert({
                "user_email": user_email,
                "project_name": clean_filename,
                "model_url": public_url
            }).execute()
            print("✅ DEBUG: DB Save Success!")
        else:
            print("⚠️ DEBUG: No email provided, skipping DB save.")

        # 5. Cleanup
        os.remove(input_path)
        os.remove(output_path)

        return JSONResponse(content={"url": public_url})

    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
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