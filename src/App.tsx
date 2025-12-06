import { useState, useRef, useEffect } from 'react';
import { StatusMonitoringCard } from './components/StatusMonitoringCard';
import { GPIOControlPanel } from './components/GPIOControlPanel';
import { FunctionButtonPanel } from './components/FunctionButtonPanel';
import { DashboardPanel } from './components/DashboardPanel';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { apiClient } from './services/api';

export default function App() {
  // 유닛보드 ID (기본값: 0)
  const [selectedUnitId, setSelectedUnitId] = useState<number>(0);
  
  // View Mode: 'control' or 'dashboard'
  const [viewMode, setViewMode] = useState<'control' | 'dashboard'>('control');

  // Dashboard State (Lifted Up)
  const [dashboardTempSelection, setDashboardTempSelection] = useState<boolean[]>(
    Array(8).fill(true)
  );

  // GPIO 제어 패널용 독립적인 상태
  const [gpioStates, setGpioStates] = useState<boolean[]>(
    Array(8).fill(false)
  );
  const [motorOn, setMotorOn] = useState(false);
  const [motorSpeed, setMotorSpeed] = useState(0); // RPM 단위로 변경
  const [motorTime, setMotorTime] = useState(0); // s 단위
  const [zoomLevel, setZoomLevel] = useState(100);

  const toggleGPIO = async (index: number) => {
    const newStates = [...gpioStates];
    newStates[index] = !newStates[index];
    setGpioStates(newStates);
    
    // GPIO 변경 시 모든 GPIO 상태를 JSON으로 백엔드로 전송
    try {
      await apiClient.controlGPIOBulk({
        unit_id: selectedUnitId,
        gpio_states: newStates,
      });
      
      console.log('GPIO 상태가 백엔드로 전송되었습니다:', {
        unit_id: selectedUnitId,
        gpio_states: newStates,
      });
    } catch (error) {
      console.error('GPIO 제어 실패:', error);
      // 에러 발생 시 이전 상태로 복원
      setGpioStates([...gpioStates]);
    }
  };

  // 모터 속도 변경 디바운싱을 위한 ref
  const motorSpeedTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const motorTimeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMotorSpeedChange = async (speed: number) => {
    setMotorSpeed(speed);
    
    // 이전 타이머가 있으면 취소
    if (motorSpeedTimeoutRef.current) {
      clearTimeout(motorSpeedTimeoutRef.current);
    }
    
    // 300ms 후에 백엔드로 전송 (슬라이더 드래그 중 과도한 요청 방지)
    motorSpeedTimeoutRef.current = setTimeout(async () => {
      try {
        await apiClient.controlMotor({
          unit_id: selectedUnitId,
          is_on: motorOn,
          speed: speed,
        });
        
        console.log('모터 속도가 백엔드로 전송되었습니다:', {
          unit_id: selectedUnitId,
          is_on: motorOn,
          speed: speed,
        });
      } catch (error) {
        console.error('모터 속도 제어 실패:', error);
        // 에러 발생 시 이전 속도로 복원
        setMotorSpeed(motorSpeed);
      }
    }, 300);
  };

  const handleMotorTimeChange = async (time: number) => {
    setMotorTime(time);
    
    // 이전 타이머가 있으면 취소
    if (motorTimeTimeoutRef.current) {
      clearTimeout(motorTimeTimeoutRef.current);
    }
    
    // 300ms 후에 백엔드로 전송
    motorTimeTimeoutRef.current = setTimeout(async () => {
      try {
        await apiClient.controlMotor({
          unit_id: selectedUnitId,
          is_on: motorOn,
          speed: motorSpeed,
          time: time,
        });
        
        console.log('모터 시간이 백엔드로 전송되었습니다:', {
          unit_id: selectedUnitId,
          is_on: motorOn,
          speed: motorSpeed,
          time: time,
        });
      } catch (error) {
        console.error('모터 시간 제어 실패:', error);
        // 에러 발생 시 이전 시간으로 복원 (optional)
        setMotorTime(motorTime);
      }
    }, 300);
  };

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (motorSpeedTimeoutRef.current) {
        clearTimeout(motorSpeedTimeoutRef.current);
      }
      if (motorTimeTimeoutRef.current) {
        clearTimeout(motorTimeTimeoutRef.current);
      }
    };
  }, []);

  // 초기 로드 시 유닛 1(index 0)에 대한 펌웨어 버전 요청
  useEffect(() => {
    // 백엔드에 초기 유닛 선택 이벤트를 전송하여 펌웨어 버전 정보를 요청하도록 함
    // FunctionButtonPanel에서도 WebSocket을 통해 UNIT_SELECT를 보내지만,
    // 여기서 명시적으로 한 번 더 보내거나, 백엔드가 연결 시점에 기본값으로 처리하도록 유도
    // WebSocket 연결이 수립된 후 보내야 하므로 약간의 지연을 주거나,
    // WebSocketContext에서 연결 상태를 가져와서 처리하는 것이 좋음.
    // 하지만 여기서는 간단하게 타임아웃으로 처리하거나, 
    // FunctionButtonPanel 내부에서 처리하도록 하는 것이 나을 수 있음.
    // 사용자의 요청: "프론트엔드가 처음 실행 될 때... set_selected_unit_id(self, unit_id: int):함수가 한번 호출되어서"
    
    // 이 부분은 FunctionButtonPanel 컴포넌트 내부에서 처리하는 것이 더 적절할 수 있음.
    // App.tsx는 전체 레이아웃을 담당하므로.
  }, []);

  const handleMotorToggle = async (isOn: boolean) => {
    setMotorOn(isOn);
    
    // 모터 ON/OFF 토글 시 백엔드로 전송
    try {
      await apiClient.controlMotor({
        unit_id: selectedUnitId,
        is_on: isOn,
        speed: motorSpeed,
        time: motorTime,
      });
      
      console.log('모터 상태가 백엔드로 전송되었습니다:', {
        unit_id: selectedUnitId,
        is_on: isOn,
        speed: motorSpeed,
        time: motorTime,
      });
    } catch (error) {
      console.error('모터 제어 실패:', error);
      // 에러 발생 시 이전 상태로 복원
      setMotorOn(!isOn);
    }
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
          {/* Left Column - Monitoring & Control OR Dashboard */}
          <div className="flex flex-col gap-6">
            {viewMode === 'control' ? (
              <>
                {/* Status Monitoring Card - 독립적인 상태 표시 */}
                <StatusMonitoringCard selectedUnitId={selectedUnitId} />

                {/* GPIO & Motor Control Panel - 독립적인 제어 */}
                <GPIOControlPanel
                  gpioStates={gpioStates}
                  toggleGPIO={toggleGPIO}
                  motorOn={motorOn}
                  setMotorOn={handleMotorToggle}
                  motorSpeed={motorSpeed}
                  setMotorSpeed={handleMotorSpeedChange}
                  motorTime={motorTime}
                  setMotorTime={handleMotorTimeChange}
                />
              </>
            ) : (
              <DashboardPanel 
                selectedUnitId={selectedUnitId} 
                tempSelection={dashboardTempSelection}
                onTempSelectionChange={setDashboardTempSelection}
              />
            )}
          </div>

          {/* Right Column - Function Buttons */}
          <FunctionButtonPanel 
            selectedUnitId={selectedUnitId}
            onUnitIdChange={setSelectedUnitId}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>
      </div>
    </div>
  );
}