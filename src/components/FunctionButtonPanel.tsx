import { Cpu, BookOpen, Play, Square, Download } from 'lucide-react';
import { useState } from 'react';

export function FunctionButtonPanel() {
  const [showUnitSelector, setShowUnitSelector] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<number | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<string | null>(null);
  const [selectedFirmware, setSelectedFirmware] = useState<string | null>(null);

  const handleUnitSelect = (unitNumber: number) => {
    setSelectedUnit(unitNumber);
    setShowUnitSelector(false);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedRecipe(file.name);
    }
  };

  const handleFirmwareSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFirmware(file.name);
    }
  };

  const buttons = [
    { 
      icon: Cpu, 
      label: '유닛보드 선택', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => setShowUnitSelector(!showUnitSelector),
      info: selectedUnit ? `유닛 ${selectedUnit}` : null
    },
    { 
      icon: BookOpen, 
      label: '레시피 선택', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => document.getElementById('recipe-file-input')?.click(),
      info: selectedRecipe
    },
    { 
      icon: Play, 
      label: '레시피 시작', 
      color: 'from-emerald-600 to-emerald-500',
      onClick: () => console.log('레시피 시작')
    },
    { 
      icon: Square, 
      label: '레시피 종료', 
      color: 'from-rose-600 to-rose-500',
      onClick: () => console.log('레시피 종료')
    },
    { 
      icon: Download, 
      label: '펌웨어 업데이트', 
      color: 'from-[#0A4D68] to-[#0A84FF]',
      onClick: () => document.getElementById('firmware-file-input')?.click(),
      info: selectedFirmware
    },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 h-fit sticky top-8">
      <div className="space-y-3">
        {buttons.map((button, index) => {
          const Icon = button.icon;
          return (
            <div key={index}>
              <button
                onClick={button.onClick}
                className={`
                  w-full flex items-center gap-4 px-6 py-4 rounded-xl
                  bg-gradient-to-r ${button.color}
                  text-white
                  hover:shadow-lg hover:scale-[1.02]
                  active:scale-[0.98]
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
                          ${selectedUnit === num 
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
        accept=".json,.csv,.txt,.recipe"
        onChange={handleFileSelect}
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
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-emerald-600">연결됨</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">펌웨어 버전</span>
            <span className="text-slate-700">v2.4.1</span>
          </div>
        </div>
      </div>
    </div>
  );
}