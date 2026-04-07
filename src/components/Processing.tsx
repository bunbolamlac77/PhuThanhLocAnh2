import { motion } from 'framer-motion';
import { Wifi, WifiOff } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ProcessingProps {
  sourceFolder: string;
  onComplete: (totalSelected: number, totalScanned: number) => void;
}

export default function Processing({ sourceFolder, onComplete }: ProcessingProps) {
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState("Đang kết nối tới AI engine...");
  const [totalFiles, setTotalFiles] = useState(0);
  const [processedFiles, setProcessedFiles] = useState(0);
  const [totalSelected, setTotalSelected] = useState(0);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'error' | 'cancelled'>('connecting');
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const handleStop = async () => {
    try {
      await fetch("http://127.0.0.1:8000/stop-scan", { method: "POST" });
      setWsStatus('cancelled');
      setCurrentFile("Tiến trình đã được dừng.");
    } catch (err) {
      console.error("Lỗi khi dừng scan:", err);
    }
  };

  useEffect(() => {
    let ws: WebSocket;
    let retryTimeout: ReturnType<typeof setTimeout>;
    let connectionTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket("ws://127.0.0.1:8000/ws/progress");

      connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          setWsStatus('error');
          setCurrentFile("Không thể kết nối backend. Hãy chắc chắn backend đang chạy.");
        }
      }, 5000);

      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        setWsStatus('connected');
        setCurrentFile("Đang phân tích ảnh...");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgress(data.progress || 0);

          if (data.total_files) setTotalFiles(data.total_files);
          if (data.total_selected !== undefined) setTotalSelected(data.total_selected);
          
          if (data.progress) {
            setProcessedFiles(Math.round((data.progress / 100) * (data.total_files || 100)));
          }

          if (data.current_file) {
            setCurrentFile(data.current_file);
          }

          if (data.status === "completed" || data.progress >= 100) {
            setTimeout(() => {
              onCompleteRef.current(data.total_selected || 0, data.total_files || 0);
            }, 1000);
          }

          if (data.status === "cancelled") {
            setWsStatus('cancelled');
          }
        } catch (err) {
          console.error("Lỗi parse WS:", err);
        }
      };

      ws.onerror = () => {
        clearTimeout(connectionTimeout);
        if (wsStatus !== 'cancelled') {
          setWsStatus('error');
          setCurrentFile("Lỗi kết nối. Đang thử lại...");
          retryTimeout = setTimeout(connect, 3000);
        }
      };

      ws.onclose = () => {
        clearTimeout(connectionTimeout);
        if (wsStatus !== 'error' && wsStatus !== 'cancelled') {
          setWsStatus('connecting');
        }
      };
    };

    connect();

    return () => {
      clearTimeout(connectionTimeout);
      clearTimeout(retryTimeout);
      if (ws) ws.close();
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

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
      {/* Vòng tròn tiến độ */}
      <div className="relative flex items-center justify-center mb-10">
        <svg className="w-80 h-80 transform -rotate-90">
          <circle cx="160" cy="160" r={radius} stroke="rgba(255,255,255,0.05)" strokeWidth="4" fill="transparent" />
          <motion.circle
            cx="160" cy="160" r={radius} stroke="#3b82f6" strokeWidth="6" fill="transparent" strokeLinecap="round"
            strokeDasharray={circumference}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            style={{ filter: "drop-shadow(0 0 12px rgba(59,130,246,0.8))" }}
          />
        </svg>

        <div className="absolute flex flex-col items-center gap-1">
          <motion.span
            key={progress}
            initial={{ scale: 0.9, opacity: 0.5 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-6xl font-extralight tracking-tighter text-white"
          >
            {progress}<span className="text-3xl text-gray-500">%</span>
          </motion.span>

          {totalFiles > 0 && (
            <span className="text-xs text-gray-500 font-light">
              Đã xong {processedFiles} / {totalFiles} ảnh
            </span>
          )}

          {totalSelected > 0 && (
            <span className="text-sm text-green-400 font-bold mt-1">
              {totalSelected} ảnh được chọn
            </span>
          )}

          <span className="text-xs text-blue-400 mt-2 uppercase tracking-[0.2em] max-w-[200px] truncate text-center px-4">
            {currentFile}
          </span>
          
          <div className="text-[10px] text-gray-600 mt-4 max-w-[250px] truncate opacity-50 px-4">
             {sourceFolder}
          </div>
        </div>
      </div>

      {/* Trạng thái kết nối WS */}
      <div className="flex items-center gap-2 mb-8 text-xs">
        {wsStatus === 'connected' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1.5 text-green-400"
          >
            <Wifi size={12} />
            <span>Đang phân tích thời gian thực</span>
          </motion.div>
        )}
        {wsStatus === 'connecting' && (
          <div className="flex items-center gap-1.5 text-yellow-500">
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            >
              <Wifi size={12} />
            </motion.div>
            <span>Đang kết nối...</span>
          </div>
        )}
        {wsStatus === 'error' && (
          <div className="flex items-center gap-1.5 text-red-400">
            <WifiOff size={12} />
            <span>Mất kết nối – đang thử lại</span>
          </div>
        )}
        {wsStatus === 'cancelled' && (
          <div className="flex items-center gap-1.5 text-red-400">
            <WifiOff size={12} />
            <span>Tiến trình đã hủy</span>
          </div>
        )}
      </div>

      {/* Thanh progress phụ & Nút điều khiển */}
      <div className="flex flex-col items-center gap-8">
        <div className="w-72 h-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          />
        </div>

        <div className="flex gap-4">
          <button 
            disabled={wsStatus === 'cancelled'}
            className="px-6 py-2 rounded-xl bg-white/5 border border-white/10 text-gray-400 text-sm hover:bg-white/10 transition-all disabled:opacity-50"
            onClick={() => alert("Chức năng Tạm dừng đang được phát triển. Sử dụng Hủy để dừng hẳn.")}
          >
            Tạm dừng
          </button>
          <button 
            onClick={handleStop}
            disabled={wsStatus === 'cancelled'}
            className="px-6 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm hover:bg-red-500/20 transition-all disabled:opacity-50"
          >
            Hủy bỏ
          </button>
        </div>
      </div>
    </motion.div>
  );
}

