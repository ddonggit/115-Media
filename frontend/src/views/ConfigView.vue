<template>
  <div>
    <div v-if="loading" class="loading-wrap">
      <div class="loading-spinner"></div><div>加载中...</div>
      <button v-if="loadErr" class="btn-ghost btn-sm" style="margin-top:8px" @click="loadConfig">🔄 重试</button>
    </div>
    <div v-else>
      <!-- 115 Config -->
      <div class="config-section">
        <div class="section-title">☁️ 115 网盘配置</div>

        <!-- Account status card -->
        <div v-if="accountInfo" class="account-card">
          <div class="account-header">
            <span class="account-label">115 账号状态</span>
            <span class="account-badge"
              :class="accountInfo.uid ? 'active' : 'inactive'">
              {{ accountInfo.uid ? '已登录' : '未登录' }}
            </span>
          </div>
          <div class="account-details" v-if="accountInfo.uid">
            <div class="detail-row"><span class="detail-key">UID</span><span class="detail-val">{{ accountInfo.uid }}</span></div>
            <div class="detail-row" v-if="accountInfo.username"><span class="detail-key">用户名</span><span class="detail-val">{{ accountInfo.username }}</span></div>
            <div class="detail-row" v-if="accountInfo.total_space"><span class="detail-key">总空间</span><span class="detail-val">{{ formatBytes(accountInfo.total_space) }}</span></div>
            <div class="detail-row" v-if="accountInfo.used_space"><span class="detail-key">已用</span><span class="detail-val">{{ formatBytes(accountInfo.used_space) }} ({{ usagePct }}%)</span></div>
          </div>
          <div class="account-hint" v-else>请通过登录页扫码或粘贴 Cookie 登录 115 账号</div>
        </div>

        <div class="form-group">
          <label>Cookie</label>
          <input type="password" v-model="form115.cookie" :placeholder="form115.uid ? '已保存 (重新输入将覆盖)' : '粘贴 115 Cookie'" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1"><label>UID</label><input type="text" v-model="form115.uid" placeholder="可选" /></div>
          <div class="form-group" style="flex:1"><label>用户名</label><input type="text" v-model="form115.username" placeholder="可选" /></div>
        </div>
        <button class="btn-glass" @click="save115" :disabled="saving115">{{ saving115 ? '保存中...' : '保存' }}</button>
        <span v-if="save115Msg" class="save-msg" :class="save115MsgOk ? 'save-ok' : 'save-err'">{{ save115Msg }}</span>

        <!-- QR code login -->
        <div class="qr-login-area">
          <button class="btn-ghost btn-sm" @click="qrExpanded = !qrExpanded">
            {{ qrExpanded ? '隐藏' : '📱 扫码登录 115' }}
          </button>
          <button class="btn-ghost btn-sm" style="margin-left:8px" @click="renewCookie">🔄 续期 Cookie</button>
          <div v-if="qrExpanded" class="qr-section">
            <div v-if="qrLoading" class="qr-placeholder-sm">⏳ 正在生成二维码...</div>
            <div v-else-if="qrImgUrl" class="qr-wrapper-sm">
              <img :src="qrImgUrl" class="qr-img-sm" alt="扫码登录" />
              <div class="qr-hint-sm">请使用 115 手机客户端扫码</div>
              <button class="btn-ghost btn-sm" style="margin-top:4px" @click="startQrLogin">🔄 重新生成</button>
            </div>
            <div v-else-if="qrErrorMsg" class="qr-error-sm">{{ qrErrorMsg }}</div>
            <div v-else class="qr-placeholder-sm" @click="startQrLogin">点击生成二维码</div>
            <div v-if="qrStatusText" class="qr-status-sm" :class="{ confirmed: qrConfirmed }">{{ qrStatusText }}</div>
          </div>
        </div>
      </div>

      <!-- TMDB + STRM -->
      <div style="display:flex;gap:16px;margin-bottom:16px">
        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">🎬 TMDB 配置</div>
          <div class="form-group"><label>API Key <span class="req">*</span></label><input type="password" v-model="formTmdb.api_key" placeholder="输入 TMDB API Key" /></div>
          <div class="form-row">
            <div class="form-group" style="flex:1"><label>语言</label><select v-model="formTmdb.language"><option value="zh-CN">zh-CN 中文</option><option value="en-US">en-US 英文</option><option value="ja-JP">ja-JP 日语</option></select></div>
          </div>
          <button class="btn-glass" @click="saveTmdb" :disabled="savingTmdb">{{ savingTmdb ? '保存中...' : '保存' }}</button>
          <span v-if="tmdbMsg" class="save-msg" :class="tmdbMsgOk ? 'save-ok' : 'save-err'">{{ tmdbMsg }}</span>
        </div>

        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">📁 STRM 配置</div>
          <div class="form-group"><label>STRM 基础 URL</label><input type="text" v-model="formStrm.strm_base_url" placeholder="http://localhost:8095/115" /></div>
          <div class="form-group"><label>媒体库路径</label><input type="text" v-model="formStrm.media_library_path" placeholder="/media/library" /></div>
          <div class="form-group"><label>整理后自动生成 STRM <input type="checkbox" v-model="formStrm.auto_generate" /></label></div>
          <button class="btn-glass" @click="saveStrm" :disabled="savingStrm">{{ savingStrm ? '保存中...' : '保存' }}</button>
          <button class="btn-ghost btn-sm" style="margin-left:8px" @click="triggerStrm">生成 STRM</button>
        </div>
      </div>

      <!-- Transfer + Subscription -->
      <div style="display:flex;gap:16px;margin-bottom:16px">
        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">⬇️ 转存配置</div>
          <div class="form-row">
            <div class="form-group"><label>最大提交重试</label><input type="number" v-model.number="formTransfer.max_submit_retry" min="1" max="10" /></div>
            <div class="form-group"><label>提交重试间隔(秒)</label><input type="number" v-model.number="formTransfer.submit_retry_interval_seconds" min="60" max="3600" /></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>最大下载重试</label><input type="number" v-model.number="formTransfer.max_download_retry" min="1" max="10" /></div>
            <div class="form-group"><label>最大等待天数</label><input type="number" v-model.number="formTransfer.max_wait_days" min="1" max="30" /></div>
          </div>
          <button class="btn-glass" @click="saveTransferConfig" :disabled="savingTransfer">{{ savingTransfer ? '保存中...' : '保存' }}</button>
        </div>

        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">📋 订阅配置</div>
          <div class="form-group"><label>RSS 检查间隔(分钟)</label><input type="number" v-model.number="formSubscription.rss_check_interval_minutes" min="5" max="1440" /></div>
          <button class="btn-glass" @click="saveSubscriptionConfig" :disabled="savingSubscription">{{ savingSubscription ? '保存中...' : '保存' }}</button>
        </div>
      </div>

      <!-- Font + Cache -->
      <div style="display:flex;gap:16px">
        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">🔤 字体设置</div>
          <div class="form-row">
            <div class="form-group" style="flex:1">
              <label>字体</label>
              <select v-model="fontFamily" @change="applyFontSettings">
                <option value="system">系统字体</option>
                <option value="siyuan">思源字体 (Noto Sans SC)</option>
              </select>
            </div>
            <div class="form-group" style="flex:1">
              <label>字号</label>
              <select v-model="fontSize" @change="applyFontSettings">
                <option value="small">小号</option>
                <option value="medium">中号</option>
                <option value="large">大号</option>
              </select>
            </div>
          </div>
        </div>

        <div class="config-section" style="flex:1;margin-bottom:0">
          <div class="section-title">🧹 缓存清理</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-ghost" @click="confirmCacheClear('sync')">清空同步缓存</button>
            <button class="btn-ghost" @click="confirmCacheClear('tmdb')">清空 TMDB 缓存</button>
            <button class="btn-ghost" @click="confirmCacheClear('events')">重置事件游标</button>
            <button class="btn-ghost" style="color:var(--red)" @click="confirmCacheClear('all')">清空全部缓存</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmModal :show="confirmShow" :message="confirmMsg" @confirm="confirmShow=false;confirmCallback?.()" @cancel="confirmShow=false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { get115Config, save115Config, getTmdbConfig, patchTmdbConfig, getStrmConfig, saveStrmConfig, renew115Cookie, triggerStrmGenerate, getTransferConfig, updateTransferConfig, getSubscriptionConfig, updateSubscriptionConfig } from '@/api/config'
import { clearSyncCache, clearTmdbCache, clearEventsCache, clearAllCaches } from '@/api/cache'
import { showToast } from '@/utils/toast'
import { getQrCode, checkQrCodeStatus, getAuthStatus } from '@/api/auth'
import { useAuthStore } from '@/store/auth'
import ConfirmModal from '@/components/ConfirmModal.vue'

const authStore = useAuthStore()
const loading = ref(true)
const loadErr = ref(false)
const saving115 = ref(false)
const savingTmdb = ref(false)
const tmdbMsg = ref('')
const tmdbMsgOk = ref(false)
const savingStrm = ref(false)
const savingTransfer = ref(false)
const savingSubscription = ref(false)

const fontSize = ref(localStorage.getItem('fontSize') || 'small')
const fontFamily = ref(localStorage.getItem('fontFamily') || 'system')
const confirmShow = ref(false)
const confirmMsg = ref('')
let confirmCallback: (() => void) | null = null

function confirmAction(msg: string, cb: () => void) {
  confirmMsg.value = msg
  confirmCallback = cb
  confirmShow.value = true
}

const form115 = reactive({ cookie: '', uid: '', username: '' })
const formTmdb = reactive({ api_key: '', language: 'zh-CN', base_url: 'https://api.themoviedb.org/3', image_base_url: 'https://image.tmdb.org/t/p/' })
const formStrm = reactive({ strm_base_url: '', media_library_path: '', auto_generate: true })
const formTransfer = reactive({ max_submit_retry: 3, submit_retry_interval_seconds: 600, max_download_retry: 3, max_wait_days: 7 })
const formSubscription = reactive({ rss_check_interval_minutes: 10 })

// QR login state
const qrExpanded = ref(false)
const qrLoading = ref(false)
const qrImgUrl = ref('')
const qrUid = ref('')
const qrTime = ref(0)
const qrSign = ref('')
const qrErrorMsg = ref('')
const qrStatusText = ref('')
const qrConfirmed = ref(false)
let qrPollTimer: ReturnType<typeof setInterval> | null = null

const accountInfo = computed(() => ({
  uid: authStore.uid || form115.uid,
  username: form115.username || authStore.username,
  total_space: authStore.totalSpace,
  used_space: authStore.usedSpace,
}))

const usagePct = computed(() => {
  if (!accountInfo.value.total_space) return 0
  return Math.round((accountInfo.value.used_space / accountInfo.value.total_space) * 100)
})

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

// Font settings
const SIYUAN_FONT_CSS = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap'
let _fontLink: HTMLLinkElement | null = null

function applyFontSettings() {
  const html = document.documentElement
  html.classList.remove('size-medium', 'size-large', 'font-siyuan')

  if (fontSize.value === 'medium') html.classList.add('size-medium')
  else if (fontSize.value === 'large') html.classList.add('size-large')

  if (fontFamily.value === 'siyuan') {
    html.classList.add('font-siyuan')
    if (!_fontLink) {
      _fontLink = document.createElement('link')
      _fontLink.rel = 'stylesheet'
      _fontLink.href = SIYUAN_FONT_CSS
      document.head.appendChild(_fontLink)
    }
  } else {
    if (_fontLink) { _fontLink.remove(); _fontLink = null }
  }

  localStorage.setItem('fontSize', fontSize.value)
  localStorage.setItem('fontFamily', fontFamily.value)
}

// QR code login
async function startQrLogin() {
  stopQrPolling()
  qrLoading.value = true
  qrImgUrl.value = ''
  qrUid.value = ''
  qrTime.value = 0
  qrSign.value = ''
  qrErrorMsg.value = ''
  qrStatusText.value = ''
  qrConfirmed.value = false

  try {
    const res = await getQrCode()
    const data = res.data.data
    qrUid.value = data.uid
    qrTime.value = data.time
    qrSign.value = data.sign
    qrImgUrl.value = data.qrcode_img_url
    qrStatusText.value = '📱 等待扫码...'
    startQrPolling()
  } catch (err: any) {
    qrErrorMsg.value = '生成二维码失败: ' + (err?.response?.data?.detail || err.message)
  } finally {
    qrLoading.value = false
  }
}

function startQrPolling() {
  stopQrPolling()
  // Poll every 3 seconds
  qrPollTimer = setInterval(() => {
    pollQrStatus()
  }, 3000)
}

async function pollQrStatus() {
  if (!qrUid.value) {
    stopQrPolling()
    return
  }

  try {
    const res = await checkQrCodeStatus(qrUid.value, qrTime.value, qrSign.value)
    const status = res.data.data

    if (status.status === 'confirmed' && status.token) {
      stopQrPolling()
      qrConfirmed.value = true
      qrStatusText.value = '✅ 扫码成功！'
      authStore.setToken(status.token)
      if (status.username) authStore.setUsername(status.username)
      if (status.uid) {
        authStore.setAccountInfo(status.uid, status.total_space || 0, status.used_space || 0)
        localStorage.setItem('uid', status.uid)
      }
    } else if (status.status === 'scanned') {
      qrStatusText.value = '👤 已扫码，请在手机上确认登录...'
    } else if (status.status === 'expired') {
      stopQrPolling()
      qrStatusText.value = '⏰ 二维码已过期' + (status.error ? ': ' + status.error : '') + '，点击下方重新生成'
    } else if (status.status === 'cancelled') {
      stopQrPolling()
      qrStatusText.value = '❌ 已取消，请重新生成二维码'
    } else {
      // scanning
      qrStatusText.value = '📱 等待扫码...'
    }
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 404) {
      stopQrPolling()
      qrStatusText.value = '⏰ 二维码已过期'
    } else {
      // Network error: keep polling until user explicitly stops or code expires
      qrStatusText.value = '📱 等待扫码... (网络波动)'
    }
  }
}

function stopQrPolling() {
  if (qrPollTimer) {
    clearInterval(qrPollTimer)
    qrPollTimer = null
  }
}

const save115Msg = ref('')
const save115MsgOk = ref(false)

async function save115() {
  if (!form115.cookie.trim()) {
    save115MsgOk.value = false
    save115Msg.value = '请先输入 115 Cookie'
    return
  }
  saving115.value = true
  save115Msg.value = ''
  save115MsgOk.value = false
  try {
    // Use proper cookie login flow: saves to DB, verifies, and issues JWT token
    const result = await authStore.loginWithCookie(form115.cookie)
    if (!result.ok) {
      save115MsgOk.value = false
      save115Msg.value = result.error || '115 登录失败'
      return
    }
    save115MsgOk.value = true
    form115.uid = authStore.uid
    form115.username = authStore.username
    save115Msg.value = `Cookie 有效 ✅ — UID: ${authStore.uid}，用户名: ${authStore.username}`
    setTimeout(() => { if (save115MsgOk.value) save115Msg.value = '' }, 5000)
  } catch (err: any) {
    save115MsgOk.value = false
    save115Msg.value = '保存失败: ' + (err?.response?.data?.detail || err?.message || '未知错误')
  } finally { saving115.value = false }
}

async function renewCookie() {
  try { await renew115Cookie(); alert('Cookie 续期成功 ✅') } catch (err: any) { alert('续期失败: ' + (err?.response?.data?.detail || err.message)) }
}

async function saveTmdb() {
  savingTmdb.value = true
  tmdbMsg.value = ''
  try {
    const payload: any = { language: formTmdb.language, base_url: formTmdb.base_url, image_base_url: formTmdb.image_base_url }
    if (formTmdb.api_key) payload.api_key = formTmdb.api_key
    await patchTmdbConfig(payload)
    tmdbMsgOk.value = true
    tmdbMsg.value = 'TMDB 配置保存成功 ✅'
    setTimeout(() => { if (tmdbMsgOk.value) tmdbMsg.value = '' }, 3000)
  } catch (err: any) {
    tmdbMsgOk.value = false
    tmdbMsg.value = '保存失败: ' + (err?.response?.data?.detail || err.message)
  } finally { savingTmdb.value = false }
}

async function saveStrm() {
  savingStrm.value = true
  try {
    await saveStrmConfig({
      strm_base_url: formStrm.strm_base_url,
      media_library_path: formStrm.media_library_path,
      auto_generate: formStrm.auto_generate,
    })
    showToast('STRM 配置已保存', 'success')
  } catch (e: any) { showToast(e?.response?.data?.detail || '保存失败', 'error') }
  finally { savingStrm.value = false }
}

async function triggerStrm() {
  confirmAction('确认生成 STRM 文件？', async () => {
    try { await triggerStrmGenerate(); showToast('STRM 生成任务已加入队列', 'success') } catch (e: any) { showToast(e?.response?.data?.detail || '生成失败', 'error') }
  })
}

async function saveTransferConfig() {
  savingTransfer.value = true
  try { await updateTransferConfig({ ...formTransfer }); showToast('转存配置已保存', 'success') }
  catch (e: any) { showToast(e?.response?.data?.detail || '保存失败', 'error') }
  finally { savingTransfer.value = false }
}

async function saveSubscriptionConfig() {
  savingSubscription.value = true
  try { await updateSubscriptionConfig({ rss_check_interval_minutes: formSubscription.rss_check_interval_minutes }); showToast('订阅配置已保存', 'success') }
  catch (e: any) { showToast(e?.response?.data?.detail || '保存失败', 'error') }
  finally { savingSubscription.value = false }
}

function confirmCacheClear(type: string) {
  const labels: Record<string, string> = { sync: '同步缓存', tmdb: 'TMDB 缓存', events: '事件游标', all: '全部缓存' }
  confirmAction(`确认清空${labels[type] || type}？此操作不可撤销。`, () => {
    const actions: Record<string, () => Promise<any>> = {
      sync: () => clearSyncCache(),
      tmdb: () => clearTmdbCache(),
      events: () => clearEventsCache(),
      all: () => clearAllCaches(),
    }
    actions[type]?.().then(() => showToast('缓存已清空', 'success')).catch((e: any) => showToast(e?.response?.data?.detail || '清空失败', 'error'))
  })
}

async function loadConfig() {
  loading.value = true
  loadErr.value = false
  try {
    const t = { timeout: 10000 }
    const [r115, rTmdb, rStrm, rTransfer, rSubscription] = await Promise.all([
      get115Config(t).catch(() => null),
      getTmdbConfig(t).catch(() => null),
      getStrmConfig(t).catch(() => null),
      getTransferConfig(t).catch(() => null),
      getSubscriptionConfig(t).catch(() => null),
    ])
    if (r115?.data) {
      form115.uid = r115.data.uid || ''
      form115.username = r115.data.username || ''
      // Sync authStore from DB — restore space info even if uid is already known
      if (!authStore.uid || !authStore.totalSpace) {
        authStore.setAccountInfo(
          r115.data.uid || authStore.uid || '',
          r115.data.total_space || authStore.totalSpace,
          r115.data.used_space || authStore.usedSpace,
        )
      }
    }
    if (rTmdb?.data) { formTmdb.api_key = rTmdb.data.api_key || ''; formTmdb.language = rTmdb.data.language; formTmdb.base_url = rTmdb.data.base_url; formTmdb.image_base_url = rTmdb.data.image_base_url }
    if (rStrm?.data) { formStrm.strm_base_url = rStrm.data.strm_base_url; formStrm.media_library_path = rStrm.data.media_library_path; formStrm.auto_generate = rStrm.data.auto_generate }
    if (rTransfer?.data) {
      formTransfer.max_submit_retry = rTransfer.data.max_submit_retry
      formTransfer.submit_retry_interval_seconds = rTransfer.data.submit_retry_interval_seconds
      formTransfer.max_download_retry = rTransfer.data.max_download_retry
      formTransfer.max_wait_days = rTransfer.data.max_wait_days
    }
    if (rSubscription?.data) { formSubscription.rss_check_interval_minutes = rSubscription.data.rss_check_interval_minutes }

    // Sync 115 login status from backend: clear local state if cookie expired
    try {
      const statusRes = await getAuthStatus()
      if (!statusRes.data.data.logged_in) {
        authStore.uid = ''
        authStore.totalSpace = 0
        authStore.usedSpace = 0
        localStorage.removeItem('uid')
        localStorage.removeItem('totalSpace')
        localStorage.removeItem('usedSpace')
      }
    } catch { /* ignore */ }
  } catch { loadErr.value = true }
  finally { loading.value = false }
}

onMounted(() => {
  loadConfig()
  applyFontSettings()
})

onUnmounted(() => {
  stopQrPolling()
})
</script>

<style scoped>
.config-section { background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.account-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--glass-border, rgba(255,255,255,0.1));
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 16px;
}
.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.account-label { font-weight: 600; font-size: var(--fs-13, 13px); }
.account-badge {
  font-size: var(--fs-11, 11px);
  padding: 2px 10px;
  border-radius: 20px;
}
.account-badge.active { background: rgba(46,204,113,0.15); color: #2ecc71; }
.account-badge.inactive { background: rgba(153,153,153,0.15); color: #999; }
.account-details { display: flex; flex-direction: column; gap: 4px; }
.detail-row { display: flex; gap: 8px; font-size: var(--fs-12, 12px); }
.detail-key { color: var(--text-muted, #999); min-width: 50px; }
.detail-val { color: var(--text, #eee); }
.account-hint { font-size: var(--fs-12, 12px); color: var(--text-muted, #999); }

.qr-login-area { margin-top: 12px; }
.qr-section { margin-top: 10px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.qr-wrapper-sm { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.qr-img-sm { width: 150px; height: 150px; border-radius: 10px; border: 2px solid var(--glass-border, rgba(255,255,255,0.15)); }
.qr-hint-sm { font-size: var(--fs-12, 12px); color: var(--text-muted, #999); }
.qr-placeholder-sm {
  width: 150px; height: 150px; display: flex; align-items: center; justify-content: center;
  border-radius: 10px; border: 2px dashed var(--glass-border, rgba(255,255,255,0.15));
  color: var(--text-muted, #999); font-size: var(--fs-12, 12px); cursor: pointer;
}
.qr-error-sm { color: var(--red, #e74c3c); font-size: var(--fs-12, 12px); }
.qr-status-sm { margin-top: 4px; font-size: var(--fs-12, 12px); color: var(--text-muted, #999); }
.qr-status-sm.confirmed { color: var(--green, #2ecc71); font-weight: 600; }

.save-msg { margin-left: 10px; font-size: var(--fs-12, 12px); }
.save-msg.save-ok { color: var(--green, #2ecc71); }
.save-msg.save-err { color: var(--red, #e74c3c); }
</style>
