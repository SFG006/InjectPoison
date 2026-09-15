from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import Response
from engine.perturbation import PoisonEngine
from api.auth import verify_api_key

app = FastAPI(
    title="InjectPoison API",
    description="Data poisoning API to protect images from unauthorized AI scrapers.",
    version="1.0.0"
)

# Initialize the black box engine once at server startup
# This loads the model into RAM/VRAM so requests process fast
poison_engine = PoisonEngine()

@app.get("/health")
def heath_check():
    """Simple health check endpoint for monitoring."""
    return {
        "status": "active",
        "service": "InjectPoison"
    }

@app.post("/v1/inject", response_class=Response)
async def inject_noise(
        file: UploadFile= File(...),
        api_key: str = Depends(verify_api_key)):
    """
        Accepts an image, applies adversarial noise in RAM, and returns the protected file.
    """

    # 1. Validate file extension
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Uploaded file must be an image (JPEG, PNG, etc.)."
        )

    # 2. Read the raw uploaded bytes into RAM
    input_bytes = await file.read()

    try:
        # 3. Pass through the black box engine
        output_bytes = poison_engine.inject(input_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Engine failure during injection: {str(e)}"
        )

    # 4. Return the protected image directly
    return Response(
        content=output_bytes,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"attachment; filename=poisoned_{file.filename}"
        }
    )
