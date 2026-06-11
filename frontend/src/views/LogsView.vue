<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">操作日志</div>
        <div style="display:flex;gap:8px">
          <select v-model="filters.module" @change="fetchData" style="width:120px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg2);color:var(--text)">
            <option value="">全部模块</option>
            <option v-for="m in modules" :key="m" :value="m">{{ moduleLabel(m) }}</option>
          </select>
          <select v-model="filters.level" @change="fetchData" style="width:100px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg2);color:var(--text)">
            <option value="">全部级别</option>
            <option value="info">信息</option>
            <option value="warning">警告</option>
            <option value="error">错误</option>
          </select>
          <select v-model="filters.range" @change="fetchData" style="width:120px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg2);color:var(--text)">
            <option value="24h">24小时内</option>
            <option value="7d">7天内</option>
            <option value="30d">30天内</option>
            <option value="all">全部</option>
          </select>
          <button class="btn-ghost btn-sm" style="color:var(--red)" @click="clearAll">清空日志</button>
        </div>
      </div>
      <!-- Stats bar -->
      <div v-if="stats" class="stats-bar" style="display:flex;gap:16px;margin-bottom:16px;padding:12px 16px;background:var(--glass-bg);border-radius:8px;font-size:var(--fs-12)">
        <span>📊 统计: </span>
        <span v-for="(v,k) in stats.by_level" :key="k"><span class="status-badge" :class="k==='error'?'s-error':k==='warning'?'s-wait':'s-done'" style="margin-right:4px">{{ levelLabel(k) }}</span> {{ v }}</span>
        <span style="margin-left:auto;color:var(--text3)">模块: {{ Object.keys(stats.by_module).length }}</span>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:1.2fr 1fr 1fr 3fr 0.8fr 1.2fr">
          <span>时间</span><span>模块</span><span>级别</span><span>详情</span><span>状态</span><span>操作</span>
        </div>
        <div v-for="log in logs" :key="log.id" class="tr" style="grid-template-columns:1.2fr 1fr 1fr 3fr 0.8fr 1.2fr">
          <span style="font-size:var(--fs-12)">{{ formatTime(log.created_at) }}</span>
          <span><span class="tag" :class="'tag-' + (log.module || 'unknown')">{{ moduleLabel(log.module) }}</span></span>
          <span><span class="status-badge" :class="log.level === 'error' ? 's-error' : log.level === 'warning' ? 's-wait' : 's-done'">{{ levelLabel(log.level) }}</span></span>
          <span style="font-size:var(--fs-12);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ log.detail }}</span>
          <span style="font-size:var(--fs-12)">{{ statusLabel(log.status) }}</span>
          <span style="font-size:var(--fs-12)">{{ actionLabel(log.action) }}</span>
        </div>
        <div v-if="logs.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无日志</div>
      </div>
    </div>
    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { listLogs, clearLogs, getLogModules, getLogStats } from '@/api/logs'
import { showToast } from '@/utils/toast'
import type { OperationLogItem, LogStats } from '@/api/types'
import { formatTime } from '@/utils/format'
import { useLogWebSocket } from '@/api/websocket'
import ConfirmModal from '@/components/ConfirmModal.vue'

const loading = ref(true)
const logs = ref<OperationLogItem[]>([])
const modules = ref<string[]>([])
const stats = ref<LogStats | null>(null)

const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null
function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg; confirmCallback = cb; confirmShow.value = true
}

const filters = reactive({ module: '', level: '', range: '24h' })

const moduleMap: Record<string, string> = {
  auth: '认证', sync: '同步', organize: '整理', transfer: '转存',
  config: '配置', subscription: '订阅', sources: '源管理',
}
function moduleLabel(m: string) { return moduleMap[m] || m }
function levelLabel(l: string) { return ({ debug: '调试', info: '信息', warning: '警告', error: '错误' } as Record<string, string>)[l] || l }
function statusLabel(s: string) { return ({ success: '成功', failed: '失败', warning: '警告' } as Record<string, string>)[s] || s }
const actionMap: Record<string, string> = {
  login: '登录', cookie_login: 'Cookie 登录', save_115_config: '保存 115 配置',
  strm_generate: '生成 STRM', run_organize: '执行整理', start_organize: '启动整理',
  create_subscription: '创建订阅', delete_subscription: '删除订阅',
  start_full_sync: '启动全量同步', start_incremental_sync: '启动增量同步',
  scan_source: '扫描 RSS 源', create_transfer: '创建转存', delete_transfer: '删除转存',
}
function actionLabel(a: string) { return actionMap[a] || a }

async function fetchData() {
  loading.value = true
  try {
    const r = await listLogs({
      module: filters.module || undefined,
      level: filters.level || undefined,
      range: filters.range,
      limit: 100,
    })
    logs.value = r.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function clearAll() {
  confirmAction('确定清空所有日志？', async () => {
    try { await clearLogs(); await fetchData(); showToast('日志已清空', 'success') } catch { showToast('清空失败', 'error') }
  })
}

const logWs = useLogWebSocket()

onMounted(async () => {
  loading.value = true
  try {
    const [logRes, modRes, statsRes] = await Promise.all([
      listLogs({ range: '24h', limit: 100 }),
      getLogModules().catch(() => ({ data: { data: [] } })),
      getLogStats().catch(() => null),
    ])
    logs.value = logRes.data
    modules.value = modRes.data.data || []
    if (statsRes?.data?.data) stats.value = statsRes.data.data
  } catch { /* ignore */ }
  finally { loading.value = false }

  logWs.on('log.new', (data: OperationLogItem) => {
    logs.value.unshift(data)
    if (logs.value.length > 200) logs.value.pop()
    if (stats.value) {
      const level = data.level || 'info'
      stats.value.by_level[level] = (stats.value.by_level[level] || 0) + 1
      const mod = data.module || 'unknown'
      stats.value.by_module[mod] = (stats.value.by_module[mod] || 0) + 1
    }
  })
})

onUnmounted(() => {
  logWs.disconnect()
})
</script>
