/** Config API */
import http from './axios'
import type { AxiosRequestConfig } from 'axios'
import type { Account115Item, Account115Create, TmdbConfigItem, TmdbConfigCreate, StrmConfigItem, StrmConfigCreate, StrmConfigUpdate, TransferConfig, TransferConfigUpdate, SubscriptionConfig, SubscriptionConfigUpdate } from './types'

export function get115Config(config?: AxiosRequestConfig) {
  return http.get<Account115Item | null>('/config/115', config)
}

export function save115Config(data: Account115Create) {
  return http.put<Account115Item>('/config/115', data)
}

export function renew115Cookie() {
  return http.post<{ message: string; uid?: string }>('/config/115/renew')
}

export function verify115Cookie(cookie: string) {
  return http.post<{ valid: boolean; uid: string; username: string; total_space: number; used_space: number }>('/config/115/verify', { cookie })
}

export function getTmdbConfig(config?: AxiosRequestConfig) {
  return http.get<TmdbConfigItem | null>('/config/tmdb', config)
}

export function saveTmdbConfig(data: TmdbConfigCreate) {
  return http.put<TmdbConfigItem>('/config/tmdb', data)
}

export function patchTmdbConfig(data: Partial<TmdbConfigCreate>) {
  return http.patch<TmdbConfigItem>('/config/tmdb', data)
}

export function getStrmConfig(config?: AxiosRequestConfig) {
  return http.get<StrmConfigItem | null>('/config/strm', config)
}

export function saveStrmConfig(data: StrmConfigCreate) {
  return http.put<StrmConfigItem>('/config/strm', data)
}

export function triggerStrmGenerate() {
  return http.post<{ message: string }>('/config/strm/generate')
}

export function getTransferConfig(config?: AxiosRequestConfig) {
  return http.get<TransferConfig>('/config/transfer', config)
}

export function updateTransferConfig(data: TransferConfigUpdate) {
  return http.put<TransferConfig>('/config/transfer', data)
}

export function getSubscriptionConfig(config?: AxiosRequestConfig) {
  return http.get<SubscriptionConfig>('/config/subscription', config)
}

export function updateSubscriptionConfig(data: SubscriptionConfigUpdate) {
  return http.put<SubscriptionConfig>('/config/subscription', data)
}
