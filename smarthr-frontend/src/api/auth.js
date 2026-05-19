import api from './index'

// POST /api/auth/login
export function login(data) {
  return api.post('/api/auth/login', data)
}

// POST /api/auth/register
export function register(data) {
  return api.post('/api/auth/register', data)
}

// POST /api/auth/logout
export function logout() {
  return api.post('/api/auth/logout')
}

// GET /api/auth/me
export function getCurrentUser() {
  return api.get('/api/auth/me')
}