import api from './index'
import axios from 'axios'

// Python AI 服务 - 面试相关直接调 Python
const pythonApi = axios.create({
  baseURL: import.meta.env.VITE_PYTHON_API_URL || '/python',
  timeout: 200000,
  withCredentials: true
})
pythonApi.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})
// Response interceptor - Python 直接返回数据，不需要解包
pythonApi.interceptors.response.use(response => response.data)

// 工作台统计 - 仍然调 Java
export function getInterviewSessions(params) {
  return api.get('/api/interview/sessions', { params })
}

// 以下全部调 Python
export function createInterviewSession(data) {
  return pythonApi.post('/api/interview/sessions', data)
}

export function getInterviewSession(id) {
  return pythonApi.get(`/api/interview/sessions/${id}`)
}

export function sendInterviewMessage(sessionId, data) {
  return pythonApi.post(`/api/interview/sessions/${sessionId}/message`, data)
}

export function endInterview(sessionId) {
  return pythonApi.post(`/api/interview/sessions/${sessionId}/end`)
}

export function getInterviewReport(sessionId) {
  return pythonApi.get(`/api/interview/sessions/${sessionId}/report`)
}

export function getInterviewResume(sessionId) {
  return pythonApi.get(`/api/interview/sessions/${sessionId}/resume`)
}

// 工作台统计 - 调 Java
export function getReportsCount() {
  return api.get('/api/interview/reports/stats/count')
}