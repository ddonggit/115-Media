/** Notify API */
import http from './axios'
import type { NotifyConfigItem, NotifyConfigCreate, NotifyConfigUpdate } from './types'

export function listNotifyConfigs() {
  return http.get<NotifyConfigItem[]>('/notify/')
}

export function createNotifyConfig(data: NotifyConfigCreate) {
  return http.post<NotifyConfigItem>('/notify/', data)
}

export function updateNotifyConfig(id: number, data: NotifyConfigUpdate) {
  return http.put<NotifyConfigItem>(`/notify/${id}`, data)
}

export function deleteNotifyConfig(id: number) {
  return http.delete<{ message: string }>(`/notify/${id}`)
}

export function testNotify() {
  return http.post<{ message: string }>('/notify/test')
}
