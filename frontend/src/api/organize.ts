/** Organize API */
import http from './axios'
import type { MediaFileItem, OrganizeRuleItem, OrganizeRuleCreate, OrganizeRuleUpdate, OrganizeConfigItem, OrganizeConfigCreate } from './types'

export function listUnrecognized() {
  return http.get<MediaFileItem[]>('/organize/unrecognized')
}

export function listOrganizeRecords(params?: { q?: string; limit?: number }) {
  return http.get<MediaFileItem[]>('/organize/records', { params })
}

export function fixFile(fileId: number, tmdbId: number) {
  return http.post<MediaFileItem>(`/organize/fix/${fileId}`, null, { params: { tmdb_id: tmdbId } })
}

export function listRules() {
  return http.get<OrganizeRuleItem[]>('/organize/rules')
}

export function createRule(data: OrganizeRuleCreate) {
  return http.post<OrganizeRuleItem>('/organize/rules', data)
}

export function updateRule(ruleId: number, data: OrganizeRuleUpdate) {
  return http.put<OrganizeRuleItem>(`/organize/rules/${ruleId}`, data)
}

export function deleteRule(ruleId: number) {
  return http.delete<{ message: string }>(`/organize/rules/${ruleId}`)
}

export function reorderRules(ruleIds: number[]) {
  return http.post<{ message: string }>('/organize/reorder', { rule_ids: ruleIds })
}

export function runOrganize() {
  return http.post<{ message: string }>('/organize/run')
}

export function getOrganizeConfig() {
  return http.get<OrganizeConfigItem | null>('/organize/config')
}

export function saveOrganizeConfig(data: OrganizeConfigCreate) {
  return http.post<OrganizeConfigItem>('/organize/config', data)
}
