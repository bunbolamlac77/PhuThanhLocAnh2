import { motion } from 'framer-motion';
import { Copy, FolderInput, CheckCircle2 } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';
import { useState } from 'react';

interface ActionScreenProps {
  sourceFolder: string;
  totalSelected: number;
  totalScanned: number;
  onReset: () => void;
}

export default function ActionScreen({ sourceFolder, totalSelected, totalScanned, onReset }: ActionScreenProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  // Lấy extension RAW từ folder (giả định folder đã được backend xử lý)
  // Thực tế backend đã ghi vào file txt, ở đây chỉ hiển thị cho đẹp
  const rawExt = "RAW"; 

  const handleExecute = async (actionType: 'copy' | 'move') => {
    try {
      const destination = await open({
        directory: true,
        multiple: false,
        title: `Chọn Thư mục đích để ${actionType === 'copy' ? 'sao chép' : 'di chuyển'} ảnh`
      });

      if (destination && typeof destination === 'string') {
        setIsProcessing(true);
        const res = await fetch("http://127.0.0.1:8000/execute-action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_folder: sourceFolder,
            destination_folder: destination,
            action_type: actionType
          })
        });
        
        const data = await res.json();
        setIsProcessing(false);
        
        if (data.status === "success") {
          alert(`Đã ${actionType === 'copy' ? 'sao chép' : 'di chuyển'} thành công ${data.processed} ảnh!`);
          onReset();
        } else {
          alert("Lỗi: " + data.message);
        }
      }
    } catch (err) {
      console.error(err);
      setIsProcessing(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, scale: 1.1 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center justify-center max-w-4xl w-full">
      <div className="flex flex-col items-center mb-12">
        <CheckCircle2 className="w-20 h-20 text-green-400 mb-6 drop-shadow-[0_0_15px_rgba(74,222,128,0.5)]" />
        <h2 className="text-5xl font-light text-white mb-4">Phân tích Hoàn tất</h2>
        
        <div className="flex flex-col items-center gap-2">
          <div className="px-6 py-2 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 font-bold text-2xl mb-2">
            ✅ {totalSelected} / {totalScanned} ảnh được chọn
          </div>
          <p className="text-gray-400 font-light italic">
            Danh sách đã được lưu tại thư mục nguồn.
          </p>
        </div>
      </div>

      <div className={`flex gap-8 w-full px-12 transition-all duration-500 ${isProcessing ? 'opacity-50 pointer-events-none scale-95' : 'opacity-100 scale-100'}`}>
        <motion.button onClick={() => handleExecute('copy')} whileHover={{ scale: 1.02 }} className="flex-1 group relative p-[2px] rounded-3xl overflow-hidden bg-gradient-to-b from-blue-500/50 to-transparent">
          <div className="relative h-full w-full bg-background/90 backdrop-blur-xl rounded-[1.4rem] p-10 flex flex-col items-center border border-white/5 group-hover:border-blue-500/30">
            <Copy className="w-16 h-16 text-blue-400 mb-6" />
            <h3 className="text-2xl font-medium text-white mb-2 uppercase tracking-wide">Copy FILE {rawExt}</h3>
            <p className="text-sm text-gray-400 text-center">Sao chép ảnh đã chọn sang thư mục mới.</p>
          </div>
        </motion.button>

        <motion.button onClick={() => handleExecute('move')} whileHover={{ scale: 1.02 }} className="flex-1 group relative p-[2px] rounded-3xl overflow-hidden bg-gradient-to-b from-purple-500/50 to-transparent">
          <div className="relative h-full w-full bg-background/90 backdrop-blur-xl rounded-[1.4rem] p-10 flex flex-col items-center border border-white/5 group-hover:border-purple-500/30">
            <FolderInput className="w-16 h-16 text-purple-400 mb-6" />
            <h3 className="text-2xl font-medium text-white mb-2 uppercase tracking-wide">Move FILE {rawExt}</h3>
            <p className="text-sm text-gray-400 text-center">Di chuyển file trực tiếp (Dùng để dọn dẹp).</p>
          </div>
        </motion.button>
      </div>

      {!isProcessing && (
        <button onClick={onReset} className="mt-16 text-sm text-gray-500 hover:text-white transition-colors underline underline-offset-8 decoration-white/10 hover:decoration-white/40">
          Quay lại màn hình chính
        </button>
      )}
    </motion.div>
  );
}
