import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Dropzone from './components/Dropzone';
import Processing from './components/Processing';
import ReviewScreen from './components/ReviewScreen';
import ActionScreen from './components/ActionScreen';
import './App.css';

// Định nghĩa các trạng thái của ứng dụng
type AppState = 'IDLE' | 'PROCESSING' | 'REVIEWING' | 'COMPLETED';

function App() {
  const [appState, setAppState] = useState<AppState>('IDLE');
  const [currentPath, setCurrentPath] = useState("");
  const [totalSelected, setTotalSelected] = useState(0);
  const [totalScanned, setTotalScanned] = useState(0);
  const [rawExtension, setRawExtension] = useState("RAW");

  const handleStartScan = (path: string) => {
    setCurrentPath(path);
    setTotalSelected(0);
    setTotalScanned(0);
    setRawExtension("RAW");
    setAppState('PROCESSING');
  };

  const handleScanComplete = (selected: number, scanned: number, extension?: string) => {
    setTotalSelected(selected);
    setTotalScanned(scanned);
    if (extension) setRawExtension(extension);
    setAppState('REVIEWING'); // Chuyển sang màn Review thay vì COMPLETED
  };

  const handleReviewConfirm = () => {
    setAppState('COMPLETED');
  };

  const handleReset = () => {
    setAppState('IDLE');
    setCurrentPath("");
    setTotalSelected(0);
    setTotalScanned(0);
  };

  return (
    <main className="min-h-screen w-full flex items-center justify-center p-8 bg-background relative overflow-hidden">

      {/* Hiệu ứng ánh sáng nền tổng thể của App */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-900/10 blur-[120px] rounded-full pointer-events-none" />

      {/* Cơ chế chuyển cảnh mượt mà */}
      <AnimatePresence mode="wait">
        {appState === 'IDLE' && (
          <Dropzone key="dropzone" onDrop={handleStartScan} />
        )}

        {appState === 'PROCESSING' && (
          <Processing 
            key="processing" 
            sourceFolder={currentPath}
            onComplete={handleScanComplete} 
          />
        )}

        {appState === 'REVIEWING' && (
          <ReviewScreen
            key="reviewing"
            folderPath={currentPath}
            onConfirm={handleReviewConfirm}
          />
        )}

        {appState === 'COMPLETED' && (
          <ActionScreen
            key="completed"
            sourceFolder={currentPath}
            totalSelected={totalSelected}
            totalScanned={totalScanned}
            rawExtension={rawExtension}
            onReset={handleReset}
          />
        )}
      </AnimatePresence>

    </main>
  );
}

export default App;
