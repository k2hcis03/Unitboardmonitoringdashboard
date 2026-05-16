import { useState, useEffect } from 'react';
import { StatusMonitoringCard } from './components/StatusMonitoringCard';
import { GPIOControlPanel } from './components/GPIOControlPanel';
import { FunctionButtonPanel } from './components/FunctionButtonPanel';
import { DashboardPanel } from './components/DashboardPanel';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { getTankIdForUnit } from './config';
import { apiClient } from './services/api';

interface UnitControlState {
  gpioStates: boolean[];
  motorOn: boolean;
  motorSpeed: number;
  motorTime: number;
}

const DEFAULT_UNIT_STATE: UnitControlState = {
  gpioStates: Array(8).fill(false),
  motorOn: false,
  motorSpeed: 0,
  motorTime: 0,
};

export default function App() {
  // 유닛보드 ID (기본값: 0)
  const [selectedUnitId, setSelectedUnitId] = useState<number>(0);

  // View Mode: 'control' or 'dashboard'
  const [viewMode, setViewMode] = useState<'control' | 'dashboard'>('control');

  // Dashboard State (Lifted Up)
  const [dashboardTempSelection, setDashboardTempSelection] = useState<boolean[]>(
    Array(8).fill(true)
  );

  // 유닛별 GPIO/모터 상태 캐시: { [unitId]: UnitControlState }
  const [unitStates, setUnitStates] = useState<Record<number, UnitControlState>>({});

  const [zoomLevel, setZoomLevel] = useState(100);

  // 현재 선택된 유닛의 상태 (캐시에 없으면 기본값)
  const currentState: UnitControlState = unitStates[selectedUnitId] ?? DEFAULT_UNIT_STATE;
  const { gpioStates, motorOn, motorSpeed, motorTime } = currentState;

  // 현재 유닛 상태 업데이트 헬퍼
  const updateCurrentUnit = (updates: Partial<UnitControlState>) => {
    setUnitStates(prev => ({
      ...prev,
      [selectedUnitId]: { ...(prev[selectedUnitId] ?? DEFAULT_UNIT_STATE), ...updates },
    }));
  };

  // 유닛 변경 시: 캐시에 없으면 기본값으로 초기화하고 백엔드에서 실제 상태 조회
  useEffect(() => {
    const unitId = selectedUnitId;

    setUnitStates(prev => {
      if (prev[unitId] !== undefined) {
        return prev; // 이미 캐시된 상태 — 그대로 복원
      }

      // 첫 방문: 기본값으로 초기화하고 비동기로 백엔드 조회
      apiClient.getGPIOState(unitId)
        .then(data => {
          if (Array.isArray(data.gpio_states) && data.gpio_states.length === 8) {
            setUnitStates(current => ({
              ...current,
              [unitId]: {
                ...(current[unitId] ?? DEFAULT_UNIT_STATE),
                gpioStates: data.gpio_states,
              },
            }));
          }
        })
        .catch(() => {});

      return { ...prev, [unitId]: { ...DEFAULT_UNIT_STATE } };
    });
  }, [selectedUnitId]);

  const toggleGPIO = async (index: number) => {
    const newStates = [...gpioStates];
    newStates[index] = !newStates[index];
    updateCurrentUnit({ gpioStates: newStates });

    const mappedUnitId = getTankIdForUnit(selectedUnitId);
    try {
      await apiClient.controlGPIOBulk({
        unit_id: mappedUnitId,
        gpio_states: newStates,
      });

      console.log('GPIO 상태가 백엔드로 전송되었습니다:', {
        unit_id: mappedUnitId,
        gpio_states: newStates,
      });
    } catch (error) {
      console.error('GPIO 제어 실패:', error);
      // 에러 발생 시 이전 상태로 복원
      updateCurrentUnit({ gpioStates });
    }
  };

  // 모터 속도/시간 변경은 UI 상태만 업데이트 (ON/OFF 토글 시에만 백엔드로 전송)
  const handleMotorSpeedChange = (speed: number) => {
    updateCurrentUnit({ motorSpeed: speed });
  };

  const handleMotorTimeChange = (time: number) => {
    updateCurrentUnit({ motorTime: time });
  };

  const handleMotorToggle = async (isOn: boolean) => {
    const sendTime = isOn ? motorTime : 0;
    updateCurrentUnit({
      motorOn: isOn,
      ...(isOn ? {} : { motorTime: 0 }),
    });

    const mappedUnitId = getTankIdForUnit(selectedUnitId);
    try {
      await apiClient.controlMotor({
        unit_id: mappedUnitId,
        is_on: isOn,
        speed: motorSpeed,
        time: sendTime,
      });

      console.log('모터 상태가 백엔드로 전송되었습니다:', {
        unit_id: mappedUnitId,
        is_on: isOn,
        speed: motorSpeed,
        time: sendTime,
      });
    } catch (error) {
      console.error('모터 제어 실패:', error);
      // 에러 발생 시 이전 상태로 복원
      updateCurrentUnit({ motorOn: !isOn });
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

                {/* GPIO & Motor Control Panel - 유닛별 상태 복원 */}
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
