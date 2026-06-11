<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="s-label">📋 订阅中</div>
          <div class="s-value">{{ stats?.active_subscriptions ?? '—' }}</div>
          <div class="s-sub">共 {{ stats?.total_subscriptions ?? '—' }} 个订阅</div>
          <div class="s-icon">🎬</div>
        </div>
        <div class="stat-card">
          <div class="s-label">⬇️ 今日转存</div>
          <div class="s-value">{{ stats?.today_transfers ?? '—' }}</div>
          <div class="s-sub">待整理 {{ stats?.pending_organize ?? '—' }}</div>
          <div class="s-icon">📥</div>
        </div>
        <div class="stat-card">
          <div class="s-label">📁 待整理</div>
          <div class="s-value">{{ stats?.pending_organize ?? '—' }}</div>
          <div class="s-sub">未处理错误 {{ stats?.unresolved_errors ?? '—' }}</div>
          <div class="s-icon">🗂️</div>
        </div>
        <div class="stat-card">
          <div class="s-label">💾 115 空间</div>
          <div class="s-value">{{ spacePct }}</div>
          <div class="s-sub">{{ spaceDetail }}</div>
          <div class="s-icon">☁️</div>
        </div>
      </div>

      <!-- Flow -->
      <div class="flow-wrap">
        <div class="section-title">自动化流程</div>
        <div class="flow">
          <div class="flow-step done"><div class="f-icon">📋</div><div class="f-label">订阅</div></div><div class="flow-arrow">→</div>
          <div class="flow-step done"><div class="f-icon">📡</div><div class="f-label">RSS 匹配</div></div><div class="flow-arrow">→</div>
          <div class="flow-step done"><div class="f-icon">⬇️</div><div class="f-label">转存</div></div><div class="flow-arrow">→</div>
          <div class="flow-step" :class="{ active: (stats?.pending_organize ?? 0) > 0 }"><div class="f-icon">📁</div><div class="f-label">整理</div></div><div class="flow-arrow">→</div>
          <div class="flow-step"><div class="f-icon">🏠</div><div class="f-label">入库</div></div><div class="flow-arrow">→</div>
          <div class="flow-step"><div class="f-icon">🔔</div><div class="f-label">通知</div></div>
        </div>
      </div>

      <!-- Error cards -->
      <div class="section-hdr"><div class="section-title">错误卡片</div></div>
      <div v-if="errors.length === 0" style="padding:32px;text-align:center;color:var(--text3)">✅ 暂无错误</div>
      <div v-for="err in errors" :key="err.id" class="error-card" :class="{ warning: err.level === 'warning' }">
        <div class="ec-left">
          <div class="ec-title">{{ err.level === 'error' ? '❌' : '⚠️' }} {{ err.title }}</div>
          <div class="ec-detail">{{ err.detail }}</div>
          <div class="ec-meta">{{ err.module }} · {{ formatTime(err.time) }}</div>
        </div>
        <div class="ec-actions">
          <button v-if="err.can_retry" class="btn-ghost btn-sm" style="color:var(--primary)" @click="handleRetry(err.id)">🔄 重试</button>
          <button v-if="!err.resolved" class="btn-ghost btn-sm" @click="handleResolve(err.id)">已解决</button>
        </div>
      </div>

      <!-- Recent media -->
      <div class="section-hdr" style="margin-top:20px">
        <div class="section-title">最近处理</div>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:3fr 1.2fr 1.2fr 1fr 1.2fr">
          <span>项目</span><span>类型</span><span>状态</span><span>数量</span><span>时间</span>
        </div>
        <div v-for="item in recentItems" :key="item.id" class="tr" style="grid-template-columns:3fr 1.2fr 1.2fr 1fr 1.2fr">
          <span>{{ item.title }}</span>
          <span><span class="tag" :class="item.tagClass">{{ item.module }}</span></span>
          <span><span class="status-badge" :class="item.status === 'success' ? 's-done' : item.status === 'failed' ? 's-error' : 's-running'">{{ item.status }}</span></span>
          <span>{{ item.action }}</span>
          <span>{{ formatTime(item.time) }}</span>
        </div>
        <div v-if="recentItems.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无处理记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getStats, getErrors, resolveError, retryError } from '@/api/dashboard'
import { showToast } from '@/utils/toast'
import type { DashboardStats, ErrorLogItem } from '@/api/types'
import { formatTime } from '@/utils/format'
import { useWebSocket } from '@/api/websocket'

const loading = ref(true)
const stats = ref<DashboardStats | null>(null)
const errors = ref<ErrorLogItem[]>([])

const spacePct = computed(() => {
  if (!stats.value?.total_space) return '—'
  return formatBytes(stats.value.total_space)
})

const spaceDetail = computed(() => {
  if (!stats.value?.total_space) return '未获取'
  const remain = stats.value.total_space - stats.value.used_space
  return `剩余 ${formatBytes(remain > 0 ? remain : 0)}`
})

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return size.toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

const recentItems = computed(() => {
  // Derive recent items from error logs (most recent first)
  return errors.value.slice(0, 6).map(e => ({
    id: e.id,
    title: e.title,
    module: e.module,
    tagClass: 'tag-' + e.module,
    status: e.resolved ? 'success' : e.level === 'error' ? 'failed' : 'running',
    action: e.can_retry ? '可重试' : '待处理',
    time: e.time,
  }))
})



async function handleRetry(id: number) {
  try {
    await retryError(id)
    await fetchData()
    showToast('操作已加入重试队列', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '重试失败', 'error') }
}

async function handleResolve(id: number) {
  try {
    await resolveError(id)
    await fetchData()
    showToast('错误已标记为已解决', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '操作失败', 'error') }
}

async function fetchData() {
  try {
    const [statsRes, errRes] = await Promise.all([getStats(), getErrors()])
    stats.value = statsRes.data.data
    errors.value = errRes.data
  } catch (e) {
    console.error('Failed to load dashboard data', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  const ws = useWebSocket()
  ws.connect()
  ws.on('transfer.progress', () => fetchData())
  ws.on('transfer.done', () => fetchData())
  ws.on('transfer.failed', () => fetchData())
  ws.on('transfer.cleanup', () => fetchData())
})

onUnmounted(() => {})
</script>
