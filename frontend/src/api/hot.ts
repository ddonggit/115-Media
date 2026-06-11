/** Hot / TMDB API */
import http from './axios'
import type { ApiResponse, HotMediaResult, GenreList, TmdbSearchResult, TmdbDetail } from './types'

export function getHotMovie(params?: Record<string, string | number | undefined>) {
  return http.get<HotMediaResult>('/hot/movie', { params })
}

export function getHotTv(params?: Record<string, string | number | undefined>) {
  return http.get<HotMediaResult>('/hot/tv', { params })
}

export function getGenres() {
  return http.get<ApiResponse<GenreList>>('/hot/genres')
}

export function tmdbSearch(query: string, page = 1) {
  return http.get<TmdbSearchResult>('/tmdb/search', { params: { query, page } })
}

export function tmdbDetail(mediaType: string, tmdbId: number) {
  return http.get<TmdbDetail>(`/tmdb/${mediaType}/${tmdbId}`)
}
