import os
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse # Thêm dòng này để trả về file ảnh
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import glob
import shutil
import urllib.parse
from typing import Optional

# Import các module nội bộ
from database import init_db, save_image_record
from ai_engine import AIEngine

# Khởi tạo App & DB
app = FastAPI(title="AI Culling Core")
init_db()

# Thêm dòng này ở dưới phần khai báo app = FastAPI(...)
# Quản lý bộ nhớ tạm cho kết quả Review (Key là folder_path)
global_review_sessions = {}

def add_review_session(folder_path, data):
    """Lưu session và giới hạn tối đa 5 session để tránh tràn RAM"""
    if len(global_review_sessions) >= 5:
        # Xóa session cũ nhất
        oldest_key = next(iter(global_review_sessions))
        del global_review_sessions[oldest_key]
    global_review_sessions[folder_path] = data

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

async def broadcast_progress(progress: float, current_file: str, status: str = "processing", total_selected: int = 0, total_files: int = 0, extension: str = ""):
    """Hàm gửi phần trăm tải theo thời gian thực xuống React UI"""
    for ws in list(active_websockets):
        try:
            await ws.send_json({
                "progress": progress,
                "current_file": current_file,
                "status": status,
                "total_selected": total_selected,
                "total_files": total_files,
                "extension": extension
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
        parent_folder=parent_folder,
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

@app.get("/api/image")
def serve_image(path: str):
    """API giúp React UI có thể load và hiển thị file ảnh từ ổ cứng Mac"""
    if not os.path.exists(path):
        return {"status": "error", "message": "File không tồn tại"}
    
    # Chỉ cho phép các định dạng ảnh phổ biến
    ext = os.path.splitext(path)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.arw', '.cr2', '.cr3', '.nef', '.dng']:
        return {"status": "error", "message": "Định dạng file không được hỗ trợ"}

    return FileResponse(path)

@app.get("/api/review-data")
def get_review_data(folder_path: str):
    """API trả về dữ liệu các nhóm ảnh để Review"""
    return {"status": "success", "data": global_review_sessions.get(folder_path, [])}

class ConfirmRequest(BaseModel):
    raw_folder: str
    raw_extension: str
    selected_names: list[str]

@app.post("/api/confirm-selection")
def confirm_selection(request: ConfirmRequest):
    """API nhận danh sách chốt cuối cùng từ UI và ghi ra file TXT"""
    export_path = os.path.join(request.raw_folder, "selected_files.txt")
    with open(export_path, "w", encoding="utf-8") as f:
        for name in request.selected_names:
            f.write(f"{name}.{request.raw_extension}\n")
    return {"status": "success"}

async def run_culling_pipeline(image_files, raw_folder, jpg_folder, parent_folder, raw_extension="ARW"):
    """Luồng xử lý AI: BẢO TOÀN KHOẢNH KHẮC BẰNG BỐI CẢNH & SỐ LƯỢNG NGƯỜI"""
    total = len(image_files)
    scanned_data = []

    for i, file_path in enumerate(image_files):
        if cancel_event.is_set():
            await broadcast_progress(0, "Đã hủy.", "cancelled", 0, total)
            return

        # Gọi phân tích AI
        vec, face_count, score, blink_count = ai.analyze_image(file_path)
        
        save_image_record(file_path, score)
        base_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        
        if vec is not None:
            scanned_data.append({
                "name": base_name_no_ext,
                "path": file_path,
                "score": score,
                "face_count": face_count,
                "blink_count": blink_count,
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
        is_same_scene = (data["scene_label"] == prev_data["scene_label"])
        
        # Tách biệt chân dung lẻ (1 người) ra khỏi các nhóm đông người
        # Nếu số lượng người thay đổi (từ 1 người sang 2+ người hoặc ngược lại), coi như Moment mới
        if data["face_count"] == 1 or prev_data["face_count"] == 1:
            is_same_group = (data["face_count"] == prev_data["face_count"])
        else:
            is_same_group = abs(data["face_count"] - prev_data["face_count"]) <= 1
        
        if is_same_scene and is_same_group:
            current_moment.append(data)
        else:
            moments.append(current_moment)
            current_moment = [data]
            
    if current_moment:
        moments.append(current_moment)

    # Bước 4: LỖI KÉP & CHỌN ẢNH TỐI ƯU TRONG TỪNG NHỊP
    selected_names = []
    
    for moment in moments:
        size = len(moment)
        # Tính trung bình số mặt trong khoảnh khắc
        avg_faces = sum(m["face_count"] for m in moment) / size
        
        # LOGIC CHỌN ẢNH:
        # - Nếu là chân dung lẻ (face = 1): Cứ 2 tấm giữ 1 (Tỷ lệ 50% - Đảm bảo đa dạng biểu cảm)
        # - Nếu là nhóm nhỏ (face <= 2): Cứ 3 tấm giữ 1 (Tỷ lệ 33%)
        # - Nếu là nhóm lớn (face > 2): Cứ 4 tấm giữ 1 (Tỷ lệ 25%)
        
        if avg_faces == 1.0:
            chunk_size = 2
        elif avg_faces <= 2.0:
            chunk_size = 3
        else:
            chunk_size = 4
            
        if size <= chunk_size:
            # Nếu moment quá ngắn, chọn tấm tốt nhất (không nhắm mắt + score cao)
            best = max(moment, key=lambda x: (-x["blink_count"], x["score"]))
            selected_names.append(best["name"])
        else:
            # Chia nhỏ moment thành các chunk và chọn ảnh tốt nhất trong mỗi chunk
            for i in range(0, size, chunk_size):
                chunk = moment[i : i + chunk_size]
                best = max(chunk, key=lambda x: (-x["blink_count"], x["score"]))
                selected_names.append(best["name"])

    # Lọc trùng
    selected_names = list(set(selected_names))
    total_selected = len(selected_names)

    # ĐÓNG GÓI DỮ LIỆU THÀNH CÁC NHÓM CHO MÀN HÌNH REVIEW
    review_data = []
    for idx, moment in enumerate(moments):
        group_imgs = []
        best_img = None
        
        for m in moment:
            is_sel = m["name"] in selected_names
            img_obj = {
                "name": m["name"],
                "path": m["path"],
                "score": round(m["score"], 1),
                "blink_count": m["blink_count"],
                "selected": is_sel
            }
            group_imgs.append(img_obj)
            if is_sel and best_img is None:
                best_img = img_obj
                
        if best_img is None and group_imgs:
            best_img = group_imgs[0]
            
        review_data.append({
            "group_id": idx,
            "best_image": best_img,
            "images": group_imgs
        })

    # Lưu vào bộ nhớ Ram của Python sử dụng hàm quản lý session
    add_review_session(parent_folder, {
        "raw_folder": raw_folder,
        "raw_extension": raw_extension,
        "groups": review_data
    })

    print(f"[AI Logic] Đang chuẩn bị xong dữ liệu Review cho {len(moments)} bối cảnh.")
    
    # Gửi tín hiệu 'review_ready' để React chuyển màn hình, kèm theo extension
    await broadcast_progress(100, f"Xong! Hãy kiểm duyệt lại ảnh.", "review_ready", total_selected, total, raw_extension)



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
            # Hỗ trợ case-insensitive cho extension nếu cần
            raw_file_path = os.path.join(request.source_folder, file_name)
            
            # Nếu không tìm thấy, thử tìm bản case-insensitive
            if not os.path.exists(raw_file_path):
                base, ext = os.path.splitext(file_name)
                # Tìm trong folder các file có tên trùng (không phân biệt hoa thường)
                files_in_dir = os.listdir(request.source_folder)
                matched = [f for f in files_in_dir if f.lower() == file_name.lower()]
                if matched:
                    raw_file_path = os.path.join(request.source_folder, matched[0])

            if os.path.exists(raw_file_path):
                try:
                    if request.action_type == "copy":
                        shutil.copy2(raw_file_path, request.destination_folder)
                    elif request.action_type == "move":
                        shutil.move(raw_file_path, request.destination_folder)
                    success_count += 1
                except Exception as ex:
                    print(f"Lỗi khi xử lý file {file_name}: {ex}")
                    not_found.append(f"{file_name} (Lỗi access)")
            else:
                not_found.append(file_name)

        return {
            "status": "success",
            "processed": success_count,
            "total_in_list": len(file_names),
            "failed_files": not_found,
            "not_found_count": len(not_found)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

