import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, cookieLogin as apiCookieLogin, getMe } from '@/api/auth'
import type { CookieLoginResponse } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const loggedIn = ref(false)
  const username = ref('')
  const token = ref(localStorage.getItem('token') || '')
  const uid = ref(localStorage.getItem('uid') || '')
  const totalSpace = ref(Number(localStorage.getItem('totalSpace')) || 0)
  const usedSpace = ref(Number(localStorage.getItem('usedSpace')) || 0)

  const isLoggedIn = computed(() => !!token.value)

  async function login(usernameVal: string, password: string): Promise<{ ok: boolean; error?: string }> {
    try {
      const res = await apiLogin({ username: usernameVal, password })
      const data = res.data.data
      applyToken(data.token, data.username)
      return { ok: true }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '登录失败'
      return { ok: false, error: msg }
    }
  }

  async function loginWithCookie(cookieStr: string): Promise<{ ok: boolean; error?: string }> {
    try {
      const res = await apiCookieLogin({ cookie: cookieStr })
      const data: CookieLoginResponse = res.data.data
      applyToken(data.token, data.username)
      uid.value = data.uid
      totalSpace.value = data.total_space
      usedSpace.value = data.used_space
      localStorage.setItem('uid', data.uid)
      localStorage.setItem('totalSpace', String(data.total_space))
      localStorage.setItem('usedSpace', String(data.used_space))
      return { ok: true }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '115 登录失败'
      return { ok: false, error: msg }
    }
  }

  function applyToken(t: string, name: string) {
    token.value = t
    username.value = name
    loggedIn.value = true
    localStorage.setItem('token', t)
    localStorage.setItem('username', name)
  }

  function setToken(t: string) {
    token.value = t
    loggedIn.value = true
    localStorage.setItem('token', t)
  }

  function setUsername(name: string) {
    username.value = name
  }

  function setAccountInfo(uidVal: string, total: number, used: number) {
    uid.value = uidVal
    totalSpace.value = total
    usedSpace.value = used
    localStorage.setItem('uid', uidVal)
    localStorage.setItem('totalSpace', String(total))
    localStorage.setItem('usedSpace', String(used))
  }

  function logout() {
    token.value = ''
    username.value = ''
    uid.value = ''
    totalSpace.value = 0
    usedSpace.value = 0
    loggedIn.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('uid')
    localStorage.removeItem('totalSpace')
    localStorage.removeItem('usedSpace')
  }

  return {
    loggedIn, username, token, uid, totalSpace, usedSpace, isLoggedIn,
    login, loginWithCookie, setToken, setUsername, setAccountInfo, logout,
  }
})
