/**
 * 애플리케이션 설정 관리
 * 환경 변수(.env)가 있으면 그것을 우선 사용하고,
 * 없으면 현재 브라우저의 호스트(window.location.hostname)를 기반으로 자동 설정합니다.
 */

/**
 * 라즈베리파이 TANK_ID ↔ 프론트엔드 유닛보드 번호 매핑
 * - 데이터 수신 시에만 사용 (명령 전송은 selectedUnitId 그대로 유지)
 * - UNIT_TO_TANK_ID[유닛보드 index] = 해당 유닛에 표시할 TANK_ID
 * 예: 유닛보드 1 → TANK_ID 601, 유닛보드 2 → TANK_ID 101
 */
export const UNIT_TO_TANK_ID: number[] = [
  601,  // 유닛보드 1 (index 0)
  101,  // 유닛보드 2 (index 1)
  102,  // 유닛보드 3
  103,  // 유닛보드 4
  104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115,
  116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131  // 유닛보드 5~32
];

/** 선택된 유닛보드 index에 대해 표시할 TANK_ID 반환 (범위 초과 시 101+index 폴백) */
export function getTankIdForUnit(unitIndex: number): number {
  if (unitIndex >= 0 && unitIndex < UNIT_TO_TANK_ID.length) {
    return UNIT_TO_TANK_ID[unitIndex];
  }
  return 101 + unitIndex;
}

// 백엔드 포트 설정 (기본값: 9001)
const BACKEND_PORT = 9001;

// 현재 호스트 가져오기 (브라우저 주소창의 도메인/IP)
const currentHost = window.location.hostname;

// API Base URL 결정
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `http://${currentHost}:${BACKEND_PORT}`;

// WebSocket URL 결정
// https면 wss, http면 ws 사용
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
export const WS_URL = import.meta.env.VITE_WS_URL || `${wsProtocol}//${currentHost}:${BACKEND_PORT}/ws/status`;

console.log('App Config:', {
  API_BASE_URL,
  WS_URL,
  Host: currentHost
});

