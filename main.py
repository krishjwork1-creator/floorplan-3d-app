import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from engine import process_image_to_3d

# ### NEW 1: Add these imports at the top
import razorpay
from pydantic import BaseModel
# -------------------------------------

# --- CONFIGURATION ---
SUPABASE_URL = "https://lebfznhghxhddkmealtm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlYmZ6bmhnaHhoZGRrbWVhbHRtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAwMjAyNDksImV4cCI6MjA4NTU5NjI0OX0.WFzxe1FRbmL2FaUqjD3yWKuzX6E-Es5u9rw4UCO7y3o"

# ### NEW 2: Add Razorpay Configuration here
RAZORPAY_KEY_ID = "rzp_live_SBaCxRDBNkWaSr"
RAZORPAY_KEY_SECRET = "PcC2Bd02yCeNsljIN8Lb13G6"

# Initialize Razorpay Client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
# ------------------------------------------

# Initialize Supabase Client
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

# ... (Your existing /convert endpoint stays exactly the same) ...
@app.post("/convert")
async def convert_floorplan(file: UploadFile = File(...)):
    try:
        clean_filename = file.filename.replace(" ", "_")
        input_path = f"temp/{clean_filename}"
        glb_filename = f"model_{clean_filename.split('.')[0]}.glb"
        output_path = f"temp/{glb_filename}"

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        process_image_to_3d(input_path, output_path)

        with open(output_path, "rb") as f:
            supabase.storage.from_("floorplans").upload(
                path=glb_filename,
                file=f,
                file_options={"content-type": "model/gltf-binary", "upsert": "true"}
            )

        project_url = SUPABASE_URL
        public_url = f"{project_url}/storage/v1/object/public/floorplans/{glb_filename}"

        os.remove(input_path)
        os.remove(output_path)

        return JSONResponse(content={"url": public_url})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ### NEW 3: Add this new endpoint at the very bottom
class OrderRequest(BaseModel):
    amount: int # Amount in paise (100 paise = 1 Rupee)

@app.post("/create-order")
async def create_order(request: OrderRequest):
    try:
        data = {
            "amount": request.amount,
            "currency": "INR",
            "receipt": "order_rcptid_11",
            "payment_capture": 1 # Auto-capture payment
        }
        order = client.order.create(data=data)
        return JSONResponse(content=order)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ----------------------------------------------------