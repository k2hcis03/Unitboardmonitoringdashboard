import { Cpu, BookOpen, Play, Square, Download } from 'lucide-react';

export function FunctionButtonPanel() {
  const buttons = [
    { icon: Cpu, label: '유닛보드 선택', color: 'from-[#0A4D68] to-[#0A84FF]' },
    { icon: BookOpen, label: '레시피 선택', color: 'from-[#0A4D68] to-[#0A84FF]' },
    { icon: Play, label: '레시피 시작', color: 'from-emerald-600 to-emerald-500' },
    { icon: Square, label: '레시피 종료', color: 'from-rose-600 to-rose-500' },
    { icon: Download, label: '펌웨어 업데이트', color: 'from-[#0A4D68] to-[#0A84FF]' },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 h-fit sticky top-8">
      <div className="space-y-3">
        {buttons.map((button, index) => {
          const Icon = button.icon;
          return (
            <button
              key={index}
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
              <span className="flex-1 text-left">{button.label}</span>
            </button>
          );
        })}
      </div>

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
