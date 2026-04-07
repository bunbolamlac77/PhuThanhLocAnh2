import os
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import glob
import shutil
from typing import Optional

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
    raw_extension: Optional[str] = "ARW"  # Nếu UI không truyền, backend sẽ tự detect

class ActionRequest(BaseModel):
    source_folder: str
    destination_folder: str
    action_type: str  # 'copy' hoặc 'move'

# Biến toàn cục điều khiển tiến trình
active_websockets = []
cancel_event = asyncio.Event()

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Giữ kết nối
    except:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

async def broadcast_progress(progress: float, current_file: str, status: str = "processing", total_selected: int = 0, total_files: int = 0):
    """Hàm gửi phần trăm tải theo thời gian thực xuống React UI"""
    for ws in list(active_websockets):
        try:
            await ws.send_json({
                "progress": progress,
                "current_file": current_file,
                "status": status,
                "total_selected": total_selected,
                "total_files": total_files,
            })
        except:
            continue

def detect_raw_extension(raw_folder: str) -> str:
    """
    Tự động nhận diện extension RAW phổ biến nhất trong thư mục.
    Nếu không thấy, mặc định trả về ARW.
    """
    extensions = ['.ARW', '.CR2', '.CR3', '.NEF', '.DNG', '.RAF', '.ORF']
    counts = {}
    
    for entry in os.scandir(raw_folder):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].upper()
            if ext in extensions:
                counts[ext] = counts.get(ext, 0) + 1
    
    if not counts:
        return "ARW"
    
    # Trả về extension có số lượng file nhiều nhất
    return max(counts, key=counts.get).replace(".", "")

def find_jpg_subfolder(parent_folder: str):
    """
    Tự động nhận diện cấu trúc thư mục:
    - Thư mục Cha: chứa file RAW
    - Thư mục Con: chứa file JPG (tên bất kỳ)
    Trả về (thư mục chứa JPG, thư mục chứa RAW, extension RAW tự nhận diện)
    """
    # Tìm file JPG trực tiếp trong thư mục cha
    jpg_in_parent = glob.glob(os.path.join(parent_folder, "*.[jJ][pP][gG]"))

    # Tìm các thư mục con
    subfolders = [
        f for f in os.scandir(parent_folder)
        if f.is_dir() and not f.name.startswith('.')
    ]

    best_jpg_folder = None
    best_count = len(jpg_in_parent)

    if jpg_in_parent:
        best_jpg_folder = parent_folder

    for sub in subfolders:
        jpgs = glob.glob(os.path.join(sub.path, "*.[jJ][pP][gG]"))
        if len(jpgs) > best_count:
            best_count = len(jpgs)
            best_jpg_folder = sub.path

    # Tự động detect RAW extension từ thư mục cha
    detected_raw_ext = detect_raw_extension(parent_folder)

    return best_jpg_folder, parent_folder, detected_raw_ext


@app.post("/start-scan")
async def start_scan(request: ScanRequest):
    """API chính nhận lệnh bắt đầu quét từ UI"""
    parent_folder = request.folder_path
    
    # Reset cancel event
    cancel_event.clear()

    # ---- AUTO-DETECT cấu trúc thư mục ----
    jpg_folder, raw_folder, detected_raw_ext = find_jpg_subfolder(parent_folder)
    
    # Ưu tiên extension từ UI nếu có, nếu không dùng tự nhận diện
    raw_extension = request.raw_extension if request.raw_extension else detected_raw_ext
    raw_extension = raw_extension.upper().strip(".")

    if not jpg_folder:
        return {"status": "error", "message": "Không tìm thấy file JPG nào trong thư mục hoặc thư mục con!"}

    image_files = glob.glob(os.path.join(jpg_folder, "*.[jJ][pP][gG]"))
    total_files = len(image_files)

    if total_files == 0:
        return {"status": "error", "message": f"Không tìm thấy file JPG trong: {jpg_folder}"}

    # THỰC THI PIPELINE LỌC ẢNH (CHẠY NGẦM)
    asyncio.create_task(run_culling_pipeline(
        image_files=image_files,
        raw_folder=raw_folder,
        jpg_folder=jpg_folder,
        raw_extension=raw_extension
    ))

    return {
        "status": "started",
        "total_files": total_files,
        "jpg_folder": jpg_folder,
        "raw_folder": raw_folder,
        "detected_raw_ext": detected_raw_ext
    }

@app.post("/stop-scan")
async def stop_scan():
    """Dừng tiến trình quét hiện tại"""
    cancel_event.set()
    return {"status": "stopping", "message": "Đang dừng tiến trình..."}

async def run_culling_pipeline(image_files, raw_folder, jpg_folder, raw_extension="ARW"):
    """Luồng xử lý AI: BẢO TOÀN KHOẢNH KHẮC BẰNG BỐI CẢNH & SỐ LƯỢNG NGƯỜI"""
    total = len(image_files)
    scanned_data = []

    for i, file_path in enumerate(image_files):
        if cancel_event.is_set():
            await broadcast_progress(0, "Đã hủy.", "cancelled", 0, total)
            return

        # Gọi hàm ALL-IN-ONE mới từ AI Engine
        vec, face_count, score = ai.analyze_image(file_path)
        
        save_image_record(file_path, score)
        base_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        
        if vec is not None:
            scanned_data.append({
                "name": base_name_no_ext,
                "score": score,
                "face_count": face_count,
                "vector": vec
            })

        progress_percent = int(((i + 1) / total) * 100)
        await broadcast_progress(progress_percent, os.path.basename(file_path), total_files=total)
        await asyncio.sleep(0.01)

    print("\n[AI Logic] Bắt đầu Thuật toán Phân tách Nhịp bấm máy...")

    # Bước 1: Gán nhãn bối cảnh (Background)
    vectors = [d["vector"] for d in scanned_data]
    scene_labels = ai.cluster_scenes(vectors, eps=0.15)
    
    for idx, data in enumerate(scanned_data):
        data["scene_label"] = scene_labels[idx]

    # Bước 2: Sắp xếp toàn bộ ảnh theo thứ tự bấm máy (Chronological)
    scanned_data.sort(key=lambda x: x["name"])

    # Bước 3: TẠO CÁC NHỊP BẤM MÁY (MOMENTS)
    moments = []
    current_moment = []

    for data in scanned_data:
        if not current_moment:
            current_moment.append(data)
            continue
            
        prev_data = current_moment[-1]
        
        # ĐIỀU KIỆN ĐỂ 2 ẢNH Ở TRONG CÙNG 1 NHỊP:
        # 1. Background giống nhau
        is_same_scene = (data["scene_label"] == prev_data["scene_label"])
        # 2. Số lượng khuôn mặt không chênh lệch quá 1
        is_same_group = abs(data["face_count"] - prev_data["face_count"]) <= 1
        
        if is_same_scene and is_same_group:
            current_moment.append(data)
        else:
            moments.append(current_moment)
            current_moment = [data]
            
    if current_moment:
        moments.append(current_moment)

    # Bước 4: LỌC TRONG TỪNG NHỊP BẰNG CHRONOLOGICAL CHUNKING (Cắt lô theo thời gian)
    selected_names = []
    
    for moment in moments:
        # LƯU Ý QUAN TRỌNG: KHÔNG sort toàn bộ moment theo score nữa.
        # Phải giữ nguyên thứ tự thời gian (đã sort theo tên file ở Bước 2)
        size = len(moment)
        
        # Phân tích xem nhịp này là Chân dung hay Chụp nhóm
        # Tính trung bình số người trong nhịp này
        avg_faces = sum(m["face_count"] for m in moment) / size
        
        # TỰ ĐỘNG THÍCH ỨNG (DYNAMIC CHUNKING)
        if avg_faces <= 1.5:
            # KIỂU 1: CHỤP CHÂN DUNG (1 người)
            # Dâu/rể sẽ đổi dáng liên tục. Bạn thường bấm 2-3 tấm cho 1 dáng.
            # -> Cắt lô nhỏ (3 ảnh/lô) để lấy được nhiều dáng khác nhau.
            chunk_size = 3
        else:
            # KIỂU 2: CHỤP COUPLE HOẶC GIA ĐÌNH (>= 2 người)
            # Khách ít đổi dáng hơn, nhưng bạn phải bấm nhồi để phòng nhắm mắt.
            # -> Cắt lô lớn hơn (4-5 ảnh/lô) để lọc gắt hơn, chỉ lấy tấm nét nhất, mở mắt đều nhất.
            chunk_size = 4
            
        if size <= 2:
            # Nếu chỉ bấm lẻ 1-2 tấm -> Chắc chắn lấy tấm nét nhất
            best = max(moment, key=lambda x: x["score"])
            selected_names.append(best["name"])
        else:
            # Duyệt qua từng lô nhỏ theo đúng THỨ TỰ THỜI GIAN
            for i in range(0, size, chunk_size):
                chunk = moment[i : i + chunk_size]
                
                # Trong Lô 3 ảnh liên tiếp (đại diện cho 1 dáng đứng), chọn 1 tấm Nét Nhất
                best = max(chunk, key=lambda x: x["score"])
                selected_names.append(best["name"])

    # Lọc trùng và Xuất file
    selected_names = list(set(selected_names))
    total_selected = len(selected_names)

    export_path = os.path.join(raw_folder, "selected_files.txt")
    with open(export_path, "w", encoding="utf-8") as f:
        for name in selected_names:
            f.write(f"{name}.{raw_extension}\n")

    print(f"[AI Logic] Từ {total} ảnh -> Chia thành {len(moments)} nhịp bấm máy riêng biệt.")
    print(f"[AI Logic] Lọc giữ lại {total_selected} ảnh xuất sắc nhất.")
    
    await broadcast_progress(100, f"Xong! Đã chọn {total_selected}/{total} ảnh", "completed", total_selected, total)



@app.post("/execute-action")
async def execute_action(request: ActionRequest):
    """
    Copy hoặc Move file RAW dựa trên file selected_files.txt.
    """
    txt_path = os.path.join(request.source_folder, "selected_files.txt")

    if not os.path.exists(txt_path):
        return {"status": "error", "message": f"Không tìm thấy file danh sách tại: {txt_path}"}

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            file_names = [line.strip() for line in f.readlines() if line.strip()]

        if not os.path.exists(request.destination_folder):
            os.makedirs(request.destination_folder, exist_ok=True)

        success_count = 0
        not_found = []

        for file_name in file_names:
            # Tìm file có tên tương ứng trong thư mục nguồn (không quan tâm case-sensitive nếu cần)
            # Ở đây chúng ta giả định tên file trong txt là chính xác
            raw_file_path = os.path.join(request.source_folder, file_name)

            if os.path.exists(raw_file_path):
                if request.action_type == "copy":
                    shutil.copy2(raw_file_path, request.destination_folder)
                elif request.action_type == "move":
                    shutil.move(raw_file_path, request.destination_folder)
                success_count += 1
            else:
                not_found.append(file_name)

        return {
            "status": "success",
            "processed": success_count,
            "total_in_list": len(file_names),
            "not_found": not_found[:10],
            "not_found_count": len(not_found)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

