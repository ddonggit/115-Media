/** Files (115 Cloud Browser) API */
import http from './axios'
import type { ApiResponse, FileBrowseResult, MediaFileItem } from './types'

export function browseFiles(cid = '0') {
  return http.get<ApiResponse<FileBrowseResult>>('/files/browse', { params: { cid } })
}

export function resolveCid(cid: string) {
  return http.get<{cid: string, name: string}>('/files/resolve', { params: { cid } })
}

export function searchFiles(q: string, limit = 50) {
  return http.get<MediaFileItem[]>('/files/search', { params: { q, limit } })
}

export function getFile(cid: string) {
  return http.get<ApiResponse<MediaFileItem>>(`/files/${cid}`)
}
