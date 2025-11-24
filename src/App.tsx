import { useState } from 'react';
import { StatusMonitoringCard } from './components/StatusMonitoringCard';
import { GPIOControlPanel } from './components/GPIOControlPanel';
import { FunctionButtonPanel } from './components/FunctionButtonPanel';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export default function App() {
  // GPIO 제어 패널용 독립적인 상태
  const [gpioStates, setGpioStates] = useState<boolean[]>(
    Array(8).fill(false)
  );
  const [motorOn, setMotorOn] = useState(false);
  const [motorSpeed, setMotorSpeed] = useState(0); // RPM 단위로 변경
  const [zoomLevel, setZoomLevel] = useState(100);

  const toggleGPIO = (index: number) => {
    const newStates = [...gpioStates];
    newStates[index] = !newStates[index];
    setGpioStates(newStates);
  };

  const adjustZoom = (delta: number) => {
    setZoomLevel(prev => Math.min(Math.max(prev + delta, 75), 150));
  };

  const resetZoom = () => {
    setZoomLevel(100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div 
        className="max-w-[1440px] mx-auto transition-transform duration-300"
        style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }}
      >
        {/* Header */}
        <header className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-[#0A4D68]">유닛보드 상태 모니터링 & 제어 시스템</h1>
            <p className="text-slate-600 mt-2">Industrial Brewing & Fermentation Equipment Dashboard</p>
          </div>
          
          {/* Zoom Controls */}
          <div className="flex items-center gap-2 bg-white rounded-xl shadow-md border border-slate-200 p-2">
            <button
              onClick={() => adjustZoom(-10)}
              disabled={zoomLevel <= 75}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="축소"
            >
              <ZoomOut className="w-5 h-5 text-[#0A4D68]" />
            </button>
            
            <button
              onClick={resetZoom}
              className="px-3 py-2 hover:bg-slate-100 rounded-lg transition-colors min-w-[60px]"
              title="기본 크기"
            >
              <span className="text-[#0A4D68] tabular-nums">{zoomLevel}%</span>
            </button>
            
            <button
              onClick={() => adjustZoom(10)}
              disabled={zoomLevel >= 150}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="확대"
            >
              <ZoomIn className="w-5 h-5 text-[#0A4D68]" />
            </button>
            
            <div className="w-px h-6 bg-slate-300 mx-1"></div>
            
            <button
              onClick={resetZoom}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="전체 화면"
            >
              <Maximize2 className="w-5 h-5 text-[#0A4D68]" />
            </button>
          </div>
        </header>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-[1fr_320px] gap-6">
          {/* Left Column - Monitoring & Control */}
          <div className="flex flex-col gap-6">
            {/* Status Monitoring Card - 독립적인 상태 표시 */}
            <StatusMonitoringCard />

            {/* GPIO & Motor Control Panel - 독립적인 제어 */}
            <GPIOControlPanel
              gpioStates={gpioStates}
              toggleGPIO={toggleGPIO}
              motorOn={motorOn}
              setMotorOn={setMotorOn}
              motorSpeed={motorSpeed}
              setMotorSpeed={setMotorSpeed}
            />
          </div>

          {/* Right Column - Function Buttons */}
          <FunctionButtonPanel />
        </div>
      </div>
    </div>
  );
}