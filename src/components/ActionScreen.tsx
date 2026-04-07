import { motion } from 'framer-motion';
import { Copy, FolderInput, CheckCircle2 } from 'lucide-react';

interface ActionScreenProps {
  onReset: () => void;
}

export default function ActionScreen({ onReset }: ActionScreenProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="flex flex-col items-center justify-center max-w-4xl w-full"
    >
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="flex flex-col items-center mb-16"
      >
        <CheckCircle2 className="w-20 h-20 text-green-400 mb-6 drop-shadow-[0_0_15px_rgba(74,222,128,0.5)]" />
        <h2 className="text-4xl font-light text-white mb-3 tracking-wide">Phân tích Hoàn tất</h2>
        <p className="text-xl text-gray-400 font-light">Đã chọn ra <span className="text-white font-medium">350 / 1200</span> khoảnh khắc đẹp nhất.</p>
      </motion.div>

      <div className="flex gap-8 w-full px-12">
        {/* Nút Copy */}
        <motion.button 
          whileHover={{ scale: 1.02, y: -5 }}
          whileTap={{ scale: 0.98 }}
          className="flex-1 group relative p-[2px] rounded-3xl bg-gradient-to-b from-blue-500/50 to-transparent overflow-hidden"
        >
          {/* Hiệu ứng Gợn sóng (Ripple) khi Hover */}
          <motion.div 
            initial={{ opacity: 0, scale: 0 }}
            whileHover={{ opacity: 0.4, scale: 1.5 }}
            transition={{ duration: 1, repeat: Infinity }}
            className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full"
          />
          <div className="absolute inset-0 bg-blue-500/20 blur-xl group-hover:bg-blue-500/30 transition-all"></div>
          <div className="relative h-full w-full bg-background/90 backdrop-blur-xl rounded-[1.4rem] p-10 flex flex-col items-center border border-white/5 group-hover:border-blue-500/30 transition-colors">
            <Copy className="w-16 h-16 text-blue-400 mb-6 group-hover:scale-110 transition-transform duration-500" />
            <h3 className="text-2xl font-medium text-white mb-2 tracking-wide">COPY ẢNH</h3>
            <p className="text-sm text-gray-400 text-center">Sao chép file RAW sang thư mục mới, giữ nguyên file gốc.</p>
          </div>
        </motion.button>

        {/* Nút Move */}
        <motion.button 
          whileHover={{ scale: 1.02, y: -5 }}
          whileTap={{ scale: 0.98 }}
          className="flex-1 group relative p-[2px] rounded-3xl bg-gradient-to-b from-purple-500/50 to-transparent overflow-hidden"
        >
          {/* Hiệu ứng Gợn sóng (Ripple) khi Hover */}
          <motion.div 
            initial={{ opacity: 0, scale: 0 }}
            whileHover={{ opacity: 0.4, scale: 1.5 }}
            transition={{ duration: 1, repeat: Infinity }}
            className="absolute inset-0 bg-purple-500/20 blur-2xl rounded-full"
          />
          <div className="absolute inset-0 bg-purple-500/20 blur-xl group-hover:bg-purple-500/30 transition-all"></div>
          <div className="relative h-full w-full bg-background/90 backdrop-blur-xl rounded-[1.4rem] p-10 flex flex-col items-center border border-white/5 group-hover:border-purple-500/30 transition-colors">
            <FolderInput className="w-16 h-16 text-purple-400 mb-6 group-hover:scale-110 transition-transform duration-500" />
            <h3 className="text-2xl font-medium text-white mb-2 tracking-wide">MOVE ẢNH</h3>
            <p className="text-sm text-gray-400 text-center">Di chuyển thẳng file RAW để tiết kiệm dung lượng ổ cứng.</p>
          </div>
        </motion.button>
      </div>

      <button onClick={onReset} className="mt-16 text-sm text-gray-500 hover:text-white transition-colors underline underline-offset-4 decoration-white/20">
        Lọc thư mục khác
      </button>
    </motion.div>
  );
}
