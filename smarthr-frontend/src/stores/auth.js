import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, logout as apiLogout, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => {
    const stored = localStorage.getItem('user')
    let user = null
    if (stored && stored !== 'null' && stored !== 'undefined') {
      try {
        user = JSON.parse(stored)
      } catch {
        user = null
      }
    }
    return { user, companyId: user?.companyId || null }
  },

  getters: {
    isLoggedIn: state => !!state.user
  },

  actions: {
    async login(email, password) {
      const data = await apiLogin({ email, password })
      // JWT 已通过 HttpOnly Cookie 设置，前端只需存储用户信息
      // data 已是 AuthResponse 对象（UnifiedResponse 已在拦截器中解包）
      if (data) {
        this.user = data
        localStorage.setItem('user', JSON.stringify(this.user))
      }
      return data
    },

    async register(userData) {
      const data = await apiRegister(userData)
      // JWT 已通过 HttpOnly Cookie 设置
      if (data) {
        this.user = data
        this.companyId = data.companyId
        localStorage.setItem('user', JSON.stringify(this.user))
      }
      return data
    },

    async logout() {
      try {
        await apiLogout()
      } finally {
        this.user = null
        localStorage.removeItem('user')
        // 清除 JWT Cookie
        document.cookie = 'jwt=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
      }
    }
  }
})