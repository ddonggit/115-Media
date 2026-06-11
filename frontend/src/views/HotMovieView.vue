<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="filter-bar">
        <select v-model="filters.genre"><option value="">类型：全部</option><option v-for="g in genreOptions" :key="g.value" :value="g.value">{{ g.label }}</option></select>
        <select v-model="filters.year"><option value="">年份：全部</option><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option></select>
        <select v-model="filters.country"><option value="">国家：全部</option><option v-for="c in countryOptions" :key="c.value" :value="c.value">{{ c.label }}</option></select>
        <select v-model="filters.rating"><option value="">评分 ≥</option><option value="9">9+</option><option value="8">8+</option><option value="7">7+</option></select>
        <select v-model="filters.language"><option value="">语言：全部</option><option value="zh">中文</option><option value="en">英语</option><option value="ja">日语</option><option value="ko">韩语</option></select>
        <select v-model="filters.sort"><option value="popularity.desc">排序：热门</option><option value="vote_average.desc">评分</option><option value="primary_release_date.desc">年份</option></select>
      </div>
      <div v-if="!items.length" style="padding:40px;text-align:center;color:var(--text3)">暂无热门影片</div>
      <div class="poster-grid">
        <div v-for="(m, i) in items" :key="m.id" class="poster-card">
          <div class="poster-img">
            <img v-if="m.poster_path" :src="posterUrl(m.poster_path)" :alt="m.title || m.name" loading="lazy" />
            <span v-else>{{ emoji[i % emoji.length] }}</span>
            <div class="overlay">
              <button class="ov-primary" @click="openSub(m)">订阅</button>
              <button class="ov-secondary" @click="openTmdb(m)">TMDB</button>
            </div>
          </div>
          <div class="poster-info">
            <div class="p-title">{{ m.title || m.name }}</div>
            <div class="p-sub"><span>{{ (m.release_date || m.first_air_date || '').slice(0, 4) }} · ⭐{{ m.vote_average?.toFixed(1) }}</span><span>tmdb:{{ m.id }}</span></div>
          </div>
        </div>
      </div>
      <div v-if="totalPages > 1" class="pagination">
        <button class="btn-ghost btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">← 上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button class="btn-ghost btn-sm" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页 →</button>
      </div>
    </div>

    <!-- Subscribe Modal -->
    <div class="modal-overlay" :class="{ active: showSubModal }">
      <div class="modal" style="max-width:440px">
        <h2>订阅 · {{ subForm.media_name }}</h2>
        <div class="form-group"><label>TMDB ID</label><input type="text" :value="subForm.tmdb_id" readonly /></div>
        <div class="form-row">
          <div class="form-group" style="flex:1"><label>画质</label>
            <select v-model="subForm.quality">
              <option value="1080p">1080p</option>
              <option value="4k">4K</option>
              <option value="bluray">BluRay</option>
              <option value="bluray+4k">BluRay+4K</option>
            </select>
          </div>
          <div class="form-group" style="flex:1"><label>升级策略</label>
            <select v-model="subForm.upgrade_strategy">
              <option value="coexist">共存</option>
              <option value="skip">跳过</option>
              <option value="max_size">大的优先</option>
              <option value="min_size">小的优先</option>
            </select>
          </div>
        </div>
        <template v-if="props.type === 'tv'">
          <div class="form-row">
            <div class="form-group" style="flex:1"><label>季</label><input type="number" v-model.number="subForm.season" min="1" /></div>
            <div class="form-group" style="flex:1"><label>起始集</label><input type="number" v-model.number="subForm.episode_start" min="1" /></div>
            <div class="form-group" style="flex:1"><label>截止集</label><input type="number" v-model.number="subForm.episode_end" min="1" placeholder="不限" /></div>
          </div>
        </template>
        <div v-if="subError" style="color:var(--red);font-size:var(--fs-12);margin-top:8px">{{ subError }}</div>
        <div v-if="subOk" style="color:var(--green);font-size:var(--fs-12);margin-top:8px">订阅成功 ✅</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeSub">取消</button>
          <button class="btn-glass" @click="saveSub" :disabled="savingSub">{{ savingSub ? '保存中...' : '保存订阅' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { getHotMovie, getHotTv, getGenres } from '@/api/hot'
import { createSubscription } from '@/api/subscriptions'
import type { HotMediaItem } from '@/api/types'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const props = withDefaults(defineProps<{ type?: 'movie' | 'tv' }>(), { type: 'movie' })

const loading = ref(true)
const items = ref<HotMediaItem[]>([])
const page = ref(1)
const totalPages = ref(1)

const filters = reactive({
  genre: (route.query.genre as string) || '',
  year: (route.query.year as string) || '',
  country: (route.query.country as string) || '',
  rating: (route.query.rating as string) || '',
  language: (route.query.language as string) || '',
  sort: (route.query.sort as string) || 'popularity.desc',
})

const genreOptions = ref<{ value: string; label: string }[]>([])
const yearOptions = Array.from({ length: 10 }, (_, i) => String(new Date().getFullYear() - i))
const emoji = ['🎬', '📽️', '🎞️', '🍿', '🎥', '📀', '💿', '📺', '🎭', '🎪']

// ── Subscribe Modal ──
const showSubModal = ref(false)
const savingSub = ref(false)
const subError = ref('')
const subOk = ref(false)
const subForm = reactive({
  tmdb_id: 0,
  media_name: '',
  media_type: props.type as 'movie' | 'tv',
  year: null as number | null,
  quality: '4k' as string,
  upgrade_strategy: 'coexist' as string,
  season: 1,
  episode_start: 1,
  episode_end: null as number | null,
})

function openSub(m: HotMediaItem) {
  subForm.tmdb_id = m.id
  subForm.media_name = (m.title || m.name || '').trim()
  subForm.media_type = props.type
  subForm.year = parseInt((m.release_date || m.first_air_date || '').slice(0, 4)) || null
  subForm.quality = '4k'
  subForm.upgrade_strategy = 'coexist'
  subForm.season = 1
  subForm.episode_start = 1
  subForm.episode_end = null
  subError.value = ''
  subOk.value = false
  showSubModal.value = true
}

function closeSub() {
  showSubModal.value = false
}

async function saveSub() {
  if (!subForm.tmdb_id || !subForm.media_name) return
  savingSub.value = true
  subError.value = ''
  subOk.value = false
  try {
    const payload: any = {
      tmdb_id: subForm.tmdb_id,
      media_name: subForm.media_name,
      media_type: subForm.media_type,
      quality: subForm.quality,
      upgrade_strategy: subForm.upgrade_strategy,
      year: subForm.year,
      include_hd_keyword: true,
    }
    if (subForm.media_type === 'tv') {
      payload.season = subForm.season
      payload.episode_start = subForm.episode_start
      payload.episode_end = subForm.episode_end || undefined
    }
    await createSubscription(payload as any)
    subOk.value = true
    setTimeout(() => { closeSub() }, 1000)
  } catch (err: any) {
    subError.value = err?.response?.data?.detail || '保存失败'
  } finally {
    savingSub.value = false
  }
}

function openTmdb(m: HotMediaItem) {
  window.open(`https://www.themoviedb.org/${props.type}/${m.id}`, '_blank')
}

function posterUrl(path: string, size = 'w500') {
  return `/api/v1/hot/img?path=${encodeURIComponent(path)}&size=${size}`
}

const countryOptions = [
  { value: 'US', label: 'US-美国' },
  { value: 'CN', label: 'CN-中国' },
  { value: 'JP', label: 'JP-日本' },
  { value: 'KR', label: 'KR-韩国' },
  { value: 'GB', label: 'GB-英国' },
  { value: 'FR', label: 'FR-法国' },
  { value: 'HK', label: 'HK-香港' },
  { value: 'TW', label: 'TW-台湾' },
]

function goPage(p: number) {
  page.value = p
  fetchMovies()
}

async function fetchMovies() {
  loading.value = true
  try {
    const params: Record<string, string | number | undefined> = {
      page: page.value,
      sort: filters.sort || 'popularity.desc',
    }
    if (filters.genre) params.genre = filters.genre
    if (filters.year) params.year = filters.year
    if (filters.country) params.country = filters.country
    if (filters.rating) params['vote_average.gte'] = filters.rating
    if (filters.language) params.language = filters.language

    const res = props.type === 'movie' ? await getHotMovie(params) : await getHotTv(params)
    items.value = res.data.data
    page.value = res.data.page
    totalPages.value = res.data.total_pages

    const q: Record<string, string> = {}
    for (const [k, v] of Object.entries(filters)) {
      if (v) q[k] = v
    }
    router.replace({ query: q })
  } catch (e) {
    console.error('Failed to load hot', props.type, e)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  page.value = 1
  fetchMovies()
})

onMounted(async () => {
  try {
    const genresRes = await getGenres()
    const genreList = genresRes.data.data[props.type === 'movie' ? 'movie' : 'tv'] || []
    genreOptions.value = genreList.map((g: any) => ({ value: String(g.id), label: `${g.id}-${g.name}` }))
  } catch { /* ignore */ }
  await fetchMovies()
})
</script>
