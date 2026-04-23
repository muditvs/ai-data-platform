from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from app.services.data_service import process_data

router = APIRouter()

UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process the data
        result = process_data(file_path)
        
        return {"filename": file.filename, "message": "File uploaded and processed successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))