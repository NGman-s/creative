import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from services.vision_service import analyze_food_image

app = FastAPI(title="LifeLens API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_images"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

@app.get("/")
async def root():
    return {"message": "LifeLens API is running"}

@app.post("/api/v1/vision/analyze")
async def analyze_vision(
    file: UploadFile = File(...),
    user_context: str = Form(...)
):
    # Save uploaded file temporarily
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_DIR, f"{file_id}{ext}")

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Call Qwen-VL analysis
        analysis_result = await analyze_food_image(temp_path, user_context)

        return {
            "code": 200,
            "data": analysis_result,
            "trace_id": file_id
        }
    except Exception as e:
        return {
            "code": 500,
            "message": str(e),
            "trace_id": file_id
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
