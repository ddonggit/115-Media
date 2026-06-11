<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">数据同步</div>
        <div style="display:flex;gap:8px">
          <button class="btn-glass" @click="startFull" :disabled="syncing">{{ syncing ? '同步中...' : '全量同步' }}</button>
          <button class="btn-ghost" @click="startIncremental" :disabled="syncing">{{ syncing ? '同步中...' : '增量同步' }}</button>
        </div>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:1.2fr 1fr 1fr 1.5fr 1.5fr 1fr">
          <span>类型</span><span>状态</span><span>进度</span><span>扫描</span><span>开始时间</span><span>操作</span>
        </div>
        <div v-for="r in records" :key="r.id" class="tr" style="grid-template-columns:1.2fr 1fr 1fr 1.5fr 1.5fr 1fr">
          <span><span class="tag" :class="r.type === 'full' ? 'tag-hua' : 'tag-ri'">{{ r.type === 'full' ? '全量' : '增量' }}</span></span>
          <span><span class="status-badge" :class="statusClass(r.status)">{{ r.status }}</span></span>
          <span>{{ r.progress }}%</span>
          <span style="font-size:var(--fs-12)">{{ r.scanned_files }}/{{ r.total_files }} 文件</span>
          <span style="font-size:var(--fs-12)">{{ formatTime(r.started_at) }}</span>
          <span>
            <button v-if="r.can_resume && r.status === 'interrupted'" class="btn-ghost btn-sm" @click="resume(r.id)">🔄 恢复</button>
          </span>
        </div>
        <div v-if="records.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无同步记录</div>
      </div>

      <!-- Sync Config -->
      <div class="glass-card">
        <div class="section-title" style="margin-bottom:12px">⚙️ 同步配置</div>
        <div class="form-row" style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
          <div class="form-group"><label>源目录 (cid)</label><input type="text" v-model="syncConfig.source_dir" placeholder="0" /></div>
          <div class="form-group"><label>视频扩展名</label><input type="text" v-model="syncConfig.video_exts" placeholder=".mkv,.mp4" /></div>
        </div>
        <div class="form-group"><label>Cron 表达式 (可选)</label><input type="text" v-model="syncConfig.cron_expr" placeholder="留空 = 手动同步" /></div>
        <button class="btn-ghost" @click="saveSyncConfig" :disabled="savingConfig">{{ savingConfig ? '保存中...' : '保存配置' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { listSyncRecords, startFullSync, startIncrementalSync, resumeSync, getSyncConfig, updateSyncConfig } from '@/api/sync'
import { showToast } from '@/utils/toast'
import type { SyncRecordItem, SyncConfigItem } from '@/api/types'
import { formatTime } from '@/utils/format'

const loading = ref(true)
const syncing = ref(false)
const savingConfig = ref(false)
const records = ref<SyncRecordItem[]>([])
const syncConfig = reactive({ source_dir: '/', video_exts: '.mkv,.mp4,.avi,.ts', cron_expr: '' })

function statusClass(s: string) {
  return s === 'completed' ? 's-done' : s === 'running' ? 's-running' : s === 'interrupted' ? 's-error' : 's-wait'
}

async function startFull() {
  syncing.value = true
  try { await startFullSync(); await fetchData(); showToast('全量同步已启动', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '启动失败', 'error') }
  finally { syncing.value = false }
}

async function startIncremental() {
  syncing.value = true
  try { await startIncrementalSync(); await fetchData(); showToast('增量同步已启动', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '启动失败', 'error') }
  finally { syncing.value = false }
}

async function resume(id: number) {
  try { await resumeSync(id); await fetchData(); showToast('同步已恢复', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '恢复失败', 'error') }
}

async function saveSyncConfig() {
  savingConfig.value = true
  try {
    await updateSyncConfig({
      source_dir: syncConfig.source_dir || '/',
      video_exts: syncConfig.video_exts || '.mkv,.mp4,.avi,.ts',
      cron_expr: syncConfig.cron_expr || null,
    })
    showToast('同步配置已保存', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '保存失败', 'error') }
  finally { savingConfig.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listSyncRecords()
    records.value = res.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

onMounted(async () => {
  loading.value = true
  try {
    const [recordsRes, cfgRes] = await Promise.all([
      listSyncRecords(),
      getSyncConfig().catch(() => null),
    ])
    records.value = recordsRes.data
    if (cfgRes?.data) {
      syncConfig.source_dir = cfgRes.data.source_dir || '/'
      syncConfig.video_exts = cfgRes.data.video_exts || '.mkv,.mp4,.avi,.ts'
      syncConfig.cron_expr = cfgRes.data.cron_expr || ''
    }
  } catch { /* ignore */ }
  finally { loading.value = false }
})
</script>
