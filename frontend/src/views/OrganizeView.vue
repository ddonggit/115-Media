<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <!-- Tabs -->
      <div class="tab-bar" style="margin-bottom:16px">
        <button class="tab-btn" :class="{ active: tab === 'rules' }" @click="tab = 'rules'">分类规则</button>
        <button class="tab-btn" :class="{ active: tab === 'records' }" @click="tab = 'records'; fetchRecords()">整理记录</button>
        <button class="tab-btn" :class="{ active: tab === 'config' }" @click="tab = 'config'">整理配置</button>
      </div>

      <!-- Rules -->
      <div v-if="tab === 'rules'">
        <div class="section-hdr">
          <div class="section-title">分类规则（按优先级从上到下匹配）</div>
          <button class="btn-accent" @click="openRuleModal">+ 添加规则</button>
        </div>
        <div class="data-table">
          <div class="th" style="grid-template-columns:0.5fr 2fr 1fr 1.5fr 1fr 1.5fr 0.8fr">
            <span>优先级</span><span>名称</span><span>类型</span><span>条件</span><span>目标 cid</span><span>重命名</span><span>操作</span>
          </div>
          <div v-for="r in rules" :key="r.id" class="tr" style="grid-template-columns:0.5fr 2fr 1fr 1.5fr 1fr 1.5fr 0.8fr">
            <span>{{ r.priority }}</span>
            <span>{{ r.name }}</span>
            <span><span class="tag">{{ r.media_type }}</span></span>
            <span style="font-size:var(--fs-12);color:var(--text3)">{{ ruleCond(r) }}</span>
            <span style="font-size:var(--fs-11)">
              <div style="color:var(--text2);margin-bottom:2px">{{ cidLabel(r.target_cid).name }}</div>
              <div style="color:var(--text3)">{{ r.target_cid }}</div>
            </span>
            <span style="font-size:var(--fs-11);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ r.rename_pattern }}</span>
            <span class="sub-actions">
              <button class="btn-ghost btn-sm" @click="editRule(r)">编辑</button>
              <button class="btn-ghost btn-sm" style="color:var(--red)" @click="deleteRuleAction(r.id)">删除</button>
            </span>
          </div>
          <div v-if="rules.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无规则</div>
        </div>
        <div style="margin-top:12px">
          <button class="btn-glass" @click="runOrganize">▶ 执行整理</button>
        </div>
      </div>

      <!-- Records -->
      <div v-if="tab === 'records'">
        <div class="section-hdr">
          <div class="section-title">整理记录</div>
          <input type="text" v-model="searchQuery" placeholder="🔍 搜索文件名..." style="width:200px;padding:6px 10px;border:1px solid var(--border);border-radius:4px;background:var(--bg2);color:var(--text)" />
        </div>
        <div class="data-table">
          <div class="th" style="grid-template-columns:2.5fr 0.7fr 1fr 1fr 1.2fr 1fr">
            <span>文件名</span><span>大小</span><span>状态</span><span>TMDB</span><span>详情</span><span>时间</span>
          </div>
          <div v-for="f in records" :key="f.id" class="tr" style="grid-template-columns:2.5fr 0.7fr 1fr 1fr 1.2fr 1fr">
            <span style="font-size:var(--fs-12);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ f.file_name }}</span>
            <span style="font-size:var(--fs-12)">{{ formatSize(f.file_size) }}</span>
            <span>
              <span v-if="f.organized" class="status-badge s-done">已整理</span>
              <span v-else-if="f.retry_count > 0" class="status-badge s-error">失败({{ f.retry_count }})</span>
              <span v-else-if="f.recognized" class="status-badge s-running">已识别</span>
              <span v-else class="status-badge s-wait">待处理</span>
            </span>
            <span style="font-size:var(--fs-12)">
              <template v-if="f.tmdb_id">{{ f.tmdb_id }}</template>
              <template v-else>
                <input type="number" v-model.number="fixTmdbId[f.id]" placeholder="ID" style="width:70px;padding:3px 6px;border:1px solid var(--border);border-radius:3px;background:var(--bg2);color:var(--text)" />
                <button class="btn-ghost btn-sm" @click="fixFile(f.id)">修正</button>
              </template>
            </span>
            <span style="font-size:var(--fs-12)">{{ [f.year, f.resolution].filter(Boolean).join(' ') }}</span>
            <span style="font-size:var(--fs-12)">{{ formatTime(f.updated_at) }}</span>
          </div>
          <div v-if="records.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无整理记录</div>
        </div>
      </div>

      <!-- Config -->
      <div v-if="tab === 'config'">
        <div class="section-title" style="margin-bottom:16px">整理目录配置</div>
        <div class="form-group"><label>源文件夹 cid <span class="req">*</span></label><input type="text" v-model="orgConfig.source_cid" placeholder="云下载目录 cid" /><div class="hint" v-if="orgConfig.source_cid">📁 {{ cidLabel(orgConfig.source_cid).name }}</div></div>
        <div class="form-group"><label>重名文件夹 cid <span class="req">*</span></label><input type="text" v-model="orgConfig.duplicate_cid" placeholder="重名整理目录 cid" /><div class="hint" v-if="orgConfig.duplicate_cid">📁 {{ cidLabel(orgConfig.duplicate_cid).name }}</div></div>
        <div class="form-group"><label>已整理文件夹 cid <span class="req">*</span></label><input type="text" v-model="orgConfig.processed_cid" placeholder="已整理目录 cid" /><div class="hint" v-if="orgConfig.processed_cid">📁 {{ cidLabel(orgConfig.processed_cid).name }}</div></div>
        <div class="status-badge" style="margin:8px 0;color:var(--text3)">整理操作不会删除任何文件，仅在三个目录间移动</div>
        <button class="btn-glass" @click="saveConfig" :disabled="savingConfig">{{ savingConfig ? '保存中...' : '保存配置' }}</button>
      </div>
    </div>

    <!-- Rule modal -->
    <div class="modal-overlay" :class="{ active: showRuleModal }">
      <div class="modal" style="max-width:540px">
        <h2>{{ editingRuleId ? '编辑规则' : '添加规则' }}</h2>
        <div class="form-group"><label>名称 <span class="req">*</span></label><input type="text" v-model="ruleForm.name" /></div>
        <div class="form-row">
          <div class="form-group" style="flex:1"><label>类型</label><select v-model="ruleForm.media_type"><option value="movie">movie</option><option value="tv">tv</option></select></div>
          <div class="form-group" style="flex:1"><label>优先级</label><input type="number" v-model.number="ruleForm.priority" /></div>
        </div>
        <div class="form-group"><label>TMDB 类型 ID（逗号分隔）</label><input type="text" v-model="ruleForm.genre_ids" placeholder="如 16,99（留空=不限）" /></div>
        <div class="form-group"><label>语言（逗号分隔）</label><input type="text" v-model="ruleForm.original_language" placeholder="如 zh,en（留空=不限）" /></div>
        <div class="form-group"><label>国家（逗号分隔）</label><input type="text" v-model="ruleForm.origin_country" placeholder="如 CN,HK（留空=不限）" /></div>
        <div class="form-group"><label>目标 cid <span class="req">*</span></label><input type="text" v-model="ruleForm.target_cid" /><div class="hint" v-if="ruleForm.target_cid">📁 {{ cidLabel(ruleForm.target_cid).name }}</div></div>
        <div class="form-group"><label>重命名模板</label><input type="text" v-model="ruleForm.rename_pattern" /></div>
        <div v-if="ruleError" style="color:var(--red);font-size:var(--fs-12)">{{ ruleError }}</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeRuleModal">取消</button>
          <button class="btn-glass" @click="saveRule" :disabled="savingRule">{{ savingRule ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { listRules, createRule, updateRule, deleteRule, runOrganize as apiRunOrganize, listOrganizeRecords as apiListOrganizeRecords, fixFile as apiFixFile, getOrganizeConfig, saveOrganizeConfig } from '@/api/organize'
import { showToast } from '@/utils/toast'
import { formatTime } from '@/utils/format'
import { resolveCid as apiResolveCid } from '@/api/files'
import type { OrganizeRuleItem, MediaFileItem, OrganizeConfigItem } from '@/api/types'
import { useCidCacheStore } from '@/store/cidCache'
import ConfirmModal from '@/components/ConfirmModal.vue'

const loading = ref(true)
const tab = ref('rules')
const rules = ref<OrganizeRuleItem[]>([])
const records = ref<MediaFileItem[]>([])
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
const fixTmdbId = reactive<Record<number, number>>({})
const orgConfig = reactive<OrganizeConfigItem>({ id: 0, source_cid: '', duplicate_cid: '', processed_cid: '', created_at: '', updated_at: '' })
const savingConfig = ref(false)

// Rule modal
const showRuleModal = ref(false)
const editingRuleId = ref<number | null>(null)
const savingRule = ref(false)
const ruleError = ref('')

const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null
function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg; confirmCallback = cb; confirmShow.value = true
}
const ruleForm = reactive({
  name: '', media_type: 'movie', priority: 0, genre_ids: '',
  original_language: '', origin_country: '', target_cid: '', rename_pattern: '{title}.{year}<.{resolution}><.{source}>',
})

const cidCache = useCidCacheStore()
async function resolveCidName(cid: string) {
  if (!cid || cidCache.names[cid] === '加载中...') return
  if (cidCache.names[cid] && cidCache.names[cid] !== '获取失败') return
  cidCache.set(cid, '加载中...')
  try {
    const res = await apiResolveCid(cid)
    cidCache.set(cid, res.data.name)
  } catch {
    cidCache.set(cid, '获取失败')
  }
}
function cidLabel(cid: string): { name: string } {
  return { name: cidCache.names[cid] || '' }
}
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchRecords, 300)
})
watch(() => orgConfig.source_cid, (v) => { if (v) resolveCidName(v) })
watch(() => orgConfig.duplicate_cid, (v) => { if (v) resolveCidName(v) })
watch(() => orgConfig.processed_cid, (v) => { if (v) resolveCidName(v) })
watch(() => ruleForm.target_cid, (v) => { if (v) resolveCidName(v) })

function ruleCond(r: OrganizeRuleItem) {
  const parts: string[] = []
  if (r.genre_ids) parts.push('类型:' + r.genre_ids)
  if (r.original_language) parts.push('语言:' + r.original_language)
  if (r.origin_country) parts.push('国家:' + r.origin_country)
  return parts.join(', ') || '（全部匹配-兜底）'
}

function openRuleModal() {
  editingRuleId.value = null
  ruleForm.name = ''
  ruleForm.media_type = 'movie'
  ruleForm.priority = rules.value.length
  ruleForm.genre_ids = ''
  ruleForm.original_language = ''
  ruleForm.origin_country = ''
  ruleForm.target_cid = ''
  ruleForm.rename_pattern = '{title}.{year}<.{resolution}><.{source}>'
  ruleError.value = ''
  showRuleModal.value = true
}

function editRule(r: OrganizeRuleItem) {
  editingRuleId.value = r.id
  ruleForm.name = r.name
  ruleForm.media_type = r.media_type
  ruleForm.priority = r.priority
  ruleForm.genre_ids = r.genre_ids || ''
  ruleForm.original_language = r.original_language || ''
  ruleForm.origin_country = r.origin_country || ''
  ruleForm.target_cid = r.target_cid
  ruleForm.rename_pattern = r.rename_pattern
  ruleError.value = ''
  showRuleModal.value = true
}

function closeRuleModal() { showRuleModal.value = false; editingRuleId.value = null }

async function saveRule() {
  if (!ruleForm.name || !ruleForm.target_cid) { ruleError.value = '请填写名称和目标 cid'; return }
  savingRule.value = true
  ruleError.value = ''
  try {
    const data = { ...ruleForm, genre_ids: ruleForm.genre_ids || undefined, original_language: ruleForm.original_language || undefined, origin_country: ruleForm.origin_country || undefined }
    if (editingRuleId.value) {
      await updateRule(editingRuleId.value, data)
    } else {
      await createRule(data as any)
    }
    closeRuleModal()
    await fetchRules()
  } catch (err: any) { ruleError.value = err?.response?.data?.detail || '保存失败' }
  finally { savingRule.value = false }
}

async function deleteRuleAction(id: number) {
  confirmAction('确定删除此规则？', async () => {
    try { await deleteRule(id); await fetchRules(); showToast('规则已删除', 'success') } catch { showToast('删除失败', 'error') }
  })
}

async function runOrganize() {
  try { await apiRunOrganize(); showToast('整理任务已加入队列', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '启动整理失败', 'error') }
}

async function fixFile(fileId: number) {
  const tmdbId = fixTmdbId[fileId]
  if (!tmdbId) return
  try {
    await apiFixFile(fileId, tmdbId)
    await fetchRecords()
    showToast('TMDB ID 已修正', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '修正失败', 'error') }
}

async function saveConfig() {
  savingConfig.value = true
  try {
    await saveOrganizeConfig({ source_cid: orgConfig.source_cid, duplicate_cid: orgConfig.duplicate_cid, processed_cid: orgConfig.processed_cid })
    showToast('整理配置已保存', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '保存失败', 'error') }
  finally { savingConfig.value = false }
}

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0; let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return size.toFixed(1) + ' ' + units[i]
}

async function fetchRules() { const r = await listRules(); rules.value = r.data }
async function fetchRecords() {
  try {
    const r = await apiListOrganizeRecords({ q: searchQuery.value || undefined })
    records.value = r.data
  } catch { /* ignore */ }
}
async function fetchConfig() {
  try {
    const r = await getOrganizeConfig()
    if (r.data) Object.assign(orgConfig, r.data)
  } catch { /* ignore */ }
}

onMounted(async () => {
  loading.value = true
  try { await Promise.all([fetchRules(), fetchRecords(), fetchConfig()]) } catch { /* ignore */ }
  finally { loading.value = false }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>
