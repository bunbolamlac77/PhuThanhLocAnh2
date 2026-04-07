import { motion } from 'framer-motion';
import { Pause, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ProcessingProps {
  onComplete: () => void;
}

export default function Processing({ onComplete }: ProcessingProps) {
  // Giả lập tiến trình chạy % để test UI
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 800); // Đợi 0.8s rồi chuyển màn hình
          return 100;
        }
        return p + 1;
      });
    }, 50); // Tốc độ chạy giả lập
    return () => clearInterval(interval);
  }, [onComplete]);

  // Toán học cho SVG Circle
  const radius = 120;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, filter: "blur(10px)" }}
      className="flex flex-col items-center justify-center"
    >
      {/* Vòng tròn Progress */}
      <div className="relative flex items-center justify-center mb-12">
        {/* Vòng nền mờ */}
        <svg className="w-80 h-80 transform -rotate-90">
          <circle 
            cx="160" cy="160" r={radius} 
            stroke="rgba(255,255,255,0.05)" 
            strokeWidth="4" fill="transparent" 
          />
          {/* Vòng tiến trình phát sáng */}
          <motion.circle 
            cx="160" cy="160" r={radius}
            stroke="#3b82f6" 
            strokeWidth="6" 
            fill="transparent"
            strokeLinecap="round"
            strokeDasharray={circumference}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.1, ease: "linear" }}
            style={{ filter: "drop-shadow(0 0 12px rgba(59,130,246,0.8))" }}
          />
        </svg>

        {/* Số % ở giữa */}
        <div className="absolute flex flex-col items-center">
          <motion.span 
            className="text-6xl font-extralight tracking-tighter text-white"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          >
            {progress}<span className="text-3xl text-gray-500">%</span>
          </motion.span>
          <span className="text-xs text-blue-400 mt-2 uppercase tracking-[0.3em]">Đang phân tích</span>
        </div>
      </div>

      {/* Nút điều khiển Tối giản */}
      <div className="flex gap-6">
        <button className="flex items-center gap-2 px-6 py-3 rounded-full bg-white/5 border border-white/10 text-white hover:bg-white/10 hover:border-white/30 transition-all backdrop-blur-md">
          <Pause size={18} /> <span className="text-sm font-medium tracking-wide">Tạm dừng</span>
        </button>
        <button className="flex items-center gap-2 px-6 py-3 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-all backdrop-blur-md">
          <Square size={18} fill="currentColor" /> <span className="text-sm font-medium tracking-wide">Hủy bỏ</span>
        </button>
      </div>
    </motion.div>
  );
}
