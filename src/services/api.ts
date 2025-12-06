import { API_BASE_URL } from '../config';

/**
 * 백엔드 API 통신 서비스
 */
// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';


export interface UnitStatus {
  unit_info: {
    unit_id: number;
    name: string | null;
    firmware_version: string | null;
    is_connected: boolean;
  };
  sensors: {
    temperature_1: number;
    temperature_2: number;
    temperature_3: number;
    temperature_4: number;
    temperature_5: number;
    temperature_6: number;
    temperature_7: number;
    temperature_8: number;
    ph: number;
    co2: number;
    flow_rate: number;
    brix: number;
    load_cell: number;
  };
  motor: {
    is_on: boolean;
    speed: number;
  };
  valves: {
    valve_1: boolean;
    valve_2: boolean;
    valve_3: boolean;
    valve_4: boolean;
  };
  last_updated: string;
}

export interface GPIOState {
  gpio_states: boolean[];
}

export interface GPIOControlRequest {
  unit_id: number;
  gpio_index: number;
  state: boolean;
}

export interface MotorControlRequest {
  unit_id: number;
  is_on: boolean;
  speed?: number;
}

export interface GPIOBulkControlRequest {
  unit_id: number;
  gpio_states: boolean[];
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(error.message || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  /**
   * 모든 유닛보드 상태 조회
   */
  async getAllUnitsStatus(): Promise<Record<number, UnitStatus>> {
    return this.request<Record<number, UnitStatus>>('/api/units/');
  }

  /**
   * 특정 유닛보드 상태 조회
   */
  async getUnitStatus(unitId: number): Promise<UnitStatus> {
    return this.request<UnitStatus>(`/api/units/${unitId}`);
  }

  /**
   * GPIO 상태 조회
   */
  async getGPIOState(unitId: number): Promise<GPIOState> {
    return this.request<GPIOState>(`/api/units/${unitId}/gpio`);
  }

  /**
   * GPIO 제어
   */
  async controlGPIO(request: GPIOControlRequest): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('/api/gpio/control', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * 모터 제어
   */
  async controlMotor(request: MotorControlRequest): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('/api/gpio/motor', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * 펌웨어 업데이트
   */
  async updateFirmware(unitId: number, filePath: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/units/${unitId}/firmware`, {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath }),
    });
  }

  /**
   * GPIO 일괄 제어 (모든 GPIO 상태를 한 번에 전송)
   */
  async controlGPIOBulk(request: GPIOBulkControlRequest): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('/api/gpio/bulk', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * DB 기록 시작
   */
  async startRecording(): Promise<{ status: string, is_recording: boolean }> {
    return this.request<{ status: string, is_recording: boolean }>('/api/recording/start', {
      method: 'POST',
    });
  }

  /**
   * DB 기록 중지
   */
  async stopRecording(): Promise<{ status: string, is_recording: boolean }> {
    return this.request<{ status: string, is_recording: boolean }>('/api/recording/stop', {
      method: 'POST',
    });
  }

  /**
   * DB 기록 상태 조회
   */
  async getRecordingStatus(): Promise<{ is_recording: boolean }> {
    return this.request<{ is_recording: boolean }>('/api/recording/status', {
      method: 'GET',
    });
  }
}

export const apiClient = new APIClient();

