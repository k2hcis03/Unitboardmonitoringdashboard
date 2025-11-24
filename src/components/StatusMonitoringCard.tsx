import { Thermometer, Droplets, Wind, Gauge, Activity, Scale } from 'lucide-react';

export function StatusMonitoringCard() {
  // 센서에서 읽어온 실제 상태값 (독립적)
  const sensorData = [
    { icon: Thermometer, name: '온도센서1', value: '12.5', unit: '°C' },
    { icon: Thermometer, name: '온도센서2', value: '12.3', unit: '°C' },
    { icon: Thermometer, name: '온도센서3', value: '34.4', unit: '°C' },
    { icon: Thermometer, name: '온도센서4', value: '20.2', unit: '°C' },
    { icon: Droplets, name: 'pH 센서', value: '12.3', unit: 'pH' },
    { icon: Wind, name: 'CO₂ 센서', value: '12.3', unit: 'ppm' },
    { icon: Activity, name: '유량 센서', value: '34.4', unit: 'L/min' },
    { icon: Gauge, name: '당도 센서', value: '20.2', unit: 'Brix' },
    { icon: Scale, name: '로드셀', value: '125.8', unit: 'kg' },
  ];

  // 유닛보드에서 읽어온 실제 상태값 (독립적)
  const statusData = [
    { name: '모터 속도', value: '1250 RPM', highlight: true },
    { name: '밸브1', value: 'ON', isOn: true },
    { name: '밸브2', value: 'OFF', isOn: false },
    { name: '밸브3', value: 'ON', isOn: true },
    { name: '밸브4', value: 'OFF', isOn: false },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-1 h-8 bg-gradient-to-b from-[#0A4D68] to-[#0A84FF] rounded-full"></div>
        <h2 className="text-[#0A4D68]">유닛보드 상태</h2>
      </div>

      {/* Sensor Values Grid */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-5 mb-8 pb-8 border-b border-slate-200">
        {sensorData.map((sensor, index) => {
          const Icon = sensor.icon;
          return (
            <div key={index} className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#0A4D68]/10 to-[#0A84FF]/10 flex items-center justify-center flex-shrink-0">
                <Icon className="w-5 h-5 text-[#0A4D68]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-slate-700">{sensor.name}</span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-[#0A4D68] tabular-nums">{sensor.value}</span>
                    <span className="text-slate-500">{sensor.unit}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Motor & Valve Status */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-4">
        {statusData.map((item, index) => (
          <div key={index} className="flex items-center justify-between">
            <span className="text-slate-700">{item.name}</span>
            <span 
              className={`
                px-3 py-1 rounded-full
                ${item.highlight 
                  ? 'bg-gradient-to-r from-[#0A4D68] to-[#0A84FF] text-white' 
                  : item.isOn 
                    ? 'bg-[#0A84FF] text-white' 
                    : 'bg-slate-200 text-slate-600'
                }
              `}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}