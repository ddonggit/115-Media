/** Logs API */
import http from './axios'
import type { OperationLogItem } from './types'

export function listLogs(params?: { module?: string; level?: string; range?: string; limit?: number }) {
  return http.get<OperationLogItem[]>('/logs/', { params })
}

export function clearLogs() {
  return http.delete<{ message: string }>('/logs/')
}

export function getLogModules() {
  return http.get<{ data: string[] }>('/logs/modules')
}

export function getLogStats() {
  return http.get<{ data: { by_level: Record<string, number>; by_module: Record<string, number> } }>('/logs/stats')
}
