/** Sync API */
import http from './axios'
import type { SyncRecordItem, SyncConfigItem, SyncConfigUpdate } from './types'

export function listSyncRecords() {
  return http.get<SyncRecordItem[]>('/sync/')
}

export function startFullSync() {
  return http.post<SyncRecordItem>('/sync/full')
}

export function startIncrementalSync() {
  return http.post<SyncRecordItem>('/sync/incremental')
}

export function resumeSync(recordId: number) {
  return http.post<SyncRecordItem>(`/sync/resume/${recordId}`)
}

export function getSyncConfig() {
  return http.get<SyncConfigItem>('/sync/config')
}

export function updateSyncConfig(data: SyncConfigUpdate) {
  return http.put<SyncConfigItem>('/sync/config', data)
}
