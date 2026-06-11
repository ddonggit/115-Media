<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">转存任务</div>
        <div style="display:flex;gap:8px">
          <div class="form-group" style="margin:0;width:140px"><select v-model="statusFilter" @change="fetchData">
            <option value="">全部状态</option>
            <option value="submitted">已提交</option>
            <option value="submit_failed">提交失败</option>
            <option value="done">已完成</option>
            <option value="download_failed">下载失败</option>
          </select></div>
          <button class="btn-ghost btn-sm" @click="cleanupExpired">🧹 清理过期</button>
          <button class="btn-accent" @click="openAddModal">+ 新建转存</button>
        </div>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:2.5fr 1.5fr 1fr 1fr 1fr 0.8fr">
          <span>媒体/链接</span><span>目标目录</span><span>状态</span><span>重试</span><span>提交时间</span><span>操作</span>
        </div>
        <div v-for="t in transfers" :key="t.id" class="tr" style="grid-template-columns:2.5fr 1.5fr 1fr 1fr 1fr 0.8fr">
          <span>
            <div>{{ t.media_name || '—' }}</div>
            <div style="font-size:var(--fs-11);color:var(--text3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px">{{ t.url }}</div>
          </span>
          <span style="font-size:var(--fs-12)">{{ t.target_dir }}</span>
          <span><span class="status-badge" :class="statusClass(t.status)">{{ statusLabel(t.status) }}</span></span>
          <span style="font-size:var(--fs-12)">提交{{ t.submit_retry_count }}/{{ t.max_submit_retry }} 下载{{ t.download_retry_count }}/{{ t.max_download_retry }}</span>
          <span style="font-size:var(--fs-12)">{{ formatTime(t.submitted_at) }}</span>
          <span>
            <button v-if="t.status === 'submit_failed' || t.status === 'download_failed'" class="btn-ghost btn-sm" @click="retry(t.id)">🔄 重试</button>
            <button class="btn-ghost btn-sm" style="color:var(--red)" @click="confirmDelete(t.id)">删除</button>
          </span>
        </div>
        <div v-if="transfers.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无转存任务</div>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal" style="max-width:500px">
        <h2>新建转存</h2>
        <div class="form-group">
          <label>磁力链接 <span class="req">*</span></label>
          <input type="text" v-model="form.url" placeholder="magnet:?xt=urn:btih:..." />
        </div>
        <div class="form-group">
          <label>目标目录 <span class="req">*</span></label>
          <input type="text" v-model="form.target_dir" placeholder="/云下载/影片名" />
        </div>
        <div class="form-group">
          <label>媒体名称</label>
          <input type="text" v-model="form.media_name" placeholder="可选" />
        </div>
        <div class="form-group">
          <label>整理完成后自动入库 <input type="checkbox" v-model="form.auto_organize" /></label>
        </div>
        <div v-if="formError" style="color:var(--red);font-size:var(--fs-12)">{{ formError }}</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeModal">取消</button>
          <button class="btn-glass" @click="save" :disabled="saving">{{ saving ? '提交中...' : '提交转存' }}</button>
        </div>
      </div>
    </div>

    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { listTransfers, createTransfer, retryTransfer, cleanupTransfers, deleteTransfer, resolveUrl } from '@/api/transfers'
import { showToast } from '@/utils/toast'
import type { TransferTaskItem } from '@/api/types'
import { formatTime } from '@/utils/format'
import { useWebSocket } from '@/api/websocket'
import ConfirmModal from '@/components/ConfirmModal.vue'

const loading = ref(true)
const transfers = ref<TransferTaskItem[]>([])
const statusFilter = ref('')
const showModal = ref(false)
const saving = ref(false)
const formError = ref('')
const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null

const form = reactive({
  url: '',
  target_dir: '',
  media_name: '',
  auto_organize: true,
})

function statusClass(s: string) {
  return s === 'done' ? 's-done' : s === 'submitted' ? 's-running' : s === 'submit_failed' ? 's-error' : 's-error'
}
function statusLabel(s: string) {
  return s === 'done' ? '已完成' : s === 'submitted' ? '已提交' : s === 'submit_failed' ? '提交失败' : '下载失败'
}

function openAddModal() {
  form.url = ''
  form.target_dir = '/云下载'
  form.media_name = ''
  form.auto_organize = true
  formError.value = ''
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function save() {
  if (!form.url || !form.target_dir) { formError.value = '请填写链接和目标目录'; return }
  saving.value = true
  formError.value = ''
  try {
    await createTransfer({
      url: form.url,
      target_dir: form.target_dir,
      media_name: form.media_name || undefined,
      auto_organize: form.auto_organize,
    })
    closeModal()
    await fetchData()
  } catch (err: any) {
    formError.value = err?.response?.data?.detail || '提交失败'
  } finally { saving.value = false }
}

async function retry(id: number) {
  try { await retryTransfer(id); await fetchData(); showToast('已加入重试队列', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '重试失败', 'error') }
}

function confirmDelete(id: number) {
  confirmAction('确定删除此转存任务？', async () => {
    try { await deleteTransfer(id); await fetchData(); showToast('转存任务已删除', 'success') } catch { showToast('删除失败', 'error') }
  })
}

function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg
  confirmCallback = cb
  confirmShow.value = true
}

async function cleanupExpired() {
  confirmAction('确定清理所有过期转存任务？', async () => {
    try { await cleanupTransfers(); await fetchData(); showToast('已清理过期转存', 'success') } catch { showToast('清理失败', 'error') }
  })
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listTransfers(statusFilter.value || undefined)
    transfers.value = res.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

watch(() => form.url, async (val) => {
  if (!val) return
  try {
    const res = await resolveUrl(val)
    if (res.data.data.media_name) {
      form.media_name = res.data.data.media_name
    }
  } catch { /* ignore */ }
})

onMounted(() => {
  fetchData()
  // Connect WebSocket and listen for transfer events
  const ws = useWebSocket()
  ws.connect()
  ws.on('transfer.progress', () => fetchData())
  ws.on('transfer.done', () => fetchData())
  ws.on('transfer.failed', () => fetchData())
  ws.on('transfer.retry', () => fetchData())
  ws.on('transfer.cleanup', () => fetchData())
})

onUnmounted(() => {
  // WebSocket stays connected globally; just stop listening
})
</script>
