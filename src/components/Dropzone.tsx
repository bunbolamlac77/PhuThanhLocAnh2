import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, ChevronDown, Check } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';

interface DropzoneProps {
  onDrop: (path: string) => void;
}

const RAW_EXTENSIONS = [
  { label: 'Sony (.ARW)', value: 'ARW' },
  { label: 'Canon (.CR3)', value: 'CR3' },
  { label: 'Canon (.CR2)', value: 'CR2' },
  { label: 'Nikon (.NEF)', value: 'NEF' },
  { label: 'Fujifilm (.RAF)', value: 'RAF' },
  { label: 'Adobe (.DNG)', value: 'DNG' },
  { label: 'Olympus (.ORF)', value: 'ORF' },
];

export default function Dropzone({ onDrop }: DropzoneProps) {
  const isDragging = false;
  const [isStarting, setIsStarting] = useState(false);
  const [selectedExt, setSelectedExt] = useState(RAW_EXTENSIONS[0]); // ARW mặc định
  const [isExtMenuOpen, setIsExtMenuOpen] = useState(false);

  const handleSelectFolder = async () => {
    if (isStarting) return;
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Chọn Thư mục Cha (Chứa cả ảnh RAW và thư mục JPG)"
      });

      if (selected && typeof selected === 'string') {
        setIsStarting(true);
        const res = await fetch("http://127.0.0.1:8000/start-scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            folder_path: selected,
            raw_extension: selectedExt.value // Vẫn truyền cái đang chọn, nhưng backend sẽ báo về cái nó detect được
          })
        });
        const data = await res.json();

        if (data.status === "started") {
          // Nếu backend detect được extension khác, có thể cập nhật UI (tùy chọn)
          if (data.detected_raw_ext) {
            const matched = RAW_EXTENSIONS.find(e => e.value === data.detected_raw_ext);
            if (matched) setSelectedExt(matched);
          }
          onDrop(selected);
        } else {
          alert("Lỗi: " + data.message);
          setIsStarting(false);
        }
      }
    } catch (err) {
      console.error(err);
      alert("Không thể kết nối tới AI backend. Hãy đảm bảo backend đang chạy.");
      setIsStarting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
      className="w-full max-w-3xl flex flex-col gap-5 relative"
    >
      {/* --- Vùng kéo thả / Click --- */}
      <div className="relative aspect-video rounded-3xl p-1">
        {/* Hiệu ứng glow */}
        <motion.div
          animate={{
            boxShadow: isDragging
              ? "0px 0px 60px 20px rgba(59, 130, 246, 0.6)"
              : ["0px 0px 20px 0px rgba(59, 130, 246, 0.1)", "0px 0px 40px 10px rgba(59, 130, 246, 0.2)", "0px 0px 20px 0px rgba(59, 130, 246, 0.1)"]
          }}
          transition={isDragging ? { duration: 0.3 } : { duration: 3, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 blur-xl"
        />

        <div
          onClick={isStarting ? undefined : handleSelectFolder}
          className={`relative h-full w-full rounded-[1.4rem] border-2 border-dashed flex flex-col items-center justify-center transition-all duration-300 backdrop-blur-xl bg-surface cursor-pointer
            ${isDragging ? "border-blue-400 bg-white/10" : "border-white/20 hover:border-white/40"}
            ${isStarting ? "opacity-50 cursor-wait" : ""}`}
        >
          <UploadCloud className={`w-24 h-24 mb-6 ${isDragging ? "text-blue-400" : "text-gray-400"}`} />
          <h2 className="text-3xl font-light tracking-wide text-white mb-2">
            {isStarting ? "Đang phân tích..." : "Chọn Thư mục Cha"}
          </h2>
          <p className="text-gray-400 tracking-wider text-sm text-center max-w-md px-8">
            {isStarting
              ? "Đang tự động nhận diện cấu trúc RAW/JPG..."
              : "Thư mục chứa file RAW và thư mục con chứa ảnh JPG (Ví dụ: Thư mục chứa folder 'jpg')"}
          </p>
        </div>
      </div>

      {/* --- Bảng chọn Extension RAW --- */}
      <div className="relative flex items-center gap-3 px-2">
        <span className="text-gray-400 text-sm whitespace-nowrap">Định dạng muốn lọc:</span>


        <div className="relative">
          <button
            onClick={() => setIsExtMenuOpen(v => !v)}
            disabled={isStarting}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/15 hover:border-blue-400/50 hover:bg-white/10 text-white text-sm font-medium transition-all duration-200 disabled:opacity-50"
          >
            <span className="w-8 h-5 rounded bg-blue-500/20 text-blue-300 text-xs font-bold flex items-center justify-center">
              {selectedExt.value}
            </span>
            {selectedExt.label}
            <ChevronDown
              size={14}
              className={`text-gray-400 transition-transform duration-200 ${isExtMenuOpen ? "rotate-180" : ""}`}
            />
          </button>

          <AnimatePresence>
            {isExtMenuOpen && (
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.97 }}
                transition={{ duration: 0.15 }}
                className="absolute bottom-full mb-2 left-0 z-50 w-52 rounded-2xl border border-white/10 bg-gray-900/95 backdrop-blur-xl shadow-2xl overflow-hidden"
              >
                {RAW_EXTENSIONS.map((ext) => (
                  <button
                    key={ext.value}
                    onClick={() => {
                      setSelectedExt(ext);
                      setIsExtMenuOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-white/10 transition-colors"
                  >
                    <span className={selectedExt.value === ext.value ? "text-blue-300 font-medium" : "text-gray-300"}>
                      {ext.label}
                    </span>
                    {selectedExt.value === ext.value && (
                      <Check size={14} className="text-blue-400" />
                    )}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <p className="text-gray-600 text-xs">
          App sẽ lọc ảnh JPG preview và xuất danh sách file <span className="text-blue-400">.{selectedExt.value}</span> tương ứng
        </p>
      </div>
    </motion.div>
  );
}
