/** Dashboard API */
import http from './axios'
import type { ApiResponse, DashboardStats, ErrorLogItem } from './types'

export function getStats() {
  return http.get<ApiResponse<DashboardStats>>('/dashboard/stats')
}

export function getErrors() {
  return http.get<ErrorLogItem[]>('/dashboard/errors')
}

export function resolveError(errorId: number) {
  return http.post<{ message: string }>(`/dashboard/errors/${errorId}/resolve`)
}

export function retryError(errorId: number) {
  return http.post<{ message: string }>(`/dashboard/errors/${errorId}/retry`)
}
