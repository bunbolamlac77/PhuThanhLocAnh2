import torch
import cv2
import numpy as np
import math
from transformers import AutoImageProcessor, AutoModel
from sklearn.cluster import DBSCAN
from insightface.app import FaceAnalysis

class AIEngine:
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"[AI Engine] Đang chạy trên thiết bị: {self.device}")
        
        print("[AI Engine] Đang tải mô hình DINOv2 (Bối cảnh)...")
        self.processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
        self.dino_model = AutoModel.from_pretrained('facebook/dinov2-small').to(self.device).eval()
        
        print("[AI Engine] Đang tải mô hình InsightFace (Nhận diện khuôn mặt)...")
        # Thử nghiệm CoreMLExecutionProvider nếu có (cho Mac Silicon)
        providers = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
        self.face_app = FaceAnalysis(name='buffalo_s', providers=providers)
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

    def _calculate_ear(self, landmarks, eye_indices):
        """Hàm toán học tính tỉ lệ mở của mắt (Eye Aspect Ratio) sử dụng tọa độ Landmarks"""
        # Trích xuất 6 điểm mốc cho một mắt: p0, p1, p2, p3, p4, p5
        # Index chuẩn: p0(khóe mắt trái), p1, p2(mí trên), p3(khóe mắt phải), p4, p5(mí dưới)
        pts = landmarks[eye_indices]
        
        # Tính khoảng cách dọc theo trục Y (khoảng cách mí trên - mí dưới)
        v1 = math.hypot(pts[1][0] - pts[5][0], pts[1][1] - pts[5][1])
        v2 = math.hypot(pts[2][0] - pts[4][0], pts[2][1] - pts[4][1])
        # Tính khoảng cách ngang (chiều dài mắt)
        h = math.hypot(pts[0][0] - pts[3][0], pts[0][1] - pts[3][1])
        
        if h == 0: return 0
        return (v1 + v2) / (2.0 * h)

    def analyze_image(self, image_path):
        """Trích xuất Vector bối cảnh, Đếm khuôn mặt, Độ nét và Đếm số người NHẮM MẮT"""
        try:
            image_data = np.fromfile(image_path, dtype=np.uint8)
            image_bgr = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            if image_bgr is None: return None, 0, 0.0, 0

            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            
            # 1. BỐI CẢNH (DINOv2)
            inputs = self.processor(images=image_rgb, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.dino_model(**inputs)
            vector = outputs.last_hidden_state[0][0].cpu().numpy()
            norm = np.linalg.norm(vector)
            if norm > 0: vector = vector / norm
                
            # 2. ĐẾM KHUÔN MẶT & MẮT NHẮM (InsightFace)
            faces = self.face_app.get(image_bgr)
            face_count = len(faces)
            
            # 3. ĐỘ NÉT CƠ BẢN
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            sharpness_score = cv2.Laplacian(gray, cv2.CV_64F).var()

            # 4. KIỂM TRA MẮT NHẮM (Sử dụng 68 landmarks từ InsightFace)
            blink_count = 0
            
            # Index cho bộ 68 landmarks (iBUG)
            # Mắt trái: 36, 37, 38, 39, 40, 41
            # Mắt phải: 42, 43, 44, 45, 46, 47
            LEFT_EYE_IDX = [36, 37, 38, 39, 40, 41]
            RIGHT_EYE_IDX = [42, 43, 44, 45, 46, 47]
            
            for face in faces:
                if 'landmark_3d_68' in face:
                    landmarks = face.landmark_3d_68
                    left_ear = self._calculate_ear(landmarks, LEFT_EYE_IDX)
                    right_ear = self._calculate_ear(landmarks, RIGHT_EYE_IDX)
                    
                    # Ngưỡng EAR < 0.20 cho Landmark iBUG (InsightFace nhạy hơn Mediapipe)
                    if left_ear < 0.20 or right_ear < 0.20:
                        blink_count += 1
            
            return vector, face_count, sharpness_score, blink_count
            
        except Exception as e:
            print(f"Lỗi đọc ảnh {image_path}: {e}")
            return None, 0, 0.0, 0

    def cluster_scenes(self, vectors, eps=0.15, min_samples=1):
        if not vectors: return []
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(vectors)
        return clustering.labels_
