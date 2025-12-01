import { Thermometer, Droplets, Wind, Gauge, Activity, Scale } from 'lucide-react';
import React, { useEffect, useState, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface StatusMonitoringCardProps {
  selectedUnitId: number;
}

// Sensor Value Structure from Backend
interface SensorValue {
  TANK_ID: number;
  SENSOR_ID: number;
  VALUE: string;
}

// Sensor Packet Structure from Backend
interface SensorPacket {
  CMD: string;
  VALUES: SensorValue[];
  // ... other fields like STATE, ORDER, DATE, TIME if needed
}

export function StatusMonitoringCard({ selectedUnitId }: StatusMonitoringCardProps) {
  const { lastMessage } = useWebSocket();
  
  // Store latest sensor values by TANK_ID and SENSOR_ID
  // Map<tankId, Map<sensorId, value>>
  const [sensorValues, setSensorValues] = useState<Record<number, Record<number, string>>>({});

  useEffect(() => {
    if (lastMessage?.type === 'SENSOR_UPDATE') {
      const packet = lastMessage.data as SensorPacket;
      
      if (packet.VALUES && Array.isArray(packet.VALUES)) {
        setSensorValues(prev => {
          const next = { ...prev };
          
          packet.VALUES.forEach(item => {
            const tankId = Number(item.TANK_ID);
            const sensorId = Number(item.SENSOR_ID);
            
            if (!next[tankId]) {
              next[tankId] = {};
            }
            // Create a new object for the tank to ensure React detects change
            next[tankId] = {
                ...next[tankId],
                [sensorId]: item.VALUE
            };
          });
          
          return next;
        });
      }
    }
  }, [lastMessage]);

  // Helper to get value for current selected unit
  // User Requirement: 
  // "유닛보드 1번을 선택하면 라즈베리파이에서 전송하는 센서 데이터 TANK_ID가 101번일 때야."
  // "유닛보드 0는 무시"
  // Mapping: Unit 1 (selectedUnitId=0 in code because of 0-index from FunctionButtonPanel)
  // So if selectedUnitId is 0 (which means Unit 1), we want TANK_ID 101.
  // Formula: 101 + selectedUnitId
  const currentTankId = 101 + selectedUnitId; 
  
  const getValue = (sensorId: number, defaultValue: string) => {
    return sensorValues[currentTankId]?.[sensorId] || defaultValue;
  };

  // 센서 데이터 구성
  const sensorData = useMemo(() => [
    { icon: Thermometer, name: '온도센서1', value: getValue(100, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서2', value: getValue(101, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서3', value: getValue(102, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서4', value: getValue(103, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서5', value: getValue(104, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서6', value: getValue(105, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서7', value: getValue(106, '0.0'), unit: '°C' },
    { icon: Thermometer, name: '온도센서8', value: getValue(107, '0.0'), unit: '°C' },
    { icon: Droplets, name: 'pH 센서', value: getValue(800, '0.0'), unit: 'pH' },
    { icon: Wind, name: 'CO₂ 센서', value: getValue(300, '0.0'), unit: 'ppm' },
    { icon: Activity, name: '유량 센서', value: getValue(700, '0.0'), unit: 'L/min' },
    { icon: Gauge, name: '당도 센서', value: getValue(900, '0.0'), unit: 'Brix' }, 
    { icon: Scale, name: '로드셀', value: getValue(400, '0.0'), unit: 'kg' },
  ], [sensorValues, currentTankId]);

  // 유닛보드 상태 데이터 구성
  // 500~: Valves (500=V1, 501=V2...), 600: Motor Speed
  const statusData = useMemo(() => [
    { name: '모터 속도', value: getValue(600, '0') + ' RPM', highlight: true },
    { name: '밸브1', value: getValue(500, '0') === '1' ? 'ON' : 'OFF', isOn: getValue(500, '0') === '1' },
    { name: '밸브2', value: getValue(501, '0') === '1' ? 'ON' : 'OFF', isOn: getValue(501, '0') === '1' },
    { name: '밸브3', value: getValue(502, '0') === '1' ? 'ON' : 'OFF', isOn: getValue(502, '0') === '1' },
    { name: '밸브4', value: getValue(503, '0') === '1' ? 'ON' : 'OFF', isOn: getValue(503, '0') === '1' },
  ], [sensorValues, currentTankId]);

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-1 h-8 bg-gradient-to-b from-[#0A4D68] to-[#0A84FF] rounded-full"></div>
        <h2 className="text-[#0A4D68]">유닛보드 상태 (Unit {selectedUnitId + 1} / Tank {currentTankId})</h2>
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