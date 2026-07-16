import { Cpu, BookOpen, Play, Pause, Square, Download, LayoutDashboard, Settings2, Clock, Send } from 'lucide-react';
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { getTankIdForUnit, APP_VERSION } from '../config';
import { useWebSocket } from '../hooks/useWebSocket';

import { apiClient } from '../services/api';

// 초를 시:분:초 형식으로 변환하는 헬퍼 함수
const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// 유닛보드별 레시피/녹화 상태. 유닛을 전환해도 각 유닛이 자기 상태를 독립적으로 유지한다.
interface UnitRecipeState {
  selectedRecipe: string | null;   // 선택된 레시피 파일명
  selectedFirmware: string | null; // 선택된 펌웨어 파일명
  isRecording: boolean;            // 실행 중(일시정지 아님)
  recipeSessionActive: boolean;    // 세션 진행 중(일시정지 포함). 처음 시작과 재시작 구분용
  remainingTime: number;           // 남은 시간(초)
  isTimerRunning: boolean;         // 타이머 진행 여부
}

const DEFAULT_RECIPE_STATE: UnitRecipeState = {
  selectedRecipe: null,
  selectedFirmware: null,
  isRecording: false,
  recipeSessionActive: false,
  remainingTime: 0,
  isTimerRunning: false,
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

  const { lastMessage, sendMessage } = useWebSocket();
  const [isPiConnected, setIsPiConnected] = useState(false);
  const [firmwareVersion, setFirmwareVersion] = useState<string>('v0.0.0');
  // DB 초기화 선택 다이얼로그 표시 여부 및 대상 유닛
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [pendingStartUnitId, setPendingStartUnitId] = useState<number | null>(null);
  const [errorCode, setErrorCode] = useState<string>('0');
  const [showJsonPanel, setShowJsonPanel] = useState(false);
  const [jsonInput, setJsonInput] = useState<string>('');
  const [isSendingJson, setIsSendingJson] = useState(false);

  // 유닛보드별 레시피/녹화 상태 맵: { [unitId]: UnitRecipeState }
  // 유닛을 전환하면 해당 유닛의 상태가 표시되어, 각 유닛이 독립적으로 자기 정보를 유지한다.
  const [recipeStates, setRecipeStates] = useState<Record<number, UnitRecipeState>>({});
  // 현재 선택된 유닛의 레시피 상태 (없으면 기본값)
  const current = recipeStates[selectedUnitId] ?? DEFAULT_RECIPE_STATE;

  // 특정 유닛의 레시피 상태 부분 업데이트 헬퍼
  const updateUnitRecipe = (unitId: number, updates: Partial<UnitRecipeState>) => {
    setRecipeStates((prev) => ({
      ...prev,
      [unitId]: { ...(prev[unitId] ?? DEFAULT_RECIPE_STATE), ...updates },
    }));
  };

  // 실행 중인 유닛이 하나라도 있는지 여부 (타이머 인터벌 생성/정리 트리거)
  const anyTimerRunning = Object.values(recipeStates).some(
    (s) => s.isTimerRunning && s.remainingTime > 0
  );

  // 레시피 타이머: 화면에 보이는 유닛뿐 아니라 실행 중인 '모든' 유닛의 남은 시간을
  // 백그라운드에서 매초 감소시킨다. 유닛을 전환해도 각 유닛 타이머는 계속 진행된다.
  useEffect(() => {
    if (!anyTimerRunning) return;

    const interval = setInterval(() => {
      setRecipeStates((prev) => {
        const next: Record<number, UnitRecipeState> = {};
        const finishedUnits: number[] = [];
        let changed = false;

        for (const [key, s] of Object.entries(prev)) {
          const unitId = Number(key);
          if (s.isTimerRunning && s.remainingTime > 0) {
            changed = true;
            const remaining = s.remainingTime - 1;
            if (remaining <= 0) {
              finishedUnits.push(unitId);
              next[unitId] = { ...s, remainingTime: 0, isTimerRunning: false };
            } else {
              next[unitId] = { ...s, remainingTime: remaining };
            }
          } else {
            next[unitId] = s;
          }
        }

        // 종료된 유닛 알림은 상태 업데이트 밖에서 실행 (렌더 중 부작용 방지)
        if (finishedUnits.length > 0) {
          setTimeout(() => {
            finishedUnits.forEach((u) => alert(`유닛 ${u + 1} 레시피가 끝났습니다`));
          }, 0);
        }

        return changed ? next : prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [anyTimerRunning]);

  useEffect(() => {
    if (lastMessage?.type === 'SYSTEM_CONNECTION_STATUS') {
      setIsPiConnected(lastMessage?.data?.connected);
    }
    
    if (lastMessage?.type === 'ACK_INITIALIZE_RECEIVED') {
      const data = lastMessage.data;
      if (data && data.FW_VERSION) {
         const versionNum = parseFloat(data.FW_VERSION);
         if (!isNaN(versionNum)) {
           setFirmwareVersion(`v${(versionNum / 100).toFixed(2)}`);
         } else {
           setFirmwareVersion(data.FW_VERSION);
         }
      }
    }

    if (lastMessage?.type === 'SENSOR_UPDATE') {
      const errorArray = lastMessage.data?.ERROR;
      if (Array.isArray(errorArray)) {
        const currentTankId = getTankIdForUnit(selectedUnitId);
        const matched = errorArray.find(
          (item: { TANK_ID: number; CODE: string }) => Number(item.TANK_ID) === currentTankId
        );
        if (matched) {
          setErrorCode(matched.CODE);
        }
      }
    }
  }, [lastMessage, selectedUnitId]);

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
    // UNIT_TO_TANK_ID 매핑을 사용하여 unit_id 변환
    const mappedUnitId = getTankIdForUnit(unitId);
    sendMessage({
      type: 'UNIT_SELECT',
      unit_id: mappedUnitId
    });
    
    setShowUnitSelector(false);
  };

  const handleRecipeFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 비동기 처리 중 유닛이 바뀌어도 이 레시피는 선택 당시 유닛에 귀속되도록 캡처한다.
    const unitId = selectedUnitId;

    try {
      // 파일 읽기
      const fileContent = await file.text();

      // JSON 파싱
      let recipeData;
      try {
        recipeData = JSON.parse(fileContent);
      } catch (parseError) {
        alert('유효하지 않은 JSON 파일입니다.');
        updateUnitRecipe(unitId, { selectedRecipe: null });
        event.target.value = '';
        return;
      }

      // 레시피 데이터 검증 (CMD가 REF인지 확인)
      if (recipeData.CMD !== 'REF') {
        alert('유효하지 않은 레시피 파일입니다. CMD가 "REF"여야 합니다.');
        updateUnitRecipe(unitId, { selectedRecipe: null });
        event.target.value = '';
        return;
      }

      // 레시피 데이터를 라즈베리파이로 전송
      const result = await apiClient.sendRecipe(recipeData);

      if (result.success) {
        // 전체 시간 계산: STEP * DATA 개수
        const step = parseInt(recipeData.STEP) || 0;
        const dataCount = Array.isArray(recipeData.DATA) ? recipeData.DATA.length : 0;
        const totalTime = step * dataCount;

        // 전송 성공 시에만 해당 유닛에 파일명/남은 시간 저장 (타이머는 아직 시작하지 않음)
        updateUnitRecipe(unitId, {
          selectedRecipe: file.name,
          remainingTime: totalTime,
          isTimerRunning: false,
        });

        console.log(`Recipe ${file.name} sent successfully. Total time: ${totalTime} seconds (${formatTime(totalTime)})`);
        alert(`레시피 "${file.name}" 전송 완료\n예상 소요 시간: ${formatTime(totalTime)}`);
      } else {
        console.error('Failed to send recipe:', result.error);
        alert(`레시피 전송 실패: ${result.error || '알 수 없는 오류'}`);
        updateUnitRecipe(unitId, { selectedRecipe: null, remainingTime: 0 });
      }
    } catch (error) {
      console.error('Failed to process recipe file:', error);
      alert('레시피 파일 처리 중 오류가 발생했습니다.');
      updateUnitRecipe(unitId, { selectedRecipe: null });
    } finally {
      // 입력 초기화 (동일 파일 재선택 가능하게)
      event.target.value = '';
    }
  };

  const handleFirmwareSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const unitId = selectedUnitId;
      updateUnitRecipe(unitId, { selectedFirmware: file.name });

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
        // UNIT_TO_TANK_ID 매핑을 사용하여 unit_id 변환
        const mappedUnitId = getTankIdForUnit(unitId);
        console.log(`Firmware update request: Unit ${unitId} (mapped to ${mappedUnitId}), File ${file.name}`);
        
        await apiClient.updateFirmware(mappedUnitId, file.name);
        
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
    const unitId = selectedUnitId;
    const unitState = recipeStates[unitId] ?? DEFAULT_RECIPE_STATE;

    // 레시피가 선택되지 않은 경우 메시지 표시
    if (unitState.selectedRecipe === null) {
      alert('레시피를 선택하세요');
      return;
    }

    // 일시정지 후 재시작이면 묻지 않고 기존 DB에 이어서 저장
    if (unitState.recipeSessionActive) {
      await runStartRecording(unitId, false);
      return;
    }

    // 처음 시작이면 DB 초기화 여부를 묻는 다이얼로그 표시 (대상 유닛 기억)
    setPendingStartUnitId(unitId);
    setShowStartDialog(true);
  };

  // 실제 녹화 시작 요청. resetDb가 true면 백엔드에서 해당 유닛 DB를 비우고 시작한다.
  const runStartRecording = async (unitId: number, resetDb: boolean) => {
    try {
      console.log(`Starting recording for unit ${unitId}... (resetDb=${resetDb})`);
      const mappedUnitId = getTankIdForUnit(unitId);
      const response = await apiClient.startRecording(mappedUnitId, resetDb);
      if (response.is_recording) {
        // 남은 시간이 있으면 타이머도 함께 시작
        setRecipeStates((prev) => {
          const s = prev[unitId] ?? DEFAULT_RECIPE_STATE;
          return {
            ...prev,
            [unitId]: {
              ...s,
              isRecording: true,
              recipeSessionActive: true,
              isTimerRunning: s.remainingTime > 0,
            },
          };
        });
        console.log(`Recording started (db_cleared=${response.db_cleared ?? false})`);
      }
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('녹화 시작에 실패했습니다.');
    }
  };

  // 다이얼로그 선택 처리: 초기화 후 시작 / 계속 저장
  const handleStartDialogConfirm = async (resetDb: boolean) => {
    const unitId = pendingStartUnitId ?? selectedUnitId;
    setShowStartDialog(false);
    setPendingStartUnitId(null);
    await runStartRecording(unitId, resetDb);
  };

  const handlePauseRecording = async () => {
    const unitId = selectedUnitId;
    try {
      console.log(`Pausing recording for unit ${unitId}...`);
      const mappedUnitId = getTankIdForUnit(unitId);
      const response = await apiClient.pauseRecording(mappedUnitId);
      if (!response.is_recording) {
        // 실행 중지 + 타이머 일시정지 (남은 시간은 유지)
        updateUnitRecipe(unitId, { isRecording: false, isTimerRunning: false });
        console.log('Recording paused');
      }
    } catch (error) {
      console.error('Failed to pause recording:', error);
      alert('일시정지에 실패했습니다.');
    }
  };

  const handleStopRecording = async () => {
    const unitId = selectedUnitId;
    try {
      console.log(`Stopping recording for unit ${unitId}...`);
      const mappedUnitId = getTankIdForUnit(unitId);
      const response = await apiClient.stopRecording(mappedUnitId);
      if (!response.is_recording) {
        // 세션 종료 → 다음 시작 시 다시 DB 초기화 여부를 묻는다. 타이머/레시피 초기화.
        updateUnitRecipe(unitId, {
          isRecording: false,
          recipeSessionActive: false,
          isTimerRunning: false,
          remainingTime: 0,
          selectedRecipe: null,
        });
        console.log('Recording stopped');
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      alert('레시피 종료에 실패했습니다.');
    }
  };

  const handleJsonSend = async () => {
    if (!jsonInput.trim()) {
      alert('JSON 내용을 입력하세요.');
      return;
    }

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(jsonInput);
    } catch {
      alert('유효하지 않은 JSON 형식입니다. 확인 후 다시 시도하세요.');
      return;
    }

    setIsSendingJson(true);
    try {
      const result = await apiClient.sendRawJson(parsed);
      if (result.success) {
        alert('JSON 전송 완료');
      } else {
        alert(`JSON 전송 실패: ${result.error || '알 수 없는 오류'}`);
      }
    } catch (error: any) {
      console.error('Failed to send raw JSON:', error);
      alert(`JSON 전송 중 오류가 발생했습니다.\n${error?.message || error}`);
    } finally {
      setIsSendingJson(false);
    }
  };

  const getJsonTemplate = () => {
    const mappedUnitId = getTankIdForUnit(selectedUnitId);
    return JSON.stringify({
      UNIT_ID: String(mappedUnitId),
      IDX: 1,
      TANK_ID: String(mappedUnitId),
      CMD: "TEMP_RPM",
      SPEED: 1000,
      DIR: "FW",
      ONOFF: "ON",
      TIME: 300,
      SEND: false
    }, null, 2);
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
      info: current.selectedRecipe,
      disabled: false
    },
    {
      icon: current.isRecording ? Pause : Play,
      label: current.isRecording ? '레시피 일시정지' : '레시피 시작',
      color: 'from-emerald-600 to-emerald-500',
      onClick: current.isRecording ? handlePauseRecording : handleStartRecording,
      disabled: false,
      visuallyDisabled: !current.isRecording && current.selectedRecipe === null
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
      info: current.selectedFirmware,
      disabled: false
    },
    { 
      icon: Send, 
      label: 'JSON 전송', 
      color: '',
      gradientStyle: { background: 'linear-gradient(to right, #B45309, #D97706)' },
      onClick: () => {
        if (!showJsonPanel && !jsonInput.trim()) {
          setJsonInput(getJsonTemplate());
        }
        setShowJsonPanel(!showJsonPanel);
      },
      disabled: false
    },
  ];

  return (
    <>
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 sticky top-8 max-h-[calc(100vh-4rem)] overflow-y-auto">
      <div className="space-y-3">
        {buttons.map((button, index) => {
          const Icon = button.icon;
          const isVisuallyDisabled = button.visuallyDisabled || button.disabled;
          return (
            <div key={index}>
              <button
                onClick={button.onClick}
                disabled={button.disabled}
                style={button.gradientStyle}
                className={`
                  w-full flex items-center gap-4 px-6 py-4 rounded-xl
                  ${button.color ? `bg-gradient-to-r ${button.color}` : ''}
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

              {/* JSON 전송 입력 패널 */}
              {index === buttons.length - 1 && showJsonPanel && (
                <div className="mt-2 bg-slate-50 rounded-xl p-4 border border-slate-200">
                  <textarea
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    placeholder='{"CMD": "TEMP_RPM", ...}'
                    className="w-full h-48 p-3 text-sm font-mono bg-white border border-slate-300 rounded-lg resize-y focus:outline-none"
                    spellCheck={false}
                  />
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={handleJsonSend}
                      disabled={isSendingJson}
                      style={isSendingJson ? undefined : { backgroundColor: '#B45309' }}
                      className={`flex-1 py-2 px-4 rounded-lg text-white font-medium transition-all
                        ${isSendingJson ? 'bg-slate-400 cursor-not-allowed' : 'hover:shadow-lg active:scale-[0.98]'}
                      `}
                    >
                      {isSendingJson ? '전송 중...' : '전송'}
                    </button>
                    <button
                      onClick={() => setJsonInput(getJsonTemplate())}
                      className="py-2 px-4 rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-all"
                    >
                      템플릿
                    </button>
                    <button
                      onClick={() => setJsonInput('')}
                      className="py-2 px-4 rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-all"
                    >
                      초기화
                    </button>
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
              <div className={`w-2 h-2 rounded-full ${errorCode === '0' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500 animate-pulse'}`}></div>
              <span className={errorCode === '0' ? 'text-emerald-600' : 'text-rose-600 font-semibold'}>
                {errorCode === '0' ? '정상' : `에러: ${errorCode}`}
              </span>
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
          <div className="flex items-center justify-between">
            <span className="text-slate-500">프로그램 버전</span>
            <span className="text-slate-700">{APP_VERSION}</span>
          </div>
          {/* 레시피 남은 시간 표시 (현재 선택된 유닛 기준) */}
          {current.remainingTime > 0 && (
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" />
                <span className="text-slate-500">남은 시간</span>
              </div>
              <div className="flex items-center gap-2">
                {current.isTimerRunning && (
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                )}
                <span className={`font-mono text-lg ${current.isTimerRunning ? 'text-emerald-600' : 'text-slate-600'}`}>
                  {formatTime(current.remainingTime)}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>

    {/* 레시피 시작 시 DB 초기화 선택 다이얼로그
        App.tsx 래퍼의 transform: scale() 때문에 position:fixed가 뷰포트가 아닌 래퍼 기준이 되므로,
        createPortal로 document.body에 렌더링하여 진짜 화면 중앙에 띄운다. */}
    {showStartDialog && createPortal(
      <div
        className="flex items-center justify-center"
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 50,
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          backdropFilter: 'blur(2px)',
        }}
        onClick={() => setShowStartDialog(false)}
      >
        <div
          className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-[420px] max-w-[90vw]"
          onClick={(e) => e.stopPropagation()}
        >
          <h3 className="text-lg font-semibold text-[#0A4D68] mb-2">레시피 시작</h3>
          <p className="text-slate-600 mb-5 leading-relaxed">
            데이터베이스를 <span className="font-semibold text-rose-600">초기화</span>하고 새로 시작할까요,
            아니면 기존 데이터베이스에 이어서 저장할까요?
          </p>
          <div className="space-y-2">
            <button
              onClick={() => handleStartDialogConfirm(true)}
              className="w-full py-3 px-4 rounded-xl text-white font-medium bg-gradient-to-r from-rose-600 to-rose-500 hover:shadow-lg active:scale-[0.98] transition-all"
            >
              초기화 후 새로 시작
            </button>
            <button
              onClick={() => handleStartDialogConfirm(false)}
              className="w-full py-3 px-4 rounded-xl text-white font-medium bg-gradient-to-r from-[#0A4D68] to-[#0A84FF] hover:shadow-lg active:scale-[0.98] transition-all"
            >
              기존 DB에 계속 저장
            </button>
            <button
              onClick={() => setShowStartDialog(false)}
              className="w-full py-3 px-4 rounded-xl text-slate-700 font-medium bg-slate-100 hover:bg-slate-200 active:scale-[0.98] transition-all"
            >
              취소
            </button>
          </div>
        </div>
      </div>,
      document.body
    )}
    </>
  );
}