/** RSS Sources API */
import http from './axios'
import type { RSSSourceItem, RSSSourceCreate, RSSSourceUpdate } from './types'

export function listSources(enabled?: boolean) {
  return http.get<RSSSourceItem[]>('/sources/', { params: { enabled } })
}

export function createSource(data: RSSSourceCreate) {
  return http.post<RSSSourceItem>('/sources/', data)
}

export function updateSource(id: number, data: RSSSourceUpdate) {
  return http.put<RSSSourceItem>(`/sources/${id}`, data)
}

export function deleteSource(id: number) {
  return http.delete<{ message: string }>(`/sources/${id}`)
}

export function exportSources() {
  return http.get<RSSSourceItem[]>('/sources/export', { responseType: 'json' })
}

export function importSources(data: RSSSourceCreate[]) {
  return http.post<{ message: string }>('/sources/import', data)
}

export function scanSource(sourceId: number) {
  return http.post<{ message: string; source_id: number }>(`/sources/${sourceId}/scan`)
}

export function getSourceStatus(sourceId: number) {
  return http.get<{ data: { id: number; name: string; sync_status: string; last_sync_at: string | null; error_message: string | null; item_count: number } }>(`/sources/${sourceId}/status`)
}
