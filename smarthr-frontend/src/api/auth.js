import api from './index'

// POST /auth/login
export function login(data) {
  return api.post('/auth/login', data)
}

// POST /auth/register
export function register(data) {
  return api.post('/auth/register', data)
}

// POST /auth/logout
export function logout() {
  return api.post('/auth/logout')
}

// GET /auth/me
export function getCurrentUser() {
  return api.get('/auth/me')
}