import torch
import cv2
import numpy as np
from transformers import AutoImageProcessor, AutoModel
from sklearn.cluster import DBSCAN
from insightface.app import FaceAnalysis

class AIEngine:
    def __init__(self):
        # 1. Kích hoạt GPU trên Mac M1
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"[AI Engine] Đang chạy trên thiết bị: {self.device}")
        
        # 2. Khởi tạo DINOv2
        print("[AI Engine] Đang tải mô hình DINOv2 (Nhận diện bối cảnh)...")
        self.processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
        self.dino_model = AutoModel.from_pretrained('facebook/dinov2-small').to(self.device).eval()
        
        # 3. Khởi tạo InsightFace (Nhận diện & Đếm khuôn mặt)
        print("[AI Engine] Đang tải mô hình InsightFace (Nhận diện khuôn mặt)...")
        self.face_app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

    def analyze_image(self, image_path):
        """Trích xuất Vector bối cảnh, Đếm khuôn mặt, và Đo độ nét ảnh"""
        try:
            # Đọc ảnh an toàn với tiếng Việt
            image_data = np.fromfile(image_path, dtype=np.uint8)
            image_bgr = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            if image_bgr is None:
                return None, 0, 0.0

            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            
            # --- TÁC VỤ 1: TRÍCH XUẤT BỐI CẢNH ---
            inputs = self.processor(images=image_rgb, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.dino_model(**inputs)
            vector = outputs.last_hidden_state[0][0].cpu().numpy()
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm # Chuẩn hóa
                
            # --- TÁC VỤ 2: ĐẾM SỐ KHUÔN MẶT ---
            faces = self.face_app.get(image_bgr)
            face_count = len(faces)
            
            # --- TÁC VỤ 3: CHẤM ĐIỂM ĐỘ NÉT CƠ BẢN (Thay cho Random) ---
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            sharpness_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            return vector, face_count, sharpness_score
            
        except Exception as e:
            print(f"Lỗi đọc ảnh {image_path}: {e}")
            return None, 0, 0.0

    def cluster_scenes(self, vectors, eps=0.15, min_samples=1):
        """Gom nhóm bối cảnh"""
        if not vectors:
            return []
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(vectors)
        return clustering.labels_
