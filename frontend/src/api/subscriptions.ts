/** Subscriptions API */
import http from './axios'
import type { SubscriptionItem, SubscriptionCreate, SubscriptionUpdate, SubscriptionCount } from './types'

export function listSubscriptions(status?: string, mediaType?: string) {
  return http.get<SubscriptionItem[]>('/subscriptions/', {
    params: { status, media_type: mediaType },
  })
}

export function getSubscription(id: number) {
  return http.get<SubscriptionItem>(`/subscriptions/${id}`)
}

export function createSubscription(data: SubscriptionCreate) {
  return http.post<SubscriptionItem>('/subscriptions/', data)
}

export function updateSubscription(id: number, data: SubscriptionUpdate) {
  return http.put<SubscriptionItem>(`/subscriptions/${id}`, data)
}

export function deleteSubscription(id: number) {
  return http.delete<{ message: string }>(`/subscriptions/${id}`)
}

export function getSubscriptionCount() {
  return http.get<{ data: SubscriptionCount }>('/subscriptions/stats/count')
}

export function searchTmdbForSubscription(query: string) {
  return http.get<{ data: Array<{ tmdb_id: number; title: string; year: string; media_type: string; rating: number }> }>('/subscriptions/tmdb/search', { params: { q: query } })
}
