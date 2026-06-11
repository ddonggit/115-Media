/** Cache API */
import http from './axios'

export function clearSyncCache() {
  return http.post<{ message: string }>('/cache/clear/sync')
}

export function clearTmdbCache() {
  return http.post<{ message: string }>('/cache/clear/tmdb')
}

export function clearEventsCache() {
  return http.post<{ message: string }>('/cache/clear/events')
}

export function clearAllCaches() {
  return http.post<{ message: string }>('/cache/clear/all')
}
