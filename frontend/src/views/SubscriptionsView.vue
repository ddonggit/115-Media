<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <!-- Tab bar -->
      <div class="tab-bar" style="margin-bottom:16px">
        <button class="tab-btn" :class="{ active: tab === 'subscriptions' }" @click="tab = 'subscriptions'">📋 订阅管理</button>
        <button class="tab-btn" :class="{ active: tab === 'sources' }" @click="tab = 'sources'">📡 RSS 源</button>
      </div>

      <div v-if="tab === 'subscriptions'">
      <div class="section-hdr">
        <div class="section-title">订阅管理</div>
        <div style="display:flex;gap:8px">
          <div class="search-box" style="width:220px"><span>🔍</span><input type="text" v-model="searchQuery" placeholder="搜索 TMDB..." @input="searchTmdb" /></div>
        </div>
      </div>

      <!-- TMDB search dropdown -->
      <div v-if="searchQuery.trim()" class="search-dropdown">
        <div v-if="tmdbResults.length > 0">
          <div v-for="r in tmdbResults" :key="r.id" class="search-item" @click="fillFromTmdb(r)">
            <span>{{ r.title || r.name }} ({{ (r.release_date || r.first_air_date || '').slice(0, 4) }}) tmdb:{{ r.id }}</span>
            <span class="tag" style="margin-left:8px">{{ r.media_type || 'movie' }}</span>
          </div>
        </div>
        <div v-else class="search-item" style="color:var(--text3);cursor:default">无匹配结果</div>
      </div>

      <div class="data-table">
        <div class="th" style="grid-template-columns:2.5fr 1fr 1fr 1fr 1fr 1fr 1fr">
          <span>影片名称 (tmdb_id)</span><span>类型</span><span>画质</span><span>策略</span><span>状态</span><span>匹配数</span><span>操作</span>
        </div>
        <div v-for="sub in subscriptions" :key="sub.id" class="tr" style="grid-template-columns:2.5fr 1fr 1fr 1fr 1fr 1fr 1fr">
          <span>{{ sub.media_name }} (tmdb:{{ sub.tmdb_id }})</span>
          <span><span class="tag" :class="mediaTag(sub.media_type)">{{ sub.media_type === 'movie' ? '电影' : '剧集' }}</span></span>
          <span>{{ sub.quality }}</span>
          <span style="font-size:var(--fs-12);color:var(--text3)">{{ sub.upgrade_strategy }}</span>
          <span><span class="status-badge" :class="statusClass(sub.status)">{{ statusLabel(sub) }}</span></span>
          <span>{{ sub.matched_count }}{{ sub.episode_current ? ' E' + sub.episode_current : '' }}</span>
          <span class="sub-actions">
            <button class="btn-ghost btn-sm" @click="editSub(sub)">编辑</button>
            <button v-if="sub.status === 'active'" class="btn-ghost btn-sm" @click="toggleStatus(sub, 'paused')">暂停</button>
            <button v-else-if="sub.status === 'paused'" class="btn-ghost btn-sm" @click="toggleStatus(sub, 'active')">激活</button>
            <button class="btn-ghost btn-sm" style="color:var(--red)" @click="deleteSub(sub.id)">删除</button>
          </span>
        </div>
        <div v-if="subscriptions.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无订阅</div>
      </div>
    </div>

    <!-- Add/Edit Subscription Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal" style="max-width:520px">
        <h2>{{ editingId ? '编辑订阅' : '添加订阅' }}</h2>
        <div class="form-group">
          <label>TMDB ID <span class="req">*</span></label>
          <input type="number" v-model.number="form.tmdb_id" placeholder="输入 TMDB ID" />
        </div>
        <div class="form-group">
          <label>影片名称 <span class="req">*</span></label>
          <input type="text" v-model="form.media_name" placeholder="输入影片名称" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1">
            <label>类型 <span class="req">*</span></label>
            <select v-model="form.media_type">
              <option value="movie">movie 电影</option>
              <option value="tv">tv 剧集</option>
            </select>
          </div>
          <div class="form-group" style="flex:1">
            <label>画质 <span class="req">*</span></label>
            <select v-model="form.quality">
              <option value="1080p">1080p</option>
              <option value="4k">4K</option>
              <option value="bluray">bluray</option>
              <option value="bluray+4k">bluray+4K</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>洗版策略</label>
          <select v-model="form.upgrade_strategy">
            <option value="coexist">coexist — 新旧共存</option>
            <option value="skip">skip — 已有不下载</option>
            <option value="max_size">max_size — 保留最大</option>
            <option value="min_size">min_size — 保留最小</option>
          </select>
        </div>
        <template v-if="form.media_type === 'tv'">
          <div class="form-row">
            <div class="form-group" style="flex:1">
              <label>季数</label>
              <input type="number" v-model.number="form.season" min="1" />
            </div>
            <div class="form-group" style="flex:1">
              <label>起始集</label>
              <input type="number" v-model.number="form.episode_start" min="1" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group" style="flex:1">
              <label>结束集（留空=无限跟进）</label>
              <input type="number" v-model.number="form.episode_end" placeholder="留空不限" />
            </div>
            <div class="form-group" style="flex:1">
              <label>包含高清关键词 <input type="checkbox" v-model="form.include_hd_keyword" /></label>
            </div>
          </div>
        </template>
        <div class="form-group" v-if="form.media_type === 'movie'">
          <label>包含高清关键词 <input type="checkbox" v-model="form.include_hd_keyword" /></label>
        </div>
        <div v-if="formError" style="color:var(--red);font-size:var(--fs-12);margin-bottom:8px">{{ formError }}</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeModal">取消</button>
          <button class="btn-glass" @click="saveSub" :disabled="saving">{{ saving ? '保存中...' : (editingId ? '更新' : '创建订阅') }}</button>
        </div>
      </div>
      </div>

      <SourcesView v-if="tab === 'sources'" />

    </div>

    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { listSubscriptions, createSubscription, updateSubscription, deleteSubscription } from '@/api/subscriptions'
import { tmdbSearch } from '@/api/hot'
import { showToast } from '@/utils/toast'
import type { SubscriptionItem, SubscriptionCreate } from '@/api/types'
import ConfirmModal from '@/components/ConfirmModal.vue'
import SourcesView from '@/views/SourcesView.vue'

const route = useRoute()

const loading = ref(true)
const tab = ref<'subscriptions' | 'sources'>('subscriptions')
const subscriptions = ref<SubscriptionItem[]>([])
const searchQuery = ref('')
const tmdbResults = ref<any[]>([])
const showModal = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formError = ref('')
const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null

function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg
  confirmCallback = cb
  confirmShow.value = true
}

const form = reactive<{
  tmdb_id: number | null
  media_name: string
  media_type: 'movie' | 'tv'
  quality: string
  upgrade_strategy: string
  season: number | null
  episode_start: number | null
  episode_end: number | null
  include_hd_keyword: boolean
}>({
  tmdb_id: null,
  media_name: '',
  media_type: 'movie',
  quality: 'bluray',
  upgrade_strategy: 'coexist',
  season: null,
  episode_start: null,
  episode_end: null,
  include_hd_keyword: true,
})

function mediaTag(type: string) {
  return type === 'movie' ? 'tag-ou' : 'tag-hua'
}

function statusClass(s: string) {
  return s === 'active' ? 's-running' : s === 'paused' ? 's-wait' : 's-done'
}

function statusLabel(sub: SubscriptionItem) {
  if (sub.status === 'active') return sub.media_type === 'tv' ? '跟进中' : '等待匹配'
  if (sub.status === 'paused') return '已暂停'
  return '已完成'
}

async function searchTmdb() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  tmdbResults.value = []
  try {
    const res = await tmdbSearch(searchQuery.value.trim())
    tmdbResults.value = res.data.data?.slice(0, 8) || []
  } catch (e) {
    console.error('TMDB search failed', e)
  } finally {
    loading.value = false
  }
}

function fillFromTmdb(item: any) {
  form.tmdb_id = item.id
  form.media_name = item.title || item.name || ''
  form.media_type = item.media_type || 'movie'
  tmdbResults.value = []
  searchQuery.value = form.media_name
}

function openAddModal() {
  editingId.value = null
  form.tmdb_id = route.query.tmdb_id ? Number(route.query.tmdb_id) : null
  form.media_name = (route.query.media_name as string) || ''
  form.media_type = (route.query.media_type as 'movie' | 'tv') || 'movie'
  form.quality = 'bluray'
  form.upgrade_strategy = 'coexist'
  form.season = null
  form.episode_start = null
  form.episode_end = null
  form.include_hd_keyword = true
  formError.value = ''
  showModal.value = true
}

function editSub(sub: SubscriptionItem) {
  editingId.value = sub.id
  form.tmdb_id = sub.tmdb_id
  form.media_name = sub.media_name
  form.media_type = sub.media_type
  form.quality = sub.quality
  form.upgrade_strategy = sub.upgrade_strategy
  form.season = sub.season
  form.episode_start = sub.episode_start
  form.episode_end = sub.episode_end
  form.include_hd_keyword = true
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingId.value = null
}

async function saveSub() {
  if (!form.tmdb_id || !form.media_name) {
    formError.value = '请填写 TMDB ID 和影片名称'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    if (editingId.value) {
      await updateSubscription(editingId.value, {
        media_name: form.media_name,
        quality: form.quality,
        upgrade_strategy: form.upgrade_strategy,
        season: form.season ?? undefined,
        episode_start: form.episode_start ?? undefined,
        episode_end: form.episode_end ?? undefined,
        include_hd_keyword: form.include_hd_keyword,
      })
    } else {
      const payload: SubscriptionCreate = {
        tmdb_id: form.tmdb_id,
        media_name: form.media_name,
        media_type: form.media_type,
        quality: form.quality as any,
        upgrade_strategy: form.upgrade_strategy as any,
        include_hd_keyword: form.include_hd_keyword,
      }
      if (form.media_type === 'tv') {
        payload.season = form.season ?? undefined
        payload.episode_start = form.episode_start ?? undefined
        payload.episode_end = form.episode_end ?? undefined
      }
      await createSubscription(payload)
    }
    closeModal()
    await fetchData()
  } catch (err: any) {
    formError.value = err?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleStatus(sub: SubscriptionItem, newStatus: 'active' | 'paused') {
  try {
    await updateSubscription(sub.id, { status: newStatus })
    await fetchData()
    showToast(newStatus === 'active' ? '订阅已激活' : '订阅已暂停', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '操作失败', 'error') }
}

async function deleteSub(id: number) {
  confirmAction('确定删除此订阅？', async () => {
    try {
      await deleteSubscription(id)
      await fetchData()
      showToast('订阅已删除', 'success')
    } catch { showToast('删除失败', 'error') }
  })
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listSubscriptions()
    subscriptions.value = res.data
  } catch (e) {
    console.error('Failed to load subscriptions', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.search-dropdown {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 12px;
  max-height: 320px;
  overflow-y: auto;
}
.search-item {
  padding: 10px 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: var(--fs-13);
}
.search-item:hover {
  background: var(--hover);
}
</style>
