import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: DashboardView, meta: { title: '总览' } },
  { path: '/hot/movie', name: 'HotMovie', component: () => import('@/views/HotMovieView.vue'), meta: { title: '热门电影' } },
  { path: '/hot/tv', name: 'HotTv', component: () => import('@/views/HotTvView.vue'), meta: { title: '热门剧集' } },
  { path: '/subscriptions', name: 'Subscriptions', component: () => import('@/views/SubscriptionsView.vue'), meta: { title: '订阅管理' } },
  { path: '/sources', redirect: '/subscriptions' },
  { path: '/transfers', name: 'Transfers', component: () => import('@/views/TransfersView.vue'), meta: { title: '转存任务' } },
  { path: '/sync', name: 'Sync', component: () => import('@/views/SyncView.vue'), meta: { title: '数据同步' } },
  { path: '/files', name: 'Files', component: () => import('@/views/FileBrowserView.vue'), meta: { title: '文件浏览' } },
  { path: '/organize', name: 'Organize', component: () => import('@/views/OrganizeView.vue'), meta: { title: '文件整理' } },
  { path: '/config', name: 'Config', component: () => import('@/views/ConfigView.vue'), meta: { title: '设置' } },
  { path: '/notify', name: 'Notify', component: () => import('@/views/NotifyView.vue'), meta: { title: '通知配置' } },
  { path: '/logs', name: 'Logs', component: () => import('@/views/LogsView.vue'), meta: { title: '操作日志' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
