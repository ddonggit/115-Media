/** Transfers API */
import http from './axios'
import type { TransferTaskItem, TransferTaskCreate } from './types'

export function listTransfers(status?: string, limit = 50) {
  return http.get<TransferTaskItem[]>('/transfers/', { params: { status, limit } })
}

export function getTransfer(id: number) {
  return http.get<TransferTaskItem>(`/transfers/${id}`)
}

export function createTransfer(data: TransferTaskCreate) {
  return http.post<TransferTaskItem>('/transfers/', data)
}

export function retryTransfer(id: number) {
  return http.post<TransferTaskItem>(`/transfers/${id}/retry`)
}

export function cleanupTransfers() {
  return http.post<{ message: string }>('/transfers/cleanup')
}

export function deleteTransfer(id: number) {
  return http.delete<{ message: string }>(`/transfers/${id}`)
}

export function resolveUrl(url: string) {
  return http.post<{ data: { media_name: string | null; url_type: string; file_count?: number } }>('/transfers/resolve-url', { url })
}
