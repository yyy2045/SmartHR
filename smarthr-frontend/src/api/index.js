import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 200000,  // AI 相关接口可能耗时较长（LLM 调用），拉长到 200s
  withCredentials: true  // 跨域请求需要携带 HttpOnly Cookie
})

// Request interceptor - 添加 JWT Token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  response => {
    // Unwrap UnifiedResponse if present
    const data = response.data
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code !== 200) {
        ElMessage.error(data.message || 'Request failed')
        return Promise.reject(new Error(data.message))
      }
      return data.data
    }
    return data
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    const message = error.response?.data?.message || error.message || 'Network error'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default api