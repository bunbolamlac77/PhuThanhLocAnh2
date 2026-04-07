import torch
import cv2
from transformers import AutoImageProcessor, AutoModel
from sklearn.cluster import DBSCAN
import numpy as np

class AIEngine:
    def __init__(self):
        # 1. Kích hoạt GPU trên Mac M1 (Metal Performance Shaders)
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"[AI Engine] Khởi tạo thành công. Đang chạy trên thiết bị: {self.device}")
        
        # 2. Khởi tạo DINOv2 (Dùng bản ViT-Small cho tốc độ cực nhanh, hoặc ViT-Large cho độ chính xác tuyệt đối)
        print("[AI Engine] Đang tải mô hình DINOv2...")
        self.processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
        self.dino_model = AutoModel.from_pretrained('facebook/dinov2-small').to(self.device).eval()
        
        # TODO: Khởi tạo YOLO-Pose và InsightFace tại đây trong tương lai

    def extract_scene_vector(self, image_path):
        """Trích xuất vector bối cảnh bằng DINOv2"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.dino_model(**inputs)
            
            # Lấy vector đại diện (CLS token)
            # DINOv2 small outputs hidden_states of size [batch, 257, 384]
            # [0][0] is the CLS token
            vector = outputs.last_hidden_state[0][0].cpu().numpy()
            return vector
        except Exception as e:
            print(f"Lỗi đọc ảnh {image_path}: {e}")
            return None

    def cluster_scenes(self, vectors, eps=0.5, min_samples=1):
        """Gom nhóm các ảnh có cùng bối cảnh bằng thuật toán DBSCAN"""
        if not vectors:
            return []
        
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(vectors)
        return clustering.labels_

    def mock_evaluate_image(self, image_path):
        """Hàm chấm điểm giả lập (Tạm thời dùng để test luồng trước khi ghép LIQE)"""
        import random
        # Tính điểm ngẫu nhiên để test giao diện lọc
        score = random.uniform(50.0, 99.9) 
        return score
