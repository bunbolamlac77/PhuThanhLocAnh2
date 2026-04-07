import { motion } from 'framer-motion';
import { Pause, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ProcessingProps {
  onComplete: () => void;
}

export default function Processing({ onComplete }: ProcessingProps) {
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState("Đang chuẩn bị dữ liệu...");

  useEffect(() => {
    // Mở kết nối WebSocket tới Backend Python
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/progress");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setProgress(data.progress || 0);
        
        if (data.current_file) {
          setCurrentFile(data.current_file);
        }

        if (data.status === "completed" || data.progress === 100) {
          setTimeout(onComplete, 800); // Chuyển màn hình khi xong
        }
      } catch (err) {
        console.error("Lỗi parse WS:", err);
      }
    };

    return () => {
      ws.close(); // Đóng kết nối khi component bị unmount
    };
  }, [onComplete]);

  const radius = 120;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, filter: "blur(10px)" }} className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center mb-12">
        <svg className="w-80 h-80 transform -rotate-90">
          <circle cx="160" cy="160" r={radius} stroke="rgba(255,255,255,0.05)" strokeWidth="4" fill="transparent" />
          <motion.circle 
            cx="160" cy="160" r={radius} stroke="#3b82f6" strokeWidth="6" fill="transparent" strokeLinecap="round"
            strokeDasharray={circumference} animate={{ strokeDashoffset }} transition={{ duration: 0.2 }}
            style={{ filter: "drop-shadow(0 0 12px rgba(59,130,246,0.8))" }}
          />
        </svg>

        <div className="absolute flex flex-col items-center">
          <motion.span className="text-6xl font-extralight tracking-tighter text-white">
            {progress}<span className="text-3xl text-gray-500">%</span>
          </motion.span>
          <span className="text-xs text-blue-400 mt-2 uppercase tracking-[0.2em] max-w-[150px] truncate text-center">
            {currentFile}
          </span>
        </div>
      </div>

      <div className="flex gap-6">
        <button className="flex items-center gap-2 px-6 py-3 rounded-full bg-white/5 border border-white/10 text-white hover:bg-white/10 backdrop-blur-md">
          <Pause size={18} /> <span className="text-sm font-medium">Tạm dừng</span>
        </button>
        <button className="flex items-center gap-2 px-6 py-3 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 backdrop-blur-md">
          <Square size={18} fill="currentColor" /> <span className="text-sm font-medium">Hủy bỏ</span>
        </button>
      </div>
    </motion.div>
  );
}
