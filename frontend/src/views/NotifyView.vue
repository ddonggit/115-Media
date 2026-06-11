<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">通知配置</div>
        <div style="display:flex;gap:8px">
          <button class="btn-ghost btn-sm" @click="testNotifyAction">📤 测试</button>
          <button class="btn-accent" @click="openAddModal">+ 添加通知</button>
        </div>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:1.5fr 1fr 1.5fr 1.2fr">
          <span>渠道</span><span>状态</span><span>通知事件</span><span>操作</span>
        </div>
        <div v-for="n in configs" :key="n.id" class="tr" style="grid-template-columns:1.5fr 1fr 1.5fr 1.2fr">
          <span><span class="tag" :class="n.channel === 'telegram' ? 'tag-ri' : 'tag-guo'">{{ n.channel === 'telegram' ? 'Telegram' : '飞书' }}</span></span>
          <span><span class="status-badge" :class="n.enabled ? 's-running' : 's-wait'">{{ n.enabled ? '已启用' : '已停用' }}</span></span>
          <span style="font-size:var(--fs-12)">{{ n.notify_on || '—' }}</span>
          <span class="sub-actions">
            <button class="btn-ghost btn-sm" @click="editConfig(n)">编辑</button>
            <button class="btn-ghost btn-sm" style="color:var(--red)" @click="deleteConfigAction(n.id)">删除</button>
          </span>
        </div>
        <div v-if="configs.length === 0" style="padding:24px;text-align:center;color:var(--text3)">暂无通知配置</div>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal" style="max-width:480px">
        <h2>{{ editingId ? '编辑通知' : '添加通知' }}</h2>
        <div class="form-group"><label>渠道</label><select v-model="form.channel"><option value="feishu">飞书</option><option value="telegram">Telegram</option></select></div>
        <div class="form-group"><label>Webhook URL <span class="req">*</span></label><input type="text" v-model="form.webhook_url" /></div>
        <template v-if="form.channel === 'telegram'">
          <div class="form-group"><label>Bot Token</label><input type="text" v-model="form.bot_token" /></div>
          <div class="form-group"><label>Chat ID</label><input type="text" v-model="form.chat_id" /></div>
        </template>
        <div class="form-group"><label>通知事件</label><input type="text" v-model="form.notify_on" placeholder='如 ["transfer_done","organize_done"]' /></div>
        <div class="form-group"><label>启用 <input type="checkbox" v-model="form.enabled" /></label></div>
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
import { listNotifyConfigs, createNotifyConfig, updateNotifyConfig, deleteNotifyConfig, testNotify } from '@/api/notify'
import { showToast } from '@/utils/toast'
import type { NotifyConfigItem } from '@/api/types'
import ConfirmModal from '@/components/ConfirmModal.vue'

const loading = ref(true)
const configs = ref<NotifyConfigItem[]>([])
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

const form = reactive({
  channel: 'feishu', webhook_url: '', bot_token: '', chat_id: '',
  enabled: false, notify_on: '',
})

function openAddModal() {
  editingId.value = null
  form.channel = 'feishu'; form.webhook_url = ''; form.bot_token = ''; form.chat_id = ''
  form.enabled = false; form.notify_on = ''
  formError.value = ''; showModal.value = true
}

function editConfig(n: NotifyConfigItem) {
  editingId.value = n.id
  form.channel = n.channel; form.webhook_url = ''; form.bot_token = ''; form.chat_id = ''
  form.enabled = n.enabled; form.notify_on = n.notify_on || ''
  formError.value = ''; showModal.value = true
}

function closeModal() { showModal.value = false; editingId.value = null }

async function save() {
  if (!form.webhook_url) { formError.value = '请填写 Webhook URL'; return }
  saving.value = true
  formError.value = ''
  try {
    const data = {
      channel: form.channel as any,
      webhook_url: form.webhook_url,
      bot_token: form.bot_token || undefined,
      chat_id: form.chat_id || undefined,
      enabled: form.enabled,
      notify_on: form.notify_on || undefined,
    }
    if (editingId.value) { await updateNotifyConfig(editingId.value, data) }
    else { await createNotifyConfig(data as any) }
    closeModal(); await fetchData()
  } catch (err: any) { formError.value = err?.response?.data?.detail || '保存失败' }
  finally { saving.value = false }
}

async function deleteConfigAction(id: number) {
  confirmAction('确定删除？', async () => {
    try { await deleteNotifyConfig(id); await fetchData(); showToast('通知配置已删除', 'success') } catch { showToast('删除失败', 'error') }
  })
}

async function testNotifyAction() {
  try { await testNotify(); alert('测试通知已发送 ✅') } catch (err: any) { alert('发送失败: ' + (err?.response?.data?.detail || err.message)) }
}

async function fetchData() {
  loading.value = true
  try { const r = await listNotifyConfigs(); configs.value = r.data } catch { /* ignore */ }
  finally { loading.value = false }
}

onMounted(fetchData)
</script>
