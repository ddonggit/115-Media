/** Shared API response types matching backend schemas */

export interface ApiResponse<T> {
  data: T
  message?: string
}

// ---- Auth ----
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  username: string
}

export interface CookieLoginRequest {
  cookie: string
}

export interface CookieLoginResponse {
  token: string
  username: string
  uid: string
  total_space: number
  used_space: number
}

export interface QrCodeData {
  uid: string
  time: number
  sign: string
  qrcode_url: string
  qrcode_img_url: string
}

export interface QrCodeStatus {
  status: 'scanning' | 'scanned' | 'confirmed' | 'expired' | 'cancelled'
  token?: string
  username?: string
  uid?: string
  total_space?: number
  used_space?: number
  error?: string
}

export interface UserInfo {
  username: string
  role: string
  uid?: string
  total_space?: number
  used_space?: number
}

// ---- Dashboard ----
export interface DashboardStats {
  active_subscriptions: number
  total_subscriptions: number
  today_transfers: number
  pending_organize: number
  space_usage_pct: number | null
  total_space: number
  used_space: number
  unresolved_errors: number
}

export interface ErrorLogItem {
  id: number
  level: 'error' | 'warning'
  time: string
  module: string
  title: string
  detail: string
  can_retry: boolean
  resolved: boolean
  checkpoint: string | null
  created_at: string
  updated_at: string
}

// ---- Hot ----
export interface HotMediaItem {
  id: number
  title?: string
  name?: string
  poster_path: string | null
  backdrop_path: string | null
  overview: string
  vote_average: number
  release_date?: string
  first_air_date?: string
  genre_ids: number[]
  original_language: string
  origin_country?: string[]
  popularity: number
  media_type?: string
}

export interface HotMediaResult {
  data: HotMediaItem[]
  page: number
  total_pages: number
}

export interface GenreList {
  movie: Genre[]
  tv: Genre[]
}

export interface Genre {
  id: number
  name: string
}

export interface TmdbSearchResult {
  data: HotMediaItem[]
  page: number
}

export interface TmdbDetail {
  data: Record<string, unknown>
}

// ---- Subscription ----
export interface SubscriptionItem {
  id: number
  tmdb_id: number
  media_name: string
  media_type: 'movie' | 'tv'
  year: number | null
  quality: string
  upgrade_strategy: string
  season: number | null
  episode_start: number | null
  episode_end: number | null
  episode_current: number | null
  source: string
  status: 'active' | 'paused' | 'completed'
  last_match_at: string | null
  matched_count: number
  created_at: string
  updated_at: string
}

export interface SubscriptionCreate {
  tmdb_id: number
  media_name: string
  media_type: 'movie' | 'tv'
  year?: number
  quality?: '1080p' | '4k' | 'bluray' | 'bluray+4k'
  upgrade_strategy?: 'coexist' | 'skip' | 'max_size' | 'min_size'
  season?: number
  episode_start?: number
  episode_end?: number | null
  include_hd_keyword?: boolean
}

export interface SubscriptionUpdate {
  media_name?: string
  quality?: string
  upgrade_strategy?: string
  season?: number
  episode_start?: number
  episode_end?: number | null
  status?: 'active' | 'paused' | 'completed'
  include_hd_keyword?: boolean
}

export interface SubscriptionCount {
  total: number
  active: number
}

// ---- RSS Source ----
export interface RSSSourceItem {
  id: number
  name: string
  url: string
  category: 'movie' | 'tv' | 'anime'
  provider: string
  enabled: boolean
  season: number
  include_keywords: string | null
  exclude_keywords: string | null
  sync_status: string
  last_sync_at: string | null
  error_message: string | null
  item_count: number
  created_at: string
  updated_at: string
}

export interface RSSSourceCreate {
  name: string
  url: string
  category: 'movie' | 'tv' | 'anime'
  provider?: string
  enabled?: boolean
  season?: number
  include_keywords?: string
  exclude_keywords?: string
}

export interface RSSSourceUpdate {
  name?: string
  url?: string
  category?: string
  enabled?: boolean
  season?: number
  include_keywords?: string
  exclude_keywords?: string
}

// ---- Transfer ----
export interface TransferTaskItem {
  id: number
  transfer_type: string
  url: string
  target_dir: string
  auto_organize: boolean
  media_name: string | null
  tmdb_id: number | null
  size: string | null
  status: 'submitted' | 'submit_failed' | 'done' | 'download_failed'
  progress: number | null
  error_message: string | null
  download_retry_count: number
  max_download_retry: number
  next_download_retry_at: string | null
  submitted_at: string | null
  expires_at: string | null
  submit_retry_count: number
  max_submit_retry: number
  next_submit_retry_at: string | null
  created_at: string
  updated_at: string
}

export interface TransferTaskCreate {
  transfer_type?: string
  url: string
  target_dir: string
  auto_organize?: boolean
  media_name?: string
  tmdb_id?: number
  size?: string
}

// ---- Sync ----
export interface SyncRecordItem {
  id: number
  type: 'full' | 'incremental'
  status: string
  progress: number
  started_at: string
  finished_at: string | null
  checkpoint_cid: string | null
  current_path: string | null
  total_files: number
  scanned_files: number
  errors: string | null
  can_resume: boolean
  created_at: string
  updated_at: string
}

// ---- Media File ----
export interface MediaFileItem {
  id: number
  cid: string
  file_name: string
  file_path: string
  file_size: number
  is_dir: boolean
  media_type: string
  tmdb_id: number | null
  year: number | null
  resolution: string | null
  version: string | null
  country: string | null
  effect: string | null
  source: string | null
  video_codec: string | null
  audio_codec: string | null
  fps: string | null
  recognized: boolean
  organized: boolean
  retry_count: number
  created_at: string
  updated_at: string
}

export interface FileBrowseResult {
  files: MediaFileItem[]
  path: string
  path_parts?: { name: string; cid: string }[]
  cid: string
}

// ---- Organize ----
export interface OrganizeRuleItem {
  id: number
  name: string
  priority: number
  media_type: 'movie' | 'tv'
  genre_ids: string | null
  original_language: string | null
  origin_country: string | null
  target_cid: string
  rename_pattern: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface OrganizeRuleCreate {
  name: string
  priority?: number
  media_type: 'movie' | 'tv'
  genre_ids?: string
  original_language?: string
  origin_country?: string
  target_cid: string
  rename_pattern: string
  enabled?: boolean
}

export interface OrganizeRuleUpdate {
  name?: string
  priority?: number
  media_type?: string
  genre_ids?: string
  original_language?: string
  origin_country?: string
  target_cid?: string
  rename_pattern?: string
  enabled?: boolean
}

export interface OrganizeConfigItem {
  id: number
  source_cid: string
  duplicate_cid: string
  processed_cid: string
  created_at: string
  updated_at: string
}

export interface OrganizeConfigCreate {
  source_cid: string
  duplicate_cid: string
  processed_cid: string
}

// ---- Config ----
export interface Account115Item {
  id: number
  uid: string | null
  username: string | null
  total_space: number | null
  used_space: number | null
  expire_time: string | null
  created_at: string
  updated_at: string
}

export interface Account115Create {
  cookie: string
  uid?: string
  username?: string
  total_space?: number
  used_space?: number
  expire_time?: string
}

export interface TmdbConfigItem {
  id: number
  api_key: string
  language: string
  base_url: string
  image_base_url: string
  created_at: string
  updated_at: string
}

export interface TmdbConfigCreate {
  api_key: string
  language?: string
  base_url?: string
  image_base_url?: string
}

export interface StrmConfigItem {
  id: number
  strm_base_url: string
  media_library_path: string
  auto_generate: boolean
  created_at: string
  updated_at: string
}

export interface StrmConfigCreate {
  strm_base_url: string
  media_library_path: string
  auto_generate?: boolean
}

export interface StrmConfigUpdate {
  strm_base_url?: string
  media_library_path?: string
  auto_generate?: boolean
}

// ---- Config - Transfer / Subscription (extra config endpoints) ---
export interface TransferConfig {
  max_submit_retry: number
  submit_retry_interval_seconds: number
  max_download_retry: number
  max_wait_days: number
}

export interface SubscriptionConfig {
  rss_check_interval_minutes: number
}

// ---- Logs ----
export interface OperationLogItem {
  id: number
  action: string
  module: string
  level: string
  detail: string
  status: string
  error_message: string | null
  created_at: string
}

// ---- Notify ----
export interface NotifyConfigItem {
  id: number
  channel: 'feishu' | 'telegram'
  enabled: boolean
  notify_on: string | null
  created_at: string
  updated_at: string
}

export interface NotifyConfigCreate {
  channel: 'feishu' | 'telegram'
  webhook_url: string
  bot_token?: string
  chat_id?: string
  enabled?: boolean
  notify_on?: string
}

export interface NotifyConfigUpdate {
  webhook_url?: string
  bot_token?: string
  chat_id?: string
  enabled?: boolean
  notify_on?: string
}

// ---- Config Updates ----
export interface TransferConfigUpdate {
  max_submit_retry?: number
  submit_retry_interval_seconds?: number
  max_download_retry?: number
  max_wait_days?: number
}

export interface SubscriptionConfigUpdate {
  rss_check_interval_minutes?: number
}

// ---- Sync Config ----
export interface SyncConfigItem {
  id: number
  source_dir: string
  video_exts: string
  cron_expr: string | null
  created_at: string
  updated_at: string
}

export interface SyncConfigUpdate {
  source_dir?: string
  video_exts?: string
  cron_expr?: string | null
}

export interface LogStats {
  by_level: Record<string, number>
  by_module: Record<string, number>
}
