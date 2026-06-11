import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('uid')
      localStorage.removeItem('totalSpace')
      localStorage.removeItem('usedSpace')
      const { useAuthStore } = await import('@/store/auth')
      useAuthStore().logout()
    }
    return Promise.reject(err)
  },
)

export default http
