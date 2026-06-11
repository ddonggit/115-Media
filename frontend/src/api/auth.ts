/** Auth API */
import http from './axios'
import type { ApiResponse, LoginRequest, LoginResponse, UserInfo, CookieLoginRequest, CookieLoginResponse, QrCodeData, QrCodeStatus } from './types'

export function login(data: LoginRequest) {
  return http.post<ApiResponse<LoginResponse>>('/auth/login', data)
}

export function cookieLogin(data: CookieLoginRequest) {
  return http.post<ApiResponse<CookieLoginResponse>>('/auth/cookie', data)
}

export function getQrCode() {
  return http.get<ApiResponse<QrCodeData>>('/auth/qrcode')
}

export function checkQrCodeStatus(uid: string, time?: number, sign?: string) {
  return http.get<ApiResponse<QrCodeStatus>>('/auth/qrcode/status', { params: { uid, time, sign } })
}

export function getMe() {
  return http.get<ApiResponse<UserInfo>>('/auth/me')
}

export function refreshToken() {
  return http.post<ApiResponse<LoginResponse>>('/auth/refresh')
}

export function getAuthStatus() {
  return http.get<ApiResponse<{ logged_in: boolean; username: string; expire_time: string | null }>>('/auth/status')
}
