<template>
  <!-- Full screen login overlay — password only -->
  <div class="login-overlay" :class="{ hidden: authStore.isLoggedIn }">
    <div class="login-wrap">
      <div class="login-box">
        <h2>📽️ 115-Media</h2>
        <div class="login-desc">影视自动化管理平台</div>

        <div style="margin:24px 0;display:flex;flex-direction:column;gap:14px;text-align:left">
          <div class="form-group">
            <label>用户名</label>
            <input type="text" v-model="authUser" placeholder="请输入用户名" @keydown.enter="focusPass" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input type="password" v-model="authPass" ref="passInput" placeholder="请输入密码" @keydown.enter="doLogin" />
          </div>
          <div v-if="authError" style="color:var(--red);font-size:var(--fs-12)">{{ authError }}</div>
        </div>

        <button class="btn-glass" style="width:100%;padding:10px;font-size:var(--fs-14)" @click="doLogin" :disabled="authLoading">
          {{ authLoading ? '⏳ 登录中...' : '🔐 进入系统' }}
        </button>
        <div style="margin-top:12px;font-size:var(--fs-12);color:var(--text3)">
          115 账号登录请前往 <router-link to="/config" style="color:var(--primary)">设置</router-link> 页面
        </div>
      </div>
    </div>
  </div>

  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="logo-area">
      <div class="logo-icon">📽️</div>
      <div>
        <div class="logo-text">115<span>Media</span></div>
        <div class="logo-sub">影视自动化平台</div>
      </div>
    </div>
    <div class="theme-row">
      <span>{{ isLight ? '☀️ 浅色' : '🌙 深色' }}</span>
      <button class="theme-btn" @click="toggleTheme">{{ isLight ? '🌙' : '☀️' }}</button>
    </div>
    <nav>
      <div class="nav-group">
        <div class="nav-group-title">概览</div>
        <router-link class="nav-item" to="/dashboard" :class="{ active: $route.path === '/dashboard' }">
          <span class="ico">📊</span><span>总览</span>
        </router-link>
      </div>
      <div class="nav-group">
        <div class="nav-group-title">发现</div>
        <router-link class="nav-item" to="/hot/movie" :class="{ active: $route.path === '/hot/movie' }">
          <span class="ico">🔥</span><span>热门电影</span>
        </router-link>
        <router-link class="nav-item" to="/hot/tv" :class="{ active: $route.path === '/hot/tv' }">
          <span class="ico">📺</span><span>热门剧集</span><span class="badge">New</span>
        </router-link>
      </div>
      <div class="nav-group">
        <div class="nav-group-title">管理</div>
        <router-link class="nav-item" to="/subscriptions" :class="{ active: $route.path === '/subscriptions' }">
          <span class="ico">📋</span><span>订阅管理</span>
        </router-link>
        <router-link class="nav-item" to="/transfers" :class="{ active: $route.path === '/transfers' }">
          <span class="ico">⬇️</span><span>转存任务</span>
        </router-link>
        <router-link class="nav-item" to="/sync" :class="{ active: $route.path === '/sync' }">
          <span class="ico">🔄</span><span>数据同步</span>
        </router-link>
        <router-link class="nav-item" to="/files" :class="{ active: $route.path === '/files' }">
          <span class="ico">📁</span><span>文件浏览</span>
        </router-link>
        <router-link class="nav-item" to="/organize" :class="{ active: $route.path === '/organize' }">
          <span class="ico">🗂️</span><span>文件整理</span>
        </router-link>
      </div>
      <div class="nav-group">
        <div class="nav-group-title">系统</div>
        <router-link class="nav-item" to="/config" :class="{ active: $route.path === '/config' }">
          <span class="ico">⚙️</span><span>设置</span>
        </router-link>
        <router-link class="nav-item" to="/notify" :class="{ active: $route.path === '/notify' }">
          <span class="ico">🔔</span><span>通知配置</span>
        </router-link>
        <router-link class="nav-item" to="/logs" :class="{ active: $route.path === '/logs' }">
          <span class="ico">📜</span><span>操作日志</span>
        </router-link>
      </div>
    </nav>
  </aside>

  <!-- Main content -->
  <div class="main">
    <header class="header-bar">
      <div class="header-left">
        <div>
          <h1 id="pageTitle">{{ pageTitle }}</h1>
          <div class="page-sub">{{ pageSub }}</div>
        </div>
      </div>
      <div class="header-right">
        <div class="avatar" @click.stop="showUserMenu = !showUserMenu">
          {{ (authStore.username || 'M').charAt(0).toUpperCase() }}
        </div>
        <div v-if="showUserMenu" class="user-menu" @click.stop>
          <div class="user-menu-name">{{ authStore.username || '用户' }}</div>
          <button class="user-menu-logout" @click="doLogout">🚪 退出登录</button>
        </div>
      </div>
    </header>
    <div class="content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { getMe } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// Login form state
const authUser = ref('admin')
const authPass = ref('admin')
const authError = ref('')
const authLoading = ref(false)
const passInput = ref<HTMLInputElement | null>(null)

// Page meta
const pageTitle = computed(() => (route.meta?.title as string) || '总览')
const pageSubMap: Record<string, string> = {
  'Dashboard': '统计 · 错误卡片 · 最近处理',
  'HotMovie': 'TMDB 热门 · 6 维筛选 · 点击海报订阅',
  'HotTv': 'TMDB 热门剧集 · 6 维筛选 · 点击海报订阅',
  'Subscriptions': 'TMDB ID 订阅 · 画质/策略/集数配置',
  'Sources': 'BT4G 源管理 · 关键词过滤 · 导入/导出',
  'Transfers': '磁力转存 · 4 种状态 · 三层重试',
  'Sync': '全量/增量同步 · 断点恢复',
  'Files': '115 目录 · cid 复制 · 单层搜索',
  'Organize': '分类规则 · TMDB 识别 · 手动修正',
  'Config': '115/TMDB/STRM/转存/订阅 配置',
  'Notify': '飞书/Telegram · 测试发送',
  'Logs': '筛选 · 统计 · 清空',
}
const pageSub = computed(() => pageSubMap[route.name as string] || '')

// Theme
const showUserMenu = ref(false)
const isLight = ref(localStorage.getItem('theme') === 'light')
function toggleTheme() {
  isLight.value = !isLight.value
  localStorage.setItem('theme', isLight.value ? 'light' : 'dark')
  document.documentElement.setAttribute('data-theme', isLight.value ? 'light' : '')
}

// Login
function focusPass() {
  passInput.value?.focus()
}

function doLogout() {
  showUserMenu.value = false
  authStore.logout()
  router.push('/')
}

function closeUserMenu(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.avatar') && !target.closest('.user-menu')) {
    showUserMenu.value = false
  }
}

async function doLogin() {
  authError.value = ''
  authLoading.value = true
  let ok = false
  try {
    const result = await authStore.login(authUser.value, authPass.value)
    ok = result.ok
    if (!ok) authError.value = result.error || '登录失败'
  } catch (err: any) {
    authError.value = err?.message || '登录失败'
  }
  authLoading.value = false
  if (ok) router.push('/dashboard')
}

onMounted(() => {
  // Restore font settings from localStorage
  const html = document.documentElement
  const fs = localStorage.getItem('fontSize') || 'small'
  const ff = localStorage.getItem('fontFamily') || 'system'
  html.classList.remove('size-medium', 'size-large', 'font-siyuan')
  if (fs === 'medium') html.classList.add('size-medium')
  else if (fs === 'large') html.classList.add('size-large')
  if (ff === 'siyuan') {
    html.classList.add('font-siyuan')
    if (!document.querySelector('link[href*="Noto+Sans+SC"]')) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap'
      document.head.appendChild(link)
    }
  }

  // Restore theme
  document.documentElement.setAttribute('data-theme', isLight.value ? 'light' : '')

  document.addEventListener('click', closeUserMenu)
  // Restore auth state from server on page refresh
  if (authStore.token) {
    getMe().then(res => {
      const data = res.data.data
      if (data.username) authStore.setUsername(data.username)
      if (data.uid) authStore.setAccountInfo(data.uid, data.total_space || 0, data.used_space || 0)
    }).catch((err: any) => {
      if (err?.response?.status === 401) {
        authStore.logout()
      }
    })
  }
})

onUnmounted(() => {
  document.removeEventListener('click', closeUserMenu)
})
</script>

<style scoped>
/* User dropdown menu */
.user-menu {
  position: absolute;
  top: 48px;
  right: 28px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur, 20px));
  -webkit-backdrop-filter: blur(var(--blur, 20px));
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 8px;
  min-width: 160px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  z-index: 100;
}
.user-menu-name {
  padding: 8px 12px;
  font-size: var(--fs-13, 13px);
  color: var(--text, #eee);
  border-bottom: 1px solid var(--glass-border);
  margin-bottom: 4px;
}
.user-menu-logout {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--red, #e74c3c);
  font-size: var(--fs-13, 13px);
  cursor: pointer;
  text-align: left;
  transition: background .15s;
  font-family: var(--font);
}
.user-menu-logout:hover {
  background: rgba(231,76,60,0.1);
}

/* Page transition */
.page-enter-active {
  transition: opacity .2s cubic-bezier(0.4, 0, 0.2, 1), transform .2s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-active { transition: opacity .15s cubic-bezier(0.4, 0, 0.2, 1); }
.page-leave-to { opacity: 0; }
</style>
