import os
import uuid
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from api.auth import verify_api_key
from worker.tasks import process_image

app = FastAPI(
    title="InjectPoison API",
    description="Data poisoning API to protect images from unauthorized AI scrapers.",
    version="1.0.0"
)

# Setup temporary local storage for the queue to read/write from
os.makedirs("temp_uploads", exist_ok=True)
os.makedirs("temp_results", exist_ok=True)

@app.get("/health")
def heath_check():
    """Simple health check endpoint for monitoring."""
    return {
        "status": "active",
        "service": "InjectPoison"
    }

@app.post("/v1/inject")
async def inject_noise(
        file: UploadFile= File(...),
        api_key: str = Depends(verify_api_key)):
    """
        Accepts an image, drops it in the queue, and returns a Job ID instantly.
    """

    # 1. Validate file extension
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Uploaded file must be an image (JPEG, PNG, etc.)."
        )
    # Generate a unique ID for this specific upload
    job_id = str(uuid.uuid4())
    input_path = f"temp_uploads/{job_id}_{file.filename}"
    output_path = f"temp_results/poisoned_{job_id}_{file.filename}"

    # Save the file to disk instantly
    with open(input_path,"wb") as buffer:
        buffer.write(await file.read())

    # Dispatch the task to Redis (runs in the background)
    process_image.delay(input_path,output_path)

    # Return a 200 OK immediately, do not wait for PyTorch
    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Use GET /v1/status/{job_id} to retrieve the image."
    }

@app.get("/v1/status/{job_id}")
async def get_job_result(job_id: str, api_key: str = Depends(verify_api_key)):
    """Checks if the background worker has finished saving the result."""

    # Search the results folder for a file containing this job_id
    for filename in os.listdir("temp_results"):
        if job_id in filename:
            output_path = os.path.join("temp_results",filename)
            return FileResponse(
                path=output_path,
                media_type="image/jpeg",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

    # If the file isn't there yet, the background worker is still calculating
    return {
        "job_id": job_id,
        "status": "processing_or_not_found"
    }