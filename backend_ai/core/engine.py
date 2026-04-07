import torch
import cv2
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
import os

class AIEngine:
    def __init__(self):
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        print(f"Using device: {self.device}")
        
        # Models will be loaded on demand (Lazy Loading)
        self.dinov2_processor = None
        self.dinov2_model = None
        self.yolo_model = None

    def load_dinov2(self):
        """Loads DINOv2 for feature extraction (High-quality aesthetic scoring)"""
        if self.dinov2_model is None:
            print("Loading DINOv2 model...")
            self.dinov2_processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
            self.dinov2_model = AutoModel.from_pretrained("facebook/dinov2-small").to(self.device).eval()

    def load_yolo_pose(self):
        """Loads YOLO-Pose for skeletal and pose analysis"""
        from ultralytics import YOLO
        if self.yolo_model is None:
            print("Loading YOLO-Pose...")
            self.yolo_model = YOLO('yolov8n-pose.pt').to(self.device)

    def load_face_analysis(self):
        """Loads InsightFace for eye and blink detection"""
        import insightface
        # Placeholder for InsightFace initialization
        # self.face_analyzer = insightface.app.FaceAnalysis(name='antelopev2', providers=['CoreMLExecutionProvider'])
        pass

    def get_sharpness(self, image_path: str) -> float:
        """Calculates sharpness using Laplacian variance (Fast, non-AI)"""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return 0.0
        return cv2.Laplacian(img, cv2.CV_64F).var()

    def extract_features(self, image_path: str):
        """Extracts deep features from an image using DINOv2 on MPS"""
        self.load_dinov2()
        image = Image.open(image_path).convert("RGB")
        inputs = self.dinov2_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.dinov2_model(**inputs)
            last_hidden_states = outputs.last_hidden_state
            # Mean pooling to get a fixed-length vector (feature embedding)
            features = last_hidden_states.mean(dim=1)
        return features.cpu().numpy()

# Global instance
ai_engine = AIEngine()
