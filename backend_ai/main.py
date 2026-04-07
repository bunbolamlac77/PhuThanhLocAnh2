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
    """Luồng xử lý AI đa tầng với Thuật toán Gom nhóm DBSCAN và Luật Top K"""
    total = len(image_files)
    scanned_data = [] # Lưu trữ toàn bộ dữ liệu quét: Tên, Điểm, Vector

    for i, file_path in enumerate(image_files):
        if cancel_event.is_set():
            await broadcast_progress(
                progress=0, current_file="Tiến trình đã bị hủy.", status="cancelled", total_files=total
            )
            return

        # 1. Trích xuất vector bối cảnh bằng DINOv2
        vec = ai.extract_scene_vector(file_path)
        
        # 2. Chấm điểm ảnh (Tạm thời là giả lập, sau này thay bằng LIQE + InsightFace)
        score = ai.mock_evaluate_image(file_path)

        # 3. Lưu dữ liệu
        save_image_record(file_path, score)
        base_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        
        scanned_data.append({
            "name": base_name_no_ext,
            "score": score,
            "vector": vec
        })

        # Báo cáo tiến độ
        progress_percent = int(((i + 1) / total) * 100)
        await broadcast_progress(
            progress=progress_percent,
            current_file=os.path.basename(file_path),
            total_files=total,
        )
        await asyncio.sleep(0.01)

    print("\n[AI Logic] Bắt đầu gom nhóm và chọn lọc...")

    # ---- BỘ LỌC ĐA TẦNG CỐT LÕI (THE BRAIN) ----
    
    # Bước A: Lọc các ảnh không đọc được vector
    valid_data = [d for d in scanned_data if d["vector"] is not None]
    vectors = [d["vector"] for d in valid_data]

    # Bước B: Chạy thuật toán phân cụm DBSCAN
    # eps=0.5 (Tùy chỉnh: Giảm eps nếu muốn chia nhỏ nhóm hơn, Tăng eps nếu muốn gộp nhóm lớn hơn)
    labels = ai.cluster_scenes(vectors, eps=0.5, min_samples=1)

    # Tổ chức ảnh vào các nhóm
    clusters = {}
    for idx, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(valid_data[idx])

    selected_names = []

    # Bước C: Áp dụng Cây quyết định (Quy tắc Top K) cho từng nhóm
    for label, items in clusters.items():
        # Sắp xếp ảnh trong cùng 1 nhóm theo thứ tự điểm từ cao xuống thấp
        items.sort(key=lambda x: x["score"], reverse=True)
        size = len(items)

        if size == 1:
            # Rule 1: Chụp tĩnh vật / Decor 1 tấm -> Giữ lại nguyên vẹn ý đồ
            selected_names.append(items[0]["name"])
        elif size <= 4:
            # Rule 2: Chụp cụm nhỏ (ví dụ bấm burst 3-4 tấm 1 dáng) -> Chỉ lấy 1 tấm xuất sắc nhất
            selected_names.append(items[0]["name"])
        else:
            # Rule 3: Chụp cụm lớn (Cô dâu chú rể đi lại, hành động dài) 
            # -> Lấy Top 30% số ảnh nét nhất trong phân cảnh đó (tối thiểu giữ 2 tấm)
            keep_count = max(2, int(size * 0.3))
            for i in range(keep_count):
                selected_names.append(items[i]["name"])

    # Xóa trùng lặp (nếu có)
    selected_names = list(set(selected_names))
    total_selected = len(selected_names)

    # ---- XUẤT FILE TXT ----
    export_path = os.path.join(raw_folder, "selected_files.txt")
    with open(export_path, "w", encoding="utf-8") as f:
        for name in selected_names:
            f.write(f"{name}.{raw_extension}\n")

    print(f"[AI Logic] Hoàn tất. Từ {total} ảnh ban đầu -> Gom thành {len(clusters)} bối cảnh/dáng -> Chọn lọc giữ lại {total_selected} ảnh.")
    
    await broadcast_progress(
        progress=100,
        current_file=f"Hoàn tất! Cắt giảm còn {total_selected}/{total} ảnh",
        status="completed",
        total_selected=total_selected,
        total_files=total,
    )



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

