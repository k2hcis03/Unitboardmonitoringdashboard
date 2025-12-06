import React, { useState, useEffect, useRef, PropsWithChildren } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from './ui/accordion';
import { useWebSocket } from '../hooks/useWebSocket';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { Play, Pause } from 'lucide-react';

// Define the sensor data structure for the chart
interface ChartData {
  time: string;
  timestamp: number;
  temp1?: number;
  temp2?: number;
  temp3?: number;
  temp4?: number;
  temp5?: number;
  temp6?: number;
  temp7?: number;
  temp8?: number;
  ph?: number;
  co2?: number;
  flow?: number;
  brix?: number;
  load_cell?: number;
}

const MAX_DATA_POINTS = 100; // Keep last 100 points for performance

interface DashboardPanelProps {
  selectedUnitId: number;
  tempSelection?: boolean[];
  onTempSelectionChange?: (selection: boolean[]) => void;
}

export function DashboardPanel({ selectedUnitId, tempSelection, onTempSelectionChange }: DashboardPanelProps) {
  const { lastMessage } = useWebSocket();
  const [data, setData] = useState<ChartData[]>([]);
  const [isStreaming, setIsStreaming] = useState(true); // Toggle for pause/resume

  // Accordion open items state
  const [openItems, setOpenItems] = useState<string[]>([
    "item-1", "item-2", "item-3", "item-4", "item-5", "item-6"
  ]);
  
  // Temperature selection state (Use props if available, otherwise local state)
  const [localSelectedTemps, setLocalSelectedTemps] = useState<boolean[]>(
    Array(8).fill(true)
  );

  const selectedTemps = tempSelection || localSelectedTemps;
  const setSelectedTemps = onTempSelectionChange || setLocalSelectedTemps;

  useEffect(() => {
    if (!isStreaming) return; // Stop updating if paused

    if (lastMessage?.type === 'SENSOR_UPDATE') {
      const sensorData = lastMessage.data;
      
      if (sensorData && Array.isArray(sensorData.VALUES)) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('ko-KR', { hour12: false });
        
        // Initialize a new data point
        const newPoint: any = {
          time: timeStr,
          timestamp: now.getTime(),
        };

        let hasDataForUnit = false;

        sensorData.VALUES.forEach((item: any) => {
            // TANK_ID 매핑: StatusMonitoringCard와 동일하게 처리 (101 + index)
            const targetTankIdStr = (selectedUnitId + 101).toString();
            const itemTankIdStr = item.TANK_ID.toString();

            if (itemTankIdStr === targetTankIdStr) {
                hasDataForUnit = true;
                const val = parseFloat(item.VALUE);
                const sensorId = parseInt(item.SENSOR_ID);

                // Sensor ID Mapping (Based on StatusMonitoringCard)
                if (sensorId >= 100 && sensorId <= 107) {
                    newPoint[`temp${sensorId - 99}`] = val;
                } else if (sensorId === 800) {
                    newPoint.ph = val;
                } else if (sensorId === 300) {
                    newPoint.co2 = val;
                } else if (sensorId === 700) { 
                    newPoint.flow = val;
                } else if (sensorId === 900) {
                     newPoint.brix = val;
                } else if (sensorId === 400) {
                     newPoint.load_cell = val;
                }
            }
        });

        if (hasDataForUnit) {
            setData(prev => {
                const newData = [...prev, newPoint];
                if (newData.length > MAX_DATA_POINTS) {
                    return newData.slice(newData.length - MAX_DATA_POINTS);
                }
                return newData;
            });
        }
      }
    }
  }, [lastMessage, selectedUnitId, isStreaming]);

  const toggleTemp = (index: number) => {
    const newSelections = [...selectedTemps];
    newSelections[index] = !newSelections[index];
    setSelectedTemps(newSelections);
  };

  const ChartWrapper = ({ title, unit, children }: PropsWithChildren<{ title: string; unit: string }>) => (
    <div className="w-full mt-4 border border-slate-300 rounded-lg bg-white p-4 relative" style={{ height: 300, width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, bottom: 5, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200" />
          <XAxis 
            dataKey="time" 
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            label={{ value: unit, angle: -90, position: 'insideLeft', offset: -5 }} 
            domain={['auto', 'auto']}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Legend />
          {children}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="p-6 space-y-4 bg-slate-50 min-h-screen">
      <Card className="border-none shadow-sm bg-transparent">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-2xl font-bold text-slate-800">
            실시간 센서 모니터링 (Unit {selectedUnitId + 1})
          </CardTitle>
          <div className="flex items-center space-x-3 bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm">
             <button
              onClick={() => setIsStreaming(!isStreaming)}
              className={`
                flex items-center justify-center w-10 h-10 rounded-full transition-all duration-200
                ${isStreaming 
                  ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                  : 'bg-emerald-100 text-emerald-600 hover:bg-emerald-200'
                }
              `}
              title={isStreaming ? '일시 정지' : '다시 시작'}
            >
              {isStreaming ? <Pause className="w-5 h-5" fill="currentColor" /> : <Play className="w-5 h-5" fill="currentColor" />}
            </button>
            <div className="flex flex-col">
              <span className="text-sm font-bold text-slate-700">
                {isStreaming ? '실시간 업데이트 중' : '일시 정지됨'}
              </span>
              <span className="text-xs text-slate-500">
                {isStreaming ? '데이터 수신 중...' : '화면 갱신 중단'}
              </span>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Accordion 
        type="multiple" 
        value={openItems} 
        onValueChange={setOpenItems}
        className="space-y-4"
      >
        
        {/* 1. Temperature Sensors */}
        <AccordionItem value="item-1" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-slate-700">온도 센서 (Temperature)</span>
              <span className="text-sm text-slate-400 font-normal">8 Channel</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <div className="flex flex-wrap gap-4 mb-4 p-4 bg-slate-50 rounded-lg">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-2">
                  <Checkbox 
                    id={`temp-${i}`} 
                    checked={selectedTemps[i]} 
                    onCheckedChange={() => toggleTemp(i)}
                  />
                  <Label htmlFor={`temp-${i}`} className="text-sm text-slate-600 cursor-pointer">
                    온도 {i + 1}
                  </Label>
                </div>
              ))}
            </div>
            <ChartWrapper title="온도" unit="°C">
              {Array.from({ length: 8 }).map((_, i) => (
                <Line
                  key={i}
                  type="monotone"
                  dataKey={`temp${i + 1}`}
                  name={`온도 ${i + 1}`}
                  stroke={`hsl(${i * 45}, 70%, 50%)`}
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                  hide={!selectedTemps[i]} 
                />
              ))}
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

        {/* 2. pH Sensor */}
        <AccordionItem value="item-2" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <span className="text-lg font-semibold text-slate-700">pH 센서</span>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <ChartWrapper title="pH" unit="pH">
              <Line type="monotone" dataKey="ph" stroke="#8884d8" name="pH" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

        {/* 3. CO2 Sensor */}
        <AccordionItem value="item-3" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <span className="text-lg font-semibold text-slate-700">CO2 센서</span>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <ChartWrapper title="CO2" unit="ppm">
              <Line type="monotone" dataKey="co2" stroke="#82ca9d" name="CO2" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

        {/* 4. Flow Rate Sensor */}
        <AccordionItem value="item-4" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <span className="text-lg font-semibold text-slate-700">유량 센서 (Flow Rate)</span>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <ChartWrapper title="유량" unit="L/min">
              <Line type="monotone" dataKey="flow" stroke="#ffc658" name="Flow" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

        {/* 5. Brix Sensor */}
        <AccordionItem value="item-5" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <span className="text-lg font-semibold text-slate-700">당도 센서 (Brix)</span>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <ChartWrapper title="당도" unit="°Bx">
              <Line type="monotone" dataKey="brix" stroke="#ff7300" name="Brix" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

        {/* 6. Load Cell */}
        <AccordionItem value="item-6" className="bg-white rounded-xl border border-slate-200 px-6">
          <AccordionTrigger className="hover:no-underline py-4">
            <span className="text-lg font-semibold text-slate-700">로드셀 (Load Cell)</span>
          </AccordionTrigger>
          <AccordionContent className="pb-6">
            <ChartWrapper title="무게" unit="kg">
              <Line type="monotone" dataKey="load_cell" stroke="#387908" name="Weight" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ChartWrapper>
          </AccordionContent>
        </AccordionItem>

      </Accordion>
    </div>
  );
}
