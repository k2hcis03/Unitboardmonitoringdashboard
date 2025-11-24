import { Power, Gauge } from 'lucide-react';
import { useState } from 'react';

interface GPIOControlPanelProps {
  gpioStates: boolean[];
  toggleGPIO: (index: number) => void;
  motorOn: boolean;
  setMotorOn: (value: boolean) => void;
  motorSpeed: number;
  setMotorSpeed: (value: number) => void;
}

export function GPIOControlPanel({
  gpioStates,
  toggleGPIO,
  motorOn,
  setMotorOn,
  motorSpeed,
  setMotorSpeed,
}: GPIOControlPanelProps) {
  const [showSpeedControl, setShowSpeedControl] = useState(false);

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-1 h-8 bg-gradient-to-b from-[#0A4D68] to-[#0A84FF] rounded-full"></div>
        <h2 className="text-[#0A4D68]">GPIO 제어</h2>
      </div>

      {/* GPIO Toggles */}
      <div className="grid grid-cols-2 gap-6 mb-8 pb-8 border-b border-slate-200">
        {/* Left Column - GPIO 1-4 */}
        <div className="space-y-4">
          {[0, 1, 2, 3].map((index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="text-slate-700">GPIO{index + 1}</span>
              <button
                onClick={() => toggleGPIO(index)}
                className={`
                  relative w-16 h-9 rounded-full transition-all duration-300 shadow-inner
                  ${gpioStates[index] 
                    ? 'bg-gradient-to-r from-[#0A4D68] to-[#0A84FF]' 
                    : 'bg-slate-300'
                  }
                  hover:shadow-lg
                `}
              >
                <div
                  className={`
                    absolute top-1 w-7 h-7 bg-white rounded-full shadow-md transition-all duration-300
                    ${gpioStates[index] ? 'left-8' : 'left-1'}
                  `}
                />
                <span className={`
                  absolute inset-0 flex items-center justify-center text-white transition-opacity
                  ${gpioStates[index] ? 'opacity-100' : 'opacity-0'}
                `}>
                  <Power className="w-4 h-4" />
                </span>
              </button>
            </div>
          ))}
        </div>

        {/* Right Column - GPIO 5-8 */}
        <div className="space-y-4">
          {[4, 5, 6, 7].map((index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="text-slate-700">GPIO{index + 1}</span>
              <button
                onClick={() => toggleGPIO(index)}
                className={`
                  relative w-16 h-9 rounded-full transition-all duration-300 shadow-inner
                  ${gpioStates[index] 
                    ? 'bg-gradient-to-r from-[#0A4D68] to-[#0A84FF]' 
                    : 'bg-slate-300'
                  }
                  hover:shadow-lg
                `}
              >
                <div
                  className={`
                    absolute top-1 w-7 h-7 bg-white rounded-full shadow-md transition-all duration-300
                    ${gpioStates[index] ? 'left-8' : 'left-1'}
                  `}
                />
                <span className={`
                  absolute inset-0 flex items-center justify-center text-white transition-opacity
                  ${gpioStates[index] ? 'opacity-100' : 'opacity-0'}
                `}>
                  <Power className="w-4 h-4" />
                </span>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Motor Controls */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-slate-700">MOTOR Speed</span>
          <button
            onClick={() => setShowSpeedControl(!showSpeedControl)}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-[#0A4D68] to-[#0A84FF] text-white hover:shadow-lg transition-all duration-300 flex items-center gap-2"
          >
            <Gauge className="w-4 h-4" />
            {motorSpeed} RPM
          </button>
        </div>

        {showSpeedControl && (
          <div className="bg-slate-50 rounded-lg p-4 space-y-3">
            <input
              type="range"
              min="0"
              max="2000"
              step="10"
              value={motorSpeed}
              onChange={(e) => setMotorSpeed(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0A84FF]"
            />
            <div className="flex justify-between">
              {[0, 500, 1000, 1500, 2000].map((val) => (
                <button
                  key={val}
                  onClick={() => setMotorSpeed(val)}
                  className="px-3 py-1 text-slate-600 hover:bg-white hover:text-[#0A4D68] rounded transition-all"
                >
                  {val}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-slate-700">MOTOR ON/OFF</span>
          <button
            onClick={() => setMotorOn(!motorOn)}
            className={`
              relative w-16 h-9 rounded-full transition-all duration-300 shadow-inner
              ${motorOn 
                ? 'bg-gradient-to-r from-[#0A4D68] to-[#0A84FF]' 
                : 'bg-slate-300'
              }
              hover:shadow-lg
            `}
          >
            <div
              className={`
                absolute top-1 w-7 h-7 bg-white rounded-full shadow-md transition-all duration-300
                ${motorOn ? 'left-8' : 'left-1'}
              `}
            />
            <span className={`
              absolute inset-0 flex items-center justify-center text-white transition-opacity
              ${motorOn ? 'opacity-100' : 'opacity-0'}
            `}>
              <Power className="w-4 h-4" />
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}