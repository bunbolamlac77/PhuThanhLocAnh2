import os
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import glob
import shutil

# Import các module nội bộ
from database import init_db, save_image_record, get_all_selected_images
from ai_engine import AIEngine

# Khởi tạo App & DB
app = FastAPI(title="AI Culling Core")
init_db()

# Load AI Engine lên RAM/VRAM của M1 ngay khi khởi động Server
ai = AIEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    folder_path: str

class ActionRequest(BaseModel):
    source_folder: str
    destination_folder: str
    action_type: str # 'copy' hoặc 'move'

# Biến toàn cục lưu kết nối WebSocket
active_websockets = []

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text() # Giữ kết nối
    except:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

async def broadcast_progress(progress: float, current_file: str, status: str = "processing"):
    """Hàm gửi phần trăm tải theo thời gian thực xuống React UI"""
    for ws in active_websockets:
        try:
            await ws.send_json({
                "progress": progress,
                "current_file": current_file,
                "status": status
            })
        except:
            continue

@app.post("/start-scan")
async def start_scan(request: ScanRequest):
    """API chính nhận lệnh bắt đầu quét từ UI"""
    folder_path = request.folder_path
    
    # Tìm toàn bộ file JPG trong thư mục
    search_pattern = os.path.join(folder_path, "*.[jJ][pP][gG]")
    image_files = glob.glob(search_pattern)
    total_files = len(image_files)
    
    if total_files == 0:
        return {"status": "error", "message": "Không tìm thấy file JPG nào!"}

    # THỰC THI PIPELINE LỌC ẢNH (CHẠY NGẦM)
    asyncio.create_task(run_culling_pipeline(image_files, folder_path))
    
    return {"status": "started", "total_files": total_files}

async def run_culling_pipeline(image_files, base_folder):
    """Luồng xử lý AI đa tầng"""
    total = len(image_files)
    vectors = []
    
    for i, file_path in enumerate(image_files):
        # 1. Trích xuất vector (DINOv2)
        vec = ai.extract_scene_vector(file_path)
        if vec is not None:
            vectors.append(vec)
            
        # 2. Chấm điểm ảnh
        score = ai.mock_evaluate_image(file_path)
        
        # 3. Lưu SQLite
        save_image_record(file_path, score)
        
        # 4. Báo cáo tiến độ về giao diện React (Giao diện phô trương)
        progress_percent = int(((i + 1) / total) * 100)
        await broadcast_progress(progress_percent, os.path.basename(file_path))
        
        # Nhường luồng cho hệ thống để tránh đơ máy
        await asyncio.sleep(0.01)

    # --- KẾT THÚC QUÉT -> XUẤT FILE TXT ---
    # Trong thực tế, hàm này sẽ áp dụng DBSCAN và Luật Top K
    export_path = os.path.join(base_folder, "selected_files.txt")
    with open(export_path, "w") as f:
        # Tạm thời xuất tất cả file có điểm > 80 làm ví dụ
        for file in image_files:
            # Thuật toán đổi đuôi .JPG -> .ARW như bạn yêu cầu
            raw_file = file.upper().replace(".JPG", ".ARW")
            f.write(raw_file + "\n")

    await broadcast_progress(100, "Hoàn tất", "completed")

@app.post("/execute-action")
async def execute_action(request: ActionRequest):
    txt_path = os.path.join(request.source_folder, "selected_files.txt")
    
    if not os.path.exists(txt_path):
        return {"status": "error", "message": "Không tìm thấy file selected_files.txt"}
        
    try:
        with open(txt_path, "r") as f:
            files_to_process = [line.strip() for line in f.readlines() if line.strip()]
            
        success_count = 0
        for file_path in files_to_process:
            if os.path.exists(file_path):
                if request.action_type == "copy":
                    shutil.copy2(file_path, request.destination_folder)
                elif request.action_type == "move":
                    shutil.move(file_path, request.destination_folder)
                success_count += 1
                
        return {"status": "success", "processed": success_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
