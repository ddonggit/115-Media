<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">RSS 源</div>
        <div style="display:flex;gap:8px">
          <button class="btn-ghost btn-sm" @click="exportSources">📤 导出</button>
          <input type="file" accept=".json" ref="fileInput" style="display:none" @change="importSources" />
          <button class="btn-ghost btn-sm" @click="clickFileInput">📥 导入</button>
          <button class="btn-accent" @click="openAddModal">+ 添加源</button>
        </div>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:2fr 1.5fr 0.8fr 0.8fr 0.8fr 0.8fr 1fr">
          <span>名称</span><span>URL</span><span>分类</span><span>状态</span><span>条目</span><span>同步</span><span>操作</span>
        </div>
        <div v-for="s in sources" :key="s.id" class="tr" style="grid-template-columns:2fr 1.5fr 0.8fr 0.8fr 0.8fr 0.8fr 1fr">
          <span>{{ s.name }}</span>
          <span style="font-size:var(--fs-12);color:var(--text3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ s.url }}</span>
          <span><span class="tag" :class="'tag-' + s.category">{{ s.category }}</span></span>
          <span><span class="status-badge" :class="s.enabled ? 's-running' : 's-wait'">{{ s.enabled ? '启用' : '停用' }}</span></span>
          <span>{{ s.item_count }}</span>
          <span style="font-size:var(--fs-12)">{{ s.sync_status }}</span>
          <span class="sub-actions">
            <button class="btn-ghost btn-sm" @click="editSource(s)">编辑</button>
            <button class="btn-ghost btn-sm" @click="toggleSource(s)">{{ s.enabled ? '停用' : '启用' }}</button>
            <button class="btn-ghost btn-sm" style="color:var(--red)" @click="deleteSourceAction(s.id)">删除</button>
          </span>
        </div>
        <div v-if="sources.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无 RSS 源</div>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal" style="max-width:500px">
        <h2>{{ editingId ? '编辑源' : '添加 RSS 源' }}</h2>
        <div class="form-group"><label>名称 <span class="req">*</span></label><input type="text" v-model="form.name" /></div>
        <div class="form-group"><label>URL <span class="req">*</span></label><input type="text" v-model="form.url" placeholder="https://bt4gprx.com/search?q=...&page=rss" /></div>
        <div class="form-row">
          <div class="form-group" style="flex:1"><label>分类</label><select v-model="form.category"><option value="movie">电影</option><option value="tv">剧集</option></select></div>
          <div class="form-group" style="flex:1"><label>集数</label><input type="number" v-model.number="form.episode" min="0" /></div>
          <div class="form-group" style="flex:1"><label>季数</label><input type="number" v-model.number="form.season" min="0" /></div>
        </div>
        <div class="form-group"><label>包含关键词</label><input type="text" v-model="form.include_keywords" placeholder="逗号分隔" /></div>
        <div class="form-group"><label>排除关键词</label><input type="text" v-model="form.exclude_keywords" placeholder="逗号分隔" /></div>
        <div v-if="formError" style="color:var(--red);font-size:var(--fs-12)">{{ formError }}</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeModal">取消</button>
          <button class="btn-glass" @click="save" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { listSources, createSource, updateSource, deleteSource, exportSources as apiExportSources, importSources as apiImportSources } from '@/api/sources'
import { showToast } from '@/utils/toast'
import type { RSSSourceItem } from '@/api/types'
import ConfirmModal from '@/components/ConfirmModal.vue'

const loading = ref(true)
const sources = ref<RSSSourceItem[]>([])
const showModal = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formError = ref('')

const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null
function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg; confirmCallback = cb; confirmShow.value = true
}
const fileInput = ref<HTMLInputElement>()

function clickFileInput() {
  fileInput.value?.click()
}

const form = reactive({
  name: '',
  url: '',
  category: 'tv',
  season: 0,
  episode: 0,
  include_keywords: '',
  exclude_keywords: '',
})

function openAddModal() {
  editingId.value = null
  form.name = ''
  form.url = ''
  form.category = 'tv'
  form.season = 0
  form.episode = 0
  form.include_keywords = ''
  form.exclude_keywords = ''
  formError.value = ''
  showModal.value = true
}

function editSource(s: RSSSourceItem) {
  editingId.value = s.id
  form.name = s.name
  form.url = s.url
  form.category = s.category
  form.season = s.season
  form.episode = (s as any).episode || 0
  form.include_keywords = s.include_keywords || ''
  form.exclude_keywords = s.exclude_keywords || ''
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingId.value = null
}

async function save() {
  if (!form.name || !form.url) { formError.value = '请填写名称和 URL'; return }
  saving.value = true
  formError.value = ''
  try {
    const data = {
      name: form.name,
      url: form.url,
      category: form.category as any,
      season: form.season,
      episode: form.episode,
      include_keywords: form.include_keywords || undefined,
      exclude_keywords: form.exclude_keywords || undefined,
    }
    if (editingId.value) {
      await updateSource(editingId.value, data)
    } else {
      await createSource(data)
    }
    closeModal()
    await fetchData()
  } catch (err: any) {
    formError.value = err?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleSource(s: RSSSourceItem) {
  try {
    await updateSource(s.id, { enabled: !s.enabled })
    await fetchData()
    showToast(s.enabled ? '已停用' : '已启用', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '操作失败', 'error') }
}

async function deleteSourceAction(id: number) {
  confirmAction('确定删除？', async () => {
    try { await deleteSource(id); await fetchData(); showToast('源已删除', 'success') } catch { showToast('删除失败', 'error') }
  })
}

async function exportSources() {
  try {
    const res = await apiExportSources()
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rss-sources.json'
    a.click()
    URL.revokeObjectURL(url)
    showToast('导出成功', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '导出失败', 'error') }
}

async function importSources(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  try {
    const text = await input.files[0].text()
    const data = JSON.parse(text)
    await apiImportSources(Array.isArray(data) ? data : [data])
    await fetchData()
    showToast('导入成功', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '导入失败', 'error') }
  input.value = ''
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listSources()
    sources.value = res.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

onMounted(fetchData)
</script>
