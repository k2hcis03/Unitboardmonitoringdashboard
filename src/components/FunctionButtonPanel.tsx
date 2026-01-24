import { Cpu, BookOpen, Play, Pause, Square, Download, LayoutDashboard, Settings2, Clock } from 'lucide-react';
import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

import { apiClient } from '../services/api';

// 초를 시:분:초 형식으로 변환하는 헬퍼 함수
const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

interface FunctionButtonPanelProps {
  selectedUnitId: number;
  onUnitIdChange: (unitId: number) => void;
  viewMode?: 'control' | 'dashboard';
  onViewModeChange?: (mode: 'control' | 'dashboard') => void;
}

export function FunctionButtonPanel({ 
  selectedUnitId, 
  onUnitIdChange,
  viewMode = 'control',
  onViewModeChange
}: FunctionButtonPanelProps) {
  const [showUnitSelector, setShowUnitSelector] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<string | null>(null);
  const [selectedFirmware, setSelectedFirmware] = useState<string | null>(null);
  
  const { lastMessage, sendMessage } = useWebSocket();
  const [isPiConnected, setIsPiConnected] = useState(false);
  const [firmwareVersion, setFirmwareVersion] = useState<string>('v0.0.0');
  const [isRecording, setIsRecording] = useState(false);

  // 레시피 타이머 관련 상태
  const [remainingTime, setRemainingTime] = useState<number>(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // 프로그램 시작 시 항상 '레시피 시작' 상태로 시작
  // 서버 상태와 관계없이 isRecording은 false로 유지
  
  // 레시피 타이머 useEffect
  useEffect(() => {
    if (isTimerRunning && remainingTime > 0) {
      timerRef.current = setInterval(() => {
        setRemainingTime((prev) => {
          if (prev <= 1) {
            // 타이머 종료
            setIsTimerRunning(false);
            if (timerRef.current) {
              clearInterval(timerRef.current);
              timerRef.current = null;
            }
            alert('현재 레시피가 끝났습니다');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isTimerRunning]);

  useEffect(() => {
    if (lastMessage?.type === 'SYSTEM_CONNECTION_STATUS') {
      setIsPiConnected(lastMessage?.data?.connected);
    }
    
    if (lastMessage?.type === 'ACK_INITIALIZE_RECEIVED') {
      const data = lastMessage.data;
      if (data && data.FW_VERSION) {
         // FW_VERSION 값을 숫자로 변환 후 100으로 나누어 소수점 2자리까지 표시 (v 접두어 포함)
         const versionNum = parseFloat(data.FW_VERSION);
         if (!isNaN(versionNum)) {
           setFirmwareVersion(`v${(versionNum / 100).toFixed(2)}`);
         } else {
           setFirmwareVersion(data.FW_VERSION); // 숫자가 아니면 그대로 표시
         }
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    // 초기 로드 시 유닛 1(index 0)에 대한 펌웨어 버전 요청을 위해 UNIT_SELECT 메시지 전송
    if (isPiConnected) {
        // 약간의 지연을 주어 연결 안정화 후 요청
        const timer = setTimeout(() => {
            handleUnitSelect(selectedUnitId + 1);
        }, 500);
        return () => clearTimeout(timer);
    }
  }, [isPiConnected, selectedUnitId]);

  const handleUnitSelect = (unitNumber: number) => {
    const unitId = unitNumber - 1;
    onUnitIdChange(unitId); // 1-32를 0-31로 변환
    
    // Send selection to backend via WebSocket
    sendMessage({
      type: 'UNIT_SELECT',
      unit_id: unitId
    });
    
    setShowUnitSelector(false);
  };

  const handleRecipeFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      // 파일 읽기
      const fileContent = await file.text();
      
      // JSON 파싱
      let recipeData;
      try {
        recipeData = JSON.parse(fileContent);
      } catch (parseError) {
        alert('유효하지 않은 JSON 파일입니다.');
        setSelectedRecipe(null);
        event.target.value = '';
        return;
      }

      // 레시피 데이터 검증 (CMD가 REF인지 확인)
      if (recipeData.CMD !== 'REF') {
        alert('유효하지 않은 레시피 파일입니다. CMD가 "REF"여야 합니다.');
        setSelectedRecipe(null);
        event.target.value = '';
        return;
      }

      // 레시피 데이터를 라즈베리파이로 전송
      const result = await apiClient.sendRecipe(recipeData);
      
      if (result.success) {
        // 전송 성공 시에만 파일명 저장
        setSelectedRecipe(file.name);
        
        // 전체 시간 계산: STEP * DATA 개수
        const step = parseInt(recipeData.STEP) || 0;
        const dataCount = Array.isArray(recipeData.DATA) ? recipeData.DATA.length : 0;
        const totalTime = step * dataCount;
        setRemainingTime(totalTime);
        setIsTimerRunning(false); // 타이머는 아직 시작하지 않음
        
        console.log(`Recipe ${file.name} sent successfully. Total time: ${totalTime} seconds (${formatTime(totalTime)})`);
        alert(`레시피 "${file.name}" 전송 완료\n예상 소요 시간: ${formatTime(totalTime)}`);
      } else {
        console.error('Failed to send recipe:', result.error);
        alert(`레시피 전송 실패: ${result.error || '알 수 없는 오류'}`);
        setSelectedRecipe(null);
        setRemainingTime(0);
      }
    } catch (error) {
      console.error('Failed to process recipe file:', error);
      alert('레시피 파일 처리 중 오류가 발생했습니다.');
      setSelectedRecipe(null);
    } finally {
      // 입력 초기화 (동일 파일 재선택 가능하게)
      event.target.value = '';
    }
  };

  const handleFirmwareSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFirmware(file.name);
      
      try {
        // 선택된 유닛보드 ID로 펌웨어 업데이트 요청 전송
        // 주의: 브라우저 환경에서는 보안상 전체 파일 경로(C:\path\to\file.bin)를 알 수 없습니다.
        // 하지만 사용자 요청에 따라 백엔드에 파일 처리를 위임하는 구조로 변경합니다.
        // 여기서는 파일명만 전송하지만, 실제로는 파일을 업로드하거나
        // 로컬 환경(Electron 등)이라면 전체 경로를 얻을 수 있습니다.
        // 현재 웹 브라우저 환경에서는 파일 객체를 통해 업로드하는 방식이 일반적입니다.
        
        // 하지만 사용자의 요청인 "선택된 파일 디렉토리 정보부터 파일이름까지 포함된 정보"를 충족하기 위해
        // 브라우저의 한계(fake path)를 설명하고, 대신 파일 자체를 업로드하는 방식을 유지하거나
        // 로컬 개발 환경에서 테스트용으로 특정 경로를 가정하는 방식 등으로 구현해야 합니다.
        
        // 여기서는 파일 이름을 그대로 보내되, 백엔드에서 이를 처리하도록 합니다.
        // 만약 Electron 등의 환경이라면 file.path로 전체 경로를 얻을 수 있습니다.
        
        // 웹 브라우저의 보안 정책으로 인해 실제 전체 경로(C:\...)는 JavaScript로 읽을 수 없습니다.
        // 따라서 파일 이름만이라도 정확히 전송합니다.
        console.log(`Firmware update request: Unit ${selectedUnitId}, File ${file.name}`);
        
        await apiClient.updateFirmware(selectedUnitId, file.name);
        
        console.log('Firmware update command sent successfully');
      } catch (error) {
        console.error('Failed to send firmware update command:', error);
        alert('펌웨어 업데이트 명령 전송에 실패했습니다.');
      }
      
      // 입력 초기화 (동일 파일 재선택 가능하게)
      event.target.value = '';
    }
  };

  const handleStartRecording = async () => {
    // 레시피가 선택되지 않은 경우 메시지 표시
    if (selectedRecipe === null) {
      alert('레시피를 선택하세요');
      return;
    }

    try {
      console.log('Starting recording...');
      const response = await apiClient.startRecording();
      if (response.is_recording) {
        setIsRecording(true);
        // 타이머 시작
        if (remainingTime > 0) {
          setIsTimerRunning(true);
        }
        console.log('Recording started');
      }
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('녹화 시작에 실패했습니다.');
    }
  };

  const handlePauseRecording = async () => {
    try {
      console.log('Pausing recording...');
      const response = await apiClient.pauseRecording();
      if (!response.is_recording) {
        setIsRecording(false);
        // 타이머 일시정지
        setIsTimerRunning(false);
        console.log('Recording paused');
      }
    } catch (error) {
      console.error('Failed to pause recording:', error);
      alert('일시정지에 실패했습니다.');
    }
  };

  const handleStopRecording = async () => {
    try {
      console.log('Stopping recording...');
      const response = await apiClient.stopRecording();
      if (!response.is_recording) {
        setIsRecording(false);
        // 타이머 종료 및 초기화
        setIsTimerRunning(false);
        setRemainingTime(0);
        setSelectedRecipe(null);
        console.log('Recording stopped');
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      alert('레시피 종료에 실패했습니다.');
    }
  };

  const buttons = [
    { 
      icon: Cpu, 
      label: '유닛보드 선택', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => setShowUnitSelector(!showUnitSelector),
      info: selectedUnitId !== null ? `유닛 ${selectedUnitId + 1}` : null,
      disabled: false
    },
    { 
      icon: BookOpen, 
      label: '레시피 선택', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => document.getElementById('recipe-file-input')?.click(),
      info: selectedRecipe,
      disabled: false
    },
    { 
      icon: isRecording ? Pause : Play, 
      label: isRecording ? '레시피 일시정지' : '레시피 시작', 
      color: 'from-emerald-600 to-emerald-500',
      onClick: isRecording ? handlePauseRecording : handleStartRecording,
      disabled: false,
      visuallyDisabled: !isRecording && selectedRecipe === null
    },
    { 
      icon: Square, 
      label: '레시피 종료', 
      color: 'from-rose-600 to-rose-500',
      onClick: handleStopRecording,
      disabled: false,
      visuallyDisabled: false
    },
    { 
      icon: viewMode === 'control' ? LayoutDashboard : Settings2, 
      label: viewMode === 'control' ? '대시보드' : '수동 제어', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => onViewModeChange && onViewModeChange(viewMode === 'control' ? 'dashboard' : 'control'),
      disabled: false
    },
    { 
      icon: Download, 
      label: '펌웨어 업데이트', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => document.getElementById('firmware-file-input')?.click(),
      info: selectedFirmware,
      disabled: false
    },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 h-fit sticky top-8">
      <div className="space-y-3">
        {buttons.map((button, index) => {
          const Icon = button.icon;
          const isVisuallyDisabled = button.visuallyDisabled || button.disabled;
          return (
            <div key={index}>
              <button
                onClick={button.onClick}
                disabled={button.disabled}
                className={`
                  w-full flex items-center gap-4 px-6 py-4 rounded-xl
                  bg-gradient-to-r ${button.color}
                  text-white
                  ${isVisuallyDisabled ? 'opacity-70 cursor-not-allowed' : 'hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]'}
                  transition-all duration-300
                  group
                `}
              >
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0 group-hover:bg-white/30 transition-all">
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 text-left">
                  <div>{button.label}</div>
                  {button.info && (
                    <div className="text-white/80 truncate max-w-[180px]">
                      {button.info}
                    </div>
                  )}
                </div>
              </button>

              {/* 유닛보드 선택 드롭다운 */}
              {index === 0 && showUnitSelector && (
                <div className="mt-2 bg-slate-50 rounded-xl p-4 border border-slate-200 max-h-[300px] overflow-y-auto">
                  <div className="grid grid-cols-4 gap-2">
                    {Array.from({ length: 32 }, (_, i) => i + 1).map((num) => (
                      <button
                        key={num}
                        onClick={() => handleUnitSelect(num)}
                        className={`
                          px-3 py-2 rounded-lg transition-all
                          ${selectedUnitId === num - 1 
                            ? 'bg-gradient-to-r from-[#0A4D68] to-[#0A84FF] text-white shadow-md' 
                            : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                          }
                        `}
                      >
                        {num}
                      </button>
                    ))}
                  </div>
                </div>
              )}

            </div>
          );
        })}
      </div>

      {/* 숨겨진 파일 입력 */}
      <input
        id="recipe-file-input"
        type="file"
        accept=".json"
        onChange={handleRecipeFileSelect}
        className="hidden"
      />
      <input
        id="firmware-file-input"
        type="file"
        accept=".bin,.hex,.zip"
        onChange={handleFirmwareSelect}
        className="hidden"
      />

      {/* System Info */}
      <div className="mt-6 pt-6 border-t border-slate-200">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">시스템 상태</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-emerald-600">정상</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">연결 상태</span>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isPiConnected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}`}></div>
              <span className={isPiConnected ? 'text-emerald-600' : 'text-slate-500'}>
                {isPiConnected ? '연결됨' : '연결 끊김'}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">펌웨어 버전</span>
            <span className="text-slate-700">{firmwareVersion}</span>
          </div>
          {/* 레시피 남은 시간 표시 */}
          {remainingTime > 0 && (
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" />
                <span className="text-slate-500">남은 시간</span>
              </div>
              <div className="flex items-center gap-2">
                {isTimerRunning && (
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                )}
                <span className={`font-mono text-lg ${isTimerRunning ? 'text-emerald-600' : 'text-slate-600'}`}>
                  {formatTime(remainingTime)}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}