<template>
  <div>
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div><div>加载中...</div></div>
    <div v-else>
      <div class="section-hdr">
        <div class="section-title">文件浏览</div>
        <div style="display:flex;gap:8px;align-items:center">
          <div class="search-box" style="width:200px"><span>🔍</span><input type="text" v-model="searchQ" placeholder="搜索当前目录..." @input="filterFiles" /></div>
          <input type="text" v-model="cidInput" placeholder="输入 cid 直达" style="width:180px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg2);color:var(--text);font-size:var(--fs-12)" @keydown.enter="jumpCid" />
          <button class="btn-ghost btn-sm" @click="jumpCid">跳转</button>
          <span style="font-size:var(--fs-12);color:var(--text3)">cid: {{ currentCid }}</span>
        </div>
      </div>
      <div style="font-size:var(--fs-12);color:var(--text3);margin-bottom:8px">
        当前路径:
        <span v-for="(p, i) in pathParts" :key="p.cid || i">
          <span v-if="i > 0" style="color:var(--text4)"> / </span>
          <span class="path-link" @click="navigateTo(p.cid)">{{ p.name || '根目录' }}</span>
        </span>
      </div>
      <div class="data-table">
        <div class="th" style="grid-template-columns:3fr 1fr 1fr 1.2fr">
          <span>文件名</span><span>大小</span><span>类型</span><span>cid</span>
        </div>
        <div v-for="f in displayedFiles" :key="f.cid || f.id" class="tr file-row" style="grid-template-columns:3fr 1fr 1fr 1.2fr" :title="f.file_name">
          <span :class="{ 'clickable-name': f.is_dir }" @click="f.is_dir && enterDir(f)">
            <span class="file-icon">{{ f.is_dir ? '📁' : '🎬' }}</span>
            {{ f.file_name }}
          </span>
          <span style="font-size:var(--fs-12)">{{ formatSize(f.file_size) }}</span>
          <span><span class="tag" :class="f.is_dir ? 'tag-wait' : 'tag-guo'">{{ f.is_dir ? '目录' : f.media_type === 'video' ? '视频' : f.media_type === 'audio' ? '音频' : '文件' }}</span></span>
          <span style="font-size:var(--fs-11);color:var(--text3);cursor:pointer" @click.stop="copyCid(f.cid, $event)">{{ cidCopied === f.cid ? '✓已复制' : f.cid }}</span>
        </div>
        <div v-if="displayedFiles.length === 0 && !loading" style="padding:24px;text-align:center;color:var(--text3)">{{ searchQ ? '无匹配结果' : '暂无文件' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { browseFiles } from '@/api/files'
import type { MediaFileItem } from '@/api/types'

const loading = ref(true)
const files = ref<MediaFileItem[]>([])
const currentCid = ref('0')
const pathParts = ref<{ name: string; cid: string }[]>([])
const searchQ = ref('')
const cidCopied = ref('')
const cidInput = ref('')

const displayedFiles = computed(() => {
  if (!searchQ.value.trim()) return files.value
  const q = searchQ.value.toLowerCase()
  return files.value.filter(f => f.file_name.toLowerCase().includes(q))
})

function filterFiles() {
  // computed handles filtering, no-op for @input binding
}

function jumpCid() {
  const cid = cidInput.value.trim()
  if (cid) {
    currentCid.value = cid
    cidInput.value = ''
    fetchBrowse()
  }
}

function navigateTo(cid: string) {
  currentCid.value = cid
  fetchBrowse()
}

async function enterDir(f: any) {
  if (f.is_dir) {
    currentCid.value = f.cid
    searchQ.value = ''
    await fetchBrowse()
  }
}

function copyCid(cid: string, _event?: MouseEvent) {
  let ok = false
  try {
    const ta = document.createElement('textarea')
    ta.value = cid
    ta.style.cssText = 'position:fixed;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    ok = document.execCommand('copy')
    document.body.removeChild(ta)
  } catch {}
  if (ok) {
    cidCopied.value = cid
    setTimeout(() => { cidCopied.value = '' }, 1500)
  } else {
    navigator.clipboard?.writeText(cid).then(() => {
      cidCopied.value = cid
      setTimeout(() => { cidCopied.value = '' }, 1500)
    }).catch(() => {
      cidCopied.value = '复制失败'
      setTimeout(() => { cidCopied.value = '' }, 2000)
    })
  }
}

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return size.toFixed(1) + ' ' + units[i]
}

async function fetchBrowse() {
  loading.value = true
  try {
    const res = await browseFiles(currentCid.value)
    files.value = res.data.data.files || []
    pathParts.value = res.data.data.path_parts || []
  } catch { /* ignore */ }
  finally { loading.value = false }
}

onMounted(fetchBrowse)
</script>

<style scoped>
.file-row { cursor: default; }
.file-row:hover { background: var(--hover); }
.file-icon { margin-right: 6px; }
.clickable-name { cursor: pointer; color: var(--accent); }
.clickable-name:hover { text-decoration: underline; }
.path-link { cursor: pointer; color: var(--accent); }
.path-link:hover { text-decoration: underline; }
</style>
