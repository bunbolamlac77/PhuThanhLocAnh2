import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, ChevronLeft, Layers, EyeOff } from 'lucide-react';

interface ReviewScreenProps {
  folderPath: string;
  onConfirm: () => void;
}

export default function ReviewScreen({ folderPath, onConfirm }: ReviewScreenProps) {
  const [data, setData] = useState<any>(null);
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null);
  const [activeImage, setActiveImage] = useState<any>(null);

  // Load dữ liệu từ Backend khi màn hình khởi tạo
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/api/review-data?folder_path=${encodeURIComponent(folderPath)}`)
      .then(res => res.json())
      .then(resData => {
        if (resData.status === "success") {
          setData(resData.data);
        }
      });
  }, [folderPath]);

  // Hàm Toggle chọn/bỏ chọn ảnh
  const toggleSelect = (groupId: number, imageName: string) => {
    const newData = { ...data };
    const group = newData.groups.find((g: any) => g.group_id === groupId);
    if (group) {
      const img = group.images.find((i: any) => i.name === imageName);
      if (img) img.selected = !img.selected;
      
      // Update lại Thumbnail của Group nếu cần
      const hasSelected = group.images.find((i: any) => i.selected);
      group.best_image = hasSelected || group.images[0];
    }
    setData(newData);
  };

  // Hàm Chọn tất cả / Bỏ chọn tất cả trong 1 nhóm
  const setGroupSelection = (groupId: number, status: boolean) => {
    const newData = { ...data };
    const group = newData.groups.find((g: any) => g.group_id === groupId);
    if (group) {
      group.images.forEach((img: any) => img.selected = status);
      const hasSelected = group.images.find((i: any) => i.selected);
      group.best_image = hasSelected || group.images[0];
    }
    setData(newData);
  };

  // Hàm Gửi chốt danh sách
  const handleConfirm = async () => {
    // Gom tất cả các tên ảnh đang có selected = true
    const selectedNames: string[] = [];
    data.groups.forEach((g: any) => {
      g.images.forEach((img: any) => {
        if (img.selected) selectedNames.push(img.name);
      });
    });

    await fetch("http://127.0.0.1:8000/api/confirm-selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_folder: data.raw_folder,
        raw_extension: data.raw_extension,
        selected_names: selectedNames
      })
    });
    onConfirm(); // Chuyển sang màn hình Copy/Move
  };

  if (!data) return <div className="text-white">Đang tải dữ liệu Review...</div>;

  const totalSelected = data.groups.reduce((acc: number, g: any) => acc + g.images.filter((i: any) => i.selected).length, 0);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 bg-background flex flex-col p-6 h-screen overflow-hidden">
      
      {/* --- HEADER --- */}
      <div className="flex justify-between items-center mb-6 px-4 shrink-0">
        <div>
          <h2 className="text-3xl font-light text-white tracking-wide">Kiểm duyệt Ảnh</h2>
          <p className="text-gray-400 text-sm mt-1">Đang chọn <span className="text-blue-400 font-bold">{totalSelected}</span> khoảnh khắc hoàn hảo</p>
        </div>
        <button onClick={handleConfirm} className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-full font-medium transition-all shadow-[0_0_20px_rgba(37,99,235,0.4)] flex items-center gap-2">
          <CheckCircle2 size={20} /> Xác nhận & Đi tiếp
        </button>
      </div>

      <AnimatePresence mode="wait">
        {/* --- TRẠNG THÁI 1: LƯỚI GRID --- */}
        {activeGroupId === null ? (
          <motion.div key="grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto custom-scrollbar px-4 pb-12">
            <div className="grid grid-cols-4 md:grid-cols-5 xl:grid-cols-6 gap-4">
              {data.groups.map((group: any) => (
                <div key={group.group_id} onClick={() => { setActiveGroupId(group.group_id); setActiveImage(group.best_image); }} 
                     className="relative aspect-[2/3] bg-surface rounded-xl overflow-hidden cursor-pointer group border border-white/5 hover:border-blue-500/50 transition-all">
                  <img src={`http://127.0.0.1:8000/api/image?path=${encodeURIComponent(group.best_image.path)}`} 
                       className={`w-full h-full object-cover group-hover:scale-105 transition-all duration-500 ${!group.images.some((i: any) => i.selected) ? 'grayscale opacity-40' : ''}`} alt={group.best_image.name} />
                  
                  {/* Badge đếm số lượng ảnh trong Nhóm */}
                  <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-md px-2 py-1 rounded-lg flex items-center gap-1 border border-white/10 z-10">
                    <Layers size={12} className="text-gray-300" />
                    <span className="text-xs text-white font-medium">{group.images.length}</span>
                  </div>
                  
                  {/* Overlay hiển thị khi Nhóm không có ảnh nào được chọn */}
                  {!group.images.some((i: any) => i.selected) && (
                     <div className="absolute inset-0 flex items-center justify-center">
                       <span className="bg-white/10 backdrop-blur-md text-white/60 text-[10px] uppercase tracking-widest px-3 py-1 rounded-full border border-white/5">Bỏ qua</span>
                     </div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        ) : (

        /* --- TRẠNG THÁI 2: CHI TIẾT (DETAIL & FILMSTRIP) --- */
          <motion.div key="detail" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col bg-black/40 rounded-2xl border border-white/10 overflow-hidden relative">
            
            <div className="absolute top-4 left-4 z-10 flex gap-2">
              <button onClick={() => setActiveGroupId(null)} className="bg-black/50 hover:bg-black p-2 rounded-full backdrop-blur-md text-white transition-colors">
                <ChevronLeft size={24} />
              </button>
            </div>

            <div className="absolute top-4 right-4 z-10 flex gap-2">
               <button onClick={() => setGroupSelection(activeGroupId!, true)} className="bg-blue-500/20 hover:bg-blue-500 text-blue-400 hover:text-white px-4 py-1.5 rounded-full backdrop-blur-md text-xs border border-blue-500/30 transition-all">
                 Chọn Tất cả
               </button>
               <button onClick={() => setGroupSelection(activeGroupId!, false)} className="bg-white/5 hover:bg-white/20 text-gray-400 hover:text-white px-4 py-1.5 rounded-full backdrop-blur-md text-xs border border-white/10 transition-all">
                 Bỏ chọn hết
               </button>
            </div>

            {/* Ảnh lớn ở giữa */}
            <div className="flex-1 flex items-center justify-center p-4">
              {activeImage && (
                <img src={`http://127.0.0.1:8000/api/image?path=${encodeURIComponent(activeImage.path)}`} className="max-w-full max-h-full object-contain rounded-lg shadow-2xl" alt={activeImage.name} />
              )}
            </div>

            {/* Dải phim (Filmstrip) các ảnh trong cùng Nhóm */}
            <div className="h-44 bg-surface/80 backdrop-blur-xl border-t border-white/10 p-4 overflow-x-auto whitespace-nowrap custom-scrollbar flex items-center gap-3 shrink-0">
              {data.groups.find((g: any) => g.group_id === activeGroupId)?.images.map((img: any) => (
                <div key={img.name} className="relative inline-block h-full aspect-[2/3] cursor-pointer group" onClick={() => setActiveImage(img)}>
                  
                  <img src={`http://127.0.0.1:8000/api/image?path=${encodeURIComponent(img.path)}`} 
                       className={`w-full h-full object-cover rounded-lg border-2 transition-all ${activeImage?.name === img.name ? 'border-blue-400' : 'border-transparent'}`} alt={img.name} />
                  
                  {/* Nút Tick xanh - Nhấp vào để Chọn/Bỏ chọn */}
                  <div onClick={(e) => { e.stopPropagation(); toggleSelect(activeGroupId, img.name); }} 
                       className={`absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center border-2 transition-colors z-10 ${img.selected ? 'bg-blue-500 border-blue-500 text-white' : 'bg-black/50 border-white/50 text-transparent hover:border-white'}`}>
                    <CheckCircle2 size={16} />
                  </div>

                  {/* Cảnh báo nhắm mắt */}
                  {img.blink_count > 0 && (
                     <div className="absolute bottom-2 left-2 bg-red-500/80 backdrop-blur-md text-white px-2 py-1 rounded text-[10px] font-bold flex items-center gap-1">
                       <EyeOff size={10} /> Nhắm mắt
                     </div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
