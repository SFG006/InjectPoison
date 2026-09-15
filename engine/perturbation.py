import io
import torch
import torchattacks
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

class PoisonEngine:
    def __init__(self, eps = 4/255, alpha=1/255 , steps=15):
        """
        Initializes the PGD attack engine.
        eps: The "Epsilon" budget. Maximum allowed pixel change (keeps noise invisible).
        alpha: Step size for each mathematical iteration.
        steps: Number of times the loop runs to maximize the AI's error.
        """

        # 1. Hardware setup (Uses GPU if available, otherwise CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 2. Load a 'Victim' Model
        # We use ResNet50 as our dummy target. If we poison against this,
        # the mathematical noise transfers incredibly well to other AI models.
        self.model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT).to(self.device)
        self.model.eval() # Freeze weights; we are altering the image, not training the model

        # 3. Configure the PGD Attack
        # This algorithm will actively try to force the AI to misclassify the image
        self.attack = torchattacks.PGD(self.model,eps=eps , alpha=alpha, steps=steps)

        # 4. Standard Vision Transforms
        # Converts the image into a mathematical matrix (Tensor) scaled between 0 and 1
        self.transfrom = transforms.Compose([
            transforms.ToTensor()
        ])

        # Converts the Tensor back into a viewable image
        self.to_pil = transforms.ToPILImage()

    def inject(self, image_bytes: bytes) -> bytes:
        """
        Accepts raw image bytes, applies adversarial noise, and returns protected image bytes.
        """
        # Open the image and convert to a PyTorch Tensor
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_tensor = self.transfrom(image).unsqueeze(0).to(self.device)

        # Get the model's actual prediction of the clean image
        with torch.no_grad():
            original_prediction = self.model(image_tensor).argmax(dim=1)

        # Apply the mathematical perturbation
        # (Pushing the pixels as far away from the original_prediction as possible)
        poisoned_tensor = self.attack(image_tensor,original_prediction)

        # Clamp ensures the mathematical noise doesn't create invalid/neon pixel colors
        poisoned_tensor = torch.clamp(poisoned_tensor, 0, 1)

        # Convert the poisoned tensor back to a standard JPEG image
        poisoned_image = self.to_pil(poisoned_tensor.squeeze(0).cpu())
        output_buffer = io.BytesIO()
        poisoned_image.save(output_buffer,format="JPEG", quality=100)

        return output_buffer.getvalue()


            