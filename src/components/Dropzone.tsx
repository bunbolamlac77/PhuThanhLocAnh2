import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';

interface DropzoneProps {
  onDrop: (path: string) => void;
}

export default function Dropzone({ onDrop }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isStarting, setIsStarting] = useState(false);

  // Mở hộp thoại hệ thống của Mac để chọn Folder
  const handleSelectFolder = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Chọn Thư mục chứa ảnh JPG"
      });
      
      if (selected && typeof selected === 'string') {
        setIsStarting(true);
        // Gọi API sang Python
        const res = await fetch("http://127.0.0.1:8000/start-scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ folder_path: selected })
        });
        const data = await res.json();
        
        if (data.status === "started") {
          onDrop(selected); // Chuyển sang màn hình Processing
        } else {
          alert("Lỗi từ AI: " + data.message);
          setIsStarting(false);
        }
      }
    } catch (err) {
      console.error(err);
      setIsStarting(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
      className="w-full max-w-3xl aspect-video rounded-3xl p-1 relative"
    >
      <motion.div 
        animate={{ boxShadow: isDragging ? "0px 0px 60px 20px rgba(59, 130, 246, 0.6)" : ["0px 0px 20px 0px rgba(59, 130, 246, 0.1)", "0px 0px 40px 10px rgba(59, 130, 246, 0.2)", "0px 0px 20px 0px rgba(59, 130, 246, 0.1)"] }}
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
          {isStarting ? "Đang khởi động AI..." : "Click hoặc Kéo thả thư mục vào đây"}
        </h2>
        <p className="text-gray-400 tracking-wider text-sm">
          Sử dụng kiến trúc đa tầng (DINOv2 + Pose) để phân tích bối cảnh.
        </p>
      </div>
    </motion.div>
  );
}
