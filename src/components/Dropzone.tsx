import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud } from 'lucide-react';

interface DropzoneProps {
  onDrop: (path: string) => void;
}

export default function Dropzone({ onDrop }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  // Xử lý sự kiện kéo thả (Giả lập cho UI, sau này sẽ móc nối với Tauri)
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = () => setIsDragging(false);
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    // Tạm thời truyền một đường dẫn ảo để kích hoạt màn hình tiếp theo
    onDrop("/Users/Mac/Pictures/Wedding_Raw");
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="w-full max-w-3xl aspect-video rounded-3xl p-1 relative"
    >
      {/* Lớp viền Glow động phía sau - Hiệu ứng Nhịp thở (Breathing) */}
      <motion.div 
        animate={{ 
          boxShadow: isDragging 
            ? "0px 0px 60px 20px rgba(59, 130, 246, 0.6)" 
            : ["0px 0px 20px 0px rgba(59, 130, 246, 0.1)", "0px 0px 40px 10px rgba(59, 130, 246, 0.2)", "0px 0px 20px 0px rgba(59, 130, 246, 0.1)"]
        }}
        transition={isDragging ? { duration: 0.3 } : { duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 blur-xl"
      />

      {/* Box chính - Glassmorphism */}
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => onDrop("/Users/Mac/Pictures/Wedding_Raw")}
        className={`relative h-full w-full rounded-[1.4rem] border-2 border-dashed flex flex-col items-center justify-center transition-all duration-300 backdrop-blur-xl bg-surface cursor-pointer
          ${isDragging ? "border-blue-400 bg-white/10" : "border-white/20 hover:border-white/40"}`}
      >
        <motion.div 
          animate={{ y: isDragging ? -10 : 0, scale: isDragging ? 1.1 : 1 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <UploadCloud className={`w-24 h-24 mb-6 transition-colors duration-300 ${isDragging ? "text-blue-400" : "text-gray-400"}`} />
        </motion.div>
        
        <h2 className="text-3xl font-light tracking-wide text-white mb-2">
          Kéo thả thư mục ảnh vào đây
        </h2>
        <p className="text-gray-400 tracking-wider text-sm">
          AI sẽ tự động quét, gom nhóm và chọn ra những khoảnh khắc hoàn hảo nhất.
        </p>
      </div>
    </motion.div>
  );
}
