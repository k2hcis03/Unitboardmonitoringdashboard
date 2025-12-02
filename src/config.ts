/**
 * 애플리케이션 설정 관리
 * 환경 변수(.env)가 있으면 그것을 우선 사용하고,
 * 없으면 현재 브라우저의 호스트(window.location.hostname)를 기반으로 자동 설정합니다.
 */

// 백엔드 포트 설정 (기본값: 9000)
const BACKEND_PORT = 9000;

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

