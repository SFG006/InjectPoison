import os
from celery import Celery
from engine.perturbation import PoisonEngine

# 1. Connect Celery to your local Docker Redis container
celery_app = Celery(
    "poison_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

# 2. Load the heavy PyTorch model into RAM *outside* the main API
poison_engine = PoisonEngine()

@celery_app.task(name="process_image_task")
def process_image(input_filepath: str , output_filepath: str):
    """
    Reads the saved file, runs the PyTorch math, and saves the poisoned result.
    """
    try:
        # Read the raw bytes from disk
        with open(input_filepath,"rb") as f:
            input_bytes = f.read()

        # Execute the black box math
        output_bytes = poison_engine.inject(input_bytes)

        # Save the protected image to the output directory
        with open(output_filepath, "wb") as f:
            f.write(output_bytes)

        return {
            "status": "success",
            "file": output_filepath
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }